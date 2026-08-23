"""Automates the prompt-injection attack from ADR 0003/0004.

Reads its cases from sextant/adversarial/injection_cases.jsonl rather than
hardcoding them here — that file already defines the attack payload, the
probes, and what counts as a compromised answer. Duplicating that as a
second, slightly-different list inline would give this project two things
calling themselves "the injection test", which drift apart the first time
one gets edited and not the other.

Week 1/2 proved this by hand: plant a poisoned document, ask the probes, read
the answers, delete the document. Useful once, but a manual test that
"someone should re-run before every release" is a test that will quietly
stop being re-run. This is that procedure as a script, so it belongs in CI on
every change to Almanac's prompt or the provider it uses.

document_injection cases seed a poisoned document, run the probes, and ALWAYS
remove it afterward — even on failure — because leaving attack content in a
demo tenant's live corpus is a real Postgres row a real Almanac call could
retrieve later, not a theoretical dangling resource. user_injection cases
need no document; the attack rides in the customer message itself.

Usage:  python sextant/run_injection.py [--provider ollama|groq|gemini]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import delete, select, text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.agents.almanac import answer_question  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db.models import Chunk, Document, Tenant  # noqa: E402
from app.rag.ingest import ingest_document  # noqa: E402

CASES_FILE = Path(__file__).parent / "adversarial" / "injection_cases.jsonl"
ATTACK_SOURCE = "SEXTANT_ATTACK"


async def _run_case(session, case: dict, *, tenant_id: str, tenant_name: str, provider: str | None) -> dict:
    if case["kind"] == "document_injection":
        await ingest_document(
            session, tenant_id=tenant_id, title=case["payload_title"],
            text=case["payload"], source=ATTACK_SOURCE,
        )
        await session.flush()

    probe_results = []
    for probe in case["probes"]:
        a = await answer_question(session, probe, tenant_name=tenant_name, provider_name=provider)
        hit = any(marker in a.text for marker in case["fail_if_answer_contains"])
        probe_results.append({"probe": probe, "compromised": hit, "answer": a.text[:150]})

    if case["kind"] == "document_injection":
        docs = (
            await session.execute(select(Document).where(Document.source == ATTACK_SOURCE))
        ).scalars().all()
        for d in docs:
            await session.execute(delete(Chunk).where(Chunk.document_id == d.id))
            await session.execute(delete(Document).where(Document.id == d.id))

    return {"id": case["id"], "kind": case["kind"], "note": case["note"], "probes": probe_results}


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["ollama", "groq", "gemini"], default=None)
    args = parser.parse_args()

    cases = [json.loads(line) for line in CASES_FILE.read_text().splitlines() if line.strip()]
    settings = get_settings()
    provider_label = args.provider or settings.answer_provider
    engine = create_async_engine(settings.database_url, connect_args={"statement_cache_size": 0})
    Session = async_sessionmaker(engine, expire_on_commit=False)

    print(f"provider={provider_label}  cases={len(cases)}\n")
    all_results = []
    tenant_cache: dict[str, tuple[str, str]] = {}

    async with Session() as session:
        for case in cases:
            slug = case["tenant"]
            if slug not in tenant_cache:
                async with session.begin():
                    t = (await session.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one()
                tenant_cache[slug] = (str(t.id), t.name)
            tid, tname = tenant_cache[slug]

            try:
                async with session.begin():
                    await session.execute(text("SELECT set_config('app.current_tenant', :t, true)"), {"t": tid})
                    result = await _run_case(session, case, tenant_id=tid, tenant_name=tname, provider=args.provider)
            except Exception:
                # A poisoned document must never survive a failed run — the
                # try/except at the call site of ingest_document isn't
                # enough on its own if the probe loop itself raises.
                async with session.begin():
                    await session.execute(text("SELECT set_config('app.current_tenant', :t, true)"), {"t": tid})
                    docs = (
                        await session.execute(select(Document).where(Document.source == ATTACK_SOURCE))
                    ).scalars().all()
                    for d in docs:
                        await session.execute(delete(Chunk).where(Chunk.document_id == d.id))
                        await session.execute(delete(Document).where(Document.id == d.id))
                raise

            all_results.append(result)
            print(f"  {case['id']}  ({case['kind']}) — {case['note']}")
            for p in result["probes"]:
                mark = "COMPROMISED" if p["compromised"] else "resisted"
                print(f"    [{mark}] {p['probe']!r}")
            print()

    await engine.dispose()

    total_probes = sum(len(r["probes"]) for r in all_results)
    total_compromised = sum(p["compromised"] for r in all_results for p in r["probes"])
    print("=" * 50)
    print(f"provider={provider_label}: {total_compromised}/{total_probes} probes compromised the model")
    print("=" * 50)
    return 1 if total_compromised else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

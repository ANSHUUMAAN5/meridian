"""Sextant — replays golden_set.jsonl through the real pipeline and scores it.

Calls app.orchestrator.handle_message directly rather than over HTTP: this is
the same code path a request takes (same Compass, same Threshold, same
specialists, same Trace writes), just without the network hop, so a full run
is fast enough to use during development, not only in CI.

Usage:
    python sextant/run.py                    # full golden set
    python sextant/run.py --kind routing      # one slice
    python sextant/run.py --tenant nimbus     # one tenant
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db.models import Conversation, Message, Tenant  # noqa: E402
from app.orchestrator import handle_message  # noqa: E402

GOLDEN_SET = Path(__file__).parent / "golden_set.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"

# A hard negative is graded on whether the FINAL answer avoids asserting a
# specific invented fact — not on which agent handled it or whether it
# escalated, both of which are legitimate outcomes (see run.py module notes).
# Deliberately the same fragile-by-nature approach flagged in ADR 0004: a
# fixed phrase list mis-scores paraphrases. Tracked as a known limitation to
# replace with an LLM judge, not treated as ground truth.
REFUSAL_MARKERS = (
    "do not know", "don't know", "not have", "no information", "cannot find",
    "not sure", "don't have", "unable to", "connect you with a human",
    "connect you with someone", "not something we handle",
)


@dataclass
class CaseResult:
    id: str
    kind: str
    tenant: str
    message: str
    expected_intent: str
    actual_intent: str
    expected_escalate: bool
    actual_escalate: bool
    agent: str
    confidence: float
    answer: str
    latency_ms: int

    @property
    def intent_correct(self) -> bool:
        return self.actual_intent == self.expected_intent

    @property
    def escalate_correct(self) -> bool:
        return self.actual_escalate == self.expected_escalate

    @property
    def refused_correctly(self) -> bool:
        return any(m in self.answer.lower() for m in REFUSAL_MARKERS)


async def _load_cases(kind: str | None, tenant: str | None) -> list[dict]:
    cases = [json.loads(line) for line in GOLDEN_SET.read_text().splitlines() if line.strip()]
    if kind:
        cases = [c for c in cases if c["kind"] == kind]
    if tenant:
        cases = [c for c in cases if c["tenant"] == tenant]
    return cases


async def run() -> list[CaseResult]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["routing", "escalation", "adversarial", "hard_negative"])
    parser.add_argument("--tenant", choices=["kite", "nimbus"])
    args = parser.parse_args()

    cases = await _load_cases(args.kind, args.tenant)
    if not cases:
        print("no matching cases")
        return []

    settings = get_settings()
    engine = create_async_engine(settings.database_url, connect_args={"statement_cache_size": 0})
    Session = async_sessionmaker(engine, expire_on_commit=False)

    tenant_cache: dict[str, tuple[str, str]] = {}  # slug -> (id, name)
    results: list[CaseResult] = []

    async with Session() as session:
        for i, case in enumerate(cases, 1):
            slug = case["tenant"]
            if slug not in tenant_cache:
                async with session.begin():
                    t = (await session.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one()
                tenant_cache[slug] = (str(t.id), t.name)
            tenant_id, tenant_name = tenant_cache[slug]

            async with session.begin():
                await session.execute(
                    text("SELECT set_config('app.current_tenant', :t, true)"), {"t": tenant_id}
                )
                conv = Conversation(tenant_id=tenant_id, external_customer_id="sextant")
                session.add(conv)
                await session.flush()
                msg = Message(
                    tenant_id=tenant_id, conversation_id=conv.id, role="customer", content=case["message"]
                )
                session.add(msg)
                await session.flush()

                started = time.perf_counter()
                outcome = await handle_message(
                    session,
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                    conversation_id=str(conv.id),
                    message_id=str(msg.id),
                    customer_message=case["message"],
                )
                elapsed = int((time.perf_counter() - started) * 1000)

            results.append(
                CaseResult(
                    id=case["id"], kind=case["kind"], tenant=slug, message=case["message"],
                    expected_intent=case["expected_intent"], actual_intent=outcome.intent,
                    expected_escalate=case["expected_escalate"], actual_escalate=outcome.escalated,
                    agent=outcome.agent, confidence=outcome.confidence, answer=outcome.answer,
                    latency_ms=elapsed,
                )
            )
            print(f"  [{i}/{len(cases)}] {case['id']:<12} done", end="\r", flush=True)

    print(" " * 60, end="\r")
    await engine.dispose()
    return results


def report(results: list[CaseResult]) -> dict:
    by_kind: dict[str, list[CaseResult]] = defaultdict(list)
    for r in results:
        by_kind[r.kind].append(r)

    summary: dict = {"total_cases": len(results), "by_kind": {}}

    print(f"\n{'=' * 70}")
    print(f"SEXTANT — {len(results)} cases")
    print("=" * 70)

    routing = by_kind.get("routing", []) + by_kind.get("adversarial", [])
    if routing:
        acc = sum(r.intent_correct for r in routing) / len(routing)
        esc_acc = sum(r.escalate_correct for r in routing) / len(routing)
        print(f"\nROUTING  (routing + adversarial, n={len(routing)})")
        print(f"  intent accuracy:     {acc:.1%}")
        print(f"  escalation accuracy: {esc_acc:.1%}")
        summary["routing_accuracy"] = round(acc, 4)
        summary["routing_escalation_accuracy"] = round(esc_acc, 4)

        wrong = [r for r in routing if not r.intent_correct]
        if wrong:
            print(f"\n  misrouted ({len(wrong)}):")
            for r in wrong:
                print(f"    {r.id}: {r.message[:50]!r}")
                print(f"           expected={r.expected_intent}  actual={r.actual_intent} (conf={r.confidence:.2f})")

    esc = by_kind.get("escalation", [])
    if esc:
        correct = sum(r.escalate_correct for r in esc)
        print(f"\nESCALATION SLICE  (n={len(esc)}) — should_escalate={{'True' if all}}")
        print(f"  correct: {correct}/{len(esc)}")
        summary["escalation_slice_correct"] = f"{correct}/{len(esc)}"

    hard_neg = by_kind.get("hard_negative", [])
    if hard_neg:
        refused = sum(r.refused_correctly for r in hard_neg)
        print(f"\nHARD NEGATIVES  (n={len(hard_neg)}) — must refuse, not invent")
        print(f"  refused correctly: {refused}/{len(hard_neg)}")
        for r in hard_neg:
            mark = "OK" if r.refused_correctly else "**HALLUCINATION RISK**"
            print(f"    {r.id}: {mark}  {r.message[:45]!r}")
            if not r.refused_correctly:
                print(f"           answered: {r.answer[:100]!r}")
        summary["hard_negative_refusal_rate"] = round(refused / len(hard_neg), 4)

    latencies = sorted(r.latency_ms for r in results)
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    print(f"\nLATENCY   p50={p50}ms  p95={p95}ms")
    summary["latency_p50_ms"] = p50
    summary["latency_p95_ms"] = p95

    for kind, rs in by_kind.items():
        summary["by_kind"][kind] = len(rs)

    print("=" * 70)
    return summary


def main() -> None:
    results = asyncio.run(run())
    if not results:
        return
    summary = report(results)

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = RESULTS_DIR / f"{stamp}.json"
    out.write_text(json.dumps({
        "summary": summary,
        "cases": [
            {
                "id": r.id, "kind": r.kind, "tenant": r.tenant, "message": r.message,
                "expected_intent": r.expected_intent, "actual_intent": r.actual_intent,
                "intent_correct": r.intent_correct,
                "expected_escalate": r.expected_escalate, "actual_escalate": r.actual_escalate,
                "escalate_correct": r.escalate_correct, "agent": r.agent,
                "confidence": r.confidence, "latency_ms": r.latency_ms,
            }
            for r in results
        ],
    }, indent=2))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()

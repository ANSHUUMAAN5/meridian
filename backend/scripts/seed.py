"""Seed a demo tenant with documents and orders.

Idempotent: re-running wipes that tenant's documents and orders and rebuilds
them, so it is safe to run after editing the seed corpus.

Runs as the restricted application role, not the owner — which means it goes
through the same RLS path as a real request. If seeding works, the tenant
context plumbing works.

Usage:  python scripts/seed.py [--tenant kite]
"""

from __future__ import annotations

import argparse
import asyncio
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models import Chunk, Document, Order, Tenant, User
from app.rag.ingest import ingest_document

SEEDS = Path(__file__).resolve().parents[1] / "seeds"

TENANTS = {
    "kite": {
        "name": "Kite & Co",
        "admin": "priya@kiteandco.in",
        "settings": {"currency": "INR", "brand_tone": "warm, plain-spoken, never pushy"},
    },
    "nimbus": {
        "name": "Nimbus Health",
        "admin": "anjali@nimbushealth.in",
        "settings": {
            "currency": "INR",
            "brand_tone": "calm, precise, never speculative about medical matters",
            # Deliberately different domain from Kite (clothing) so the demo
            # proves the same code answers correctly for two unrelated
            # businesses — see plan §3.
        },
    },
}

ORDER_STATUSES = ["confirmed", "processing", "dispatched", "out_for_delivery", "delivered", "cancelled"]
KITE_ITEMS = [
    ("Linen Camp Shirt", "M", 2499), ("Linen Camp Shirt", "L", 2499),
    ("Wide-Leg Trouser", "S", 3299), ("Cotton Crew Tee", "M", 1199),
    ("Merino Cardigan", "L", 4599), ("Denim Jacket", "M", 5299),
    ("Silk Scarf", "One Size", 1899), ("Chino Shorts", "32", 1999),
]
# (item, pack size, price) — no dosage/quantity language beyond pack size;
# Manifest reports what a pharmacy order system reports, nothing that reads
# as medical guidance.
NIMBUS_ITEMS = [
    ("Metformin 500mg", "30 tablets", 149), ("Insulin Glargine", "1 pen (3ml)", 899),
    ("Atorvastatin 10mg", "30 tablets", 179), ("Levothyroxine 50mcg", "90 tablets", 129),
    ("Amoxicillin 250mg", "15 capsules", 89), ("Cetirizine 10mg (OTC)", "10 tablets", 35),
    ("Multivitamin", "60 tablets", 249), ("Losartan 50mg", "30 tablets", 159),
]
ITEM_POOLS = {"kite": KITE_ITEMS, "nimbus": NIMBUS_ITEMS}
ORDER_PREFIXES = {"kite": "KC", "nimbus": "NH"}


def _title_from(path: Path) -> str:
    """'01-returns.md' -> 'Returns' (the heading is inside the file)."""
    stem = path.stem.split("-", 1)[-1]
    return stem.replace("-", " ").title()


async def seed(slug: str) -> None:
    spec = TENANTS[slug]
    settings = get_settings()
    engine = create_async_engine(settings.database_url, connect_args={"statement_cache_size": 0})
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        async with session.begin():
            tenant = (
                await session.execute(select(Tenant).where(Tenant.slug == slug))
            ).scalar_one_or_none()
            if tenant is None:
                tenant = Tenant(name=spec["name"], slug=slug, settings=spec["settings"])
                session.add(tenant)
                await session.flush()
                print(f"created tenant {spec['name']} ({slug})")
            else:
                print(f"tenant {spec['name']} already exists")

            tenant_id = str(tenant.id)

            # From here on, behave exactly like a request: bind the session to
            # this tenant so every write goes through the RLS WITH CHECK.
            await session.execute(
                text("SELECT set_config('app.current_tenant', :t, true)"), {"t": tenant_id}
            )

            user = (
                await session.execute(select(User).where(User.email == spec["admin"]))
            ).scalar_one_or_none()
            if user is None:
                session.add(User(tenant_id=tenant_id, email=spec["admin"], role="admin"))
                print(f"created admin user {spec['admin']}")

            # Rebuild documents from scratch so edits to the corpus take effect.
            await session.execute(delete(Chunk).where(Chunk.tenant_id == tenant_id))
            await session.execute(delete(Document).where(Document.tenant_id == tenant_id))

            files = sorted((SEEDS / slug).glob("*.md"))
            if not files:
                raise SystemExit(f"no seed documents in {SEEDS / slug}")

            total_chunks = 0
            for path in files:
                result = await ingest_document(
                    session,
                    tenant_id=tenant_id,
                    title=_title_from(path),
                    text=path.read_text(),
                    source=f"seeds/{slug}/{path.name}",
                )
                total_chunks += result.chunks
                print(f"  {result.title:<22} {result.chunks:>2} chunks  {result.tokens:>4} tokens")

            # Orders — the mock commerce backend Manifest will query.
            await session.execute(delete(Order).where(Order.tenant_id == tenant_id))
            rng = random.Random(4471)  # deterministic so eval cases stay valid
            now = datetime.now(UTC)
            items_pool = ITEM_POOLS[slug]
            prefix = ORDER_PREFIXES[slug]
            for i in range(24):
                items = [
                    {"name": n, "size": size, "price": p, "qty": 1}
                    for n, size, p in rng.sample(items_pool, rng.randint(1, 3))
                ]
                session.add(
                    Order(
                        tenant_id=tenant_id,
                        order_number=f"{prefix}{4400 + i}",
                        external_customer_id=f"cust_{rng.randint(1000, 1099)}",
                        status=rng.choice(ORDER_STATUSES),
                        items=items,
                        total=sum(it["price"] for it in items),
                        currency="INR",
                        placed_at=now - timedelta(days=rng.randint(1, 45)),
                    )
                )

            print(f"\n{len(files)} documents, {total_chunks} chunks, 24 orders")

    await engine.dispose()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", default="kite", choices=sorted(TENANTS))
    asyncio.run(seed(ap.parse_args().tenant))

    # fastembed's ONNX runtime has a native-level cleanup bug on macOS: its
    # thread pool destructor can throw during Python's normal interpreter
    # shutdown (libc++abi: recursive_mutex lock failed), well after the
    # database transaction has already committed. os._exit skips that
    # teardown entirely rather than let a cosmetic crash-on-exit report this
    # script as failed when the actual seeding succeeded — verified by
    # querying the database independently after a run that "crashed".
    #
    # os._exit also skips Python's normal buffer flush, which is invisible
    # interactively (the terminal is line-buffered) but silently swallows
    # every print() the moment output is piped or redirected — exactly how
    # CI and `| tail` consume it. Flush explicitly first.
    import os
    import sys

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)

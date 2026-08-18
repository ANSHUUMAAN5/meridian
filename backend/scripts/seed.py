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
}

ORDER_STATUSES = ["confirmed", "processing", "dispatched", "out_for_delivery", "delivered", "cancelled"]
KITE_ITEMS = [
    ("Linen Camp Shirt", "M", 2499), ("Linen Camp Shirt", "L", 2499),
    ("Wide-Leg Trouser", "S", 3299), ("Cotton Crew Tee", "M", 1199),
    ("Merino Cardigan", "L", 4599), ("Denim Jacket", "M", 5299),
    ("Silk Scarf", "One Size", 1899), ("Chino Shorts", "32", 1999),
]


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
            for i in range(24):
                items = [
                    {"name": n, "size": s, "price": p, "qty": 1}
                    for n, s, p in rng.sample(KITE_ITEMS, rng.randint(1, 3))
                ]
                session.add(
                    Order(
                        tenant_id=tenant_id,
                        order_number=f"KC{4400 + i}",
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

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models import (
    AgentTrace,
    Chunk,
    Conversation,
    Document,
    Escalation,
    Message,
    Order,
    Tenant,
    User,
)

TENANT_SETTING = "app.current_tenant"


@pytest_asyncio.fixture(scope="module")
async def app_sessionmaker() -> async_sessionmaker[AsyncSession]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, connect_args={"statement_cache_size": 0})
    return async_sessionmaker(engine, expire_on_commit=False)


async def bind_tenant(session: AsyncSession, tenant_id: str | None) -> None:
    await session.execute(
        text(f"SELECT set_config('{TENANT_SETTING}', :t, true)"), {"t": tenant_id or ""}
    )


@dataclass(frozen=True)
class SeededTenant:
    id: str
    document_id: str
    chunk_id: str
    conversation_id: str
    message_id: str
    trace_id: str
    escalation_id: str
    order_id: str
    user_id: str


async def _seed_one_tenant(session: AsyncSession, *, name: str, slug: str) -> SeededTenant:
    tenant = Tenant(name=name, slug=slug)
    session.add(tenant)
    await session.flush()
    tid = str(tenant.id)

    await bind_tenant(session, tid)

    user = User(tenant_id=tid, email=f"owner@{slug}.test", role="admin")
    doc = Document(tenant_id=tid, title="Isolation test doc", status="indexed")
    session.add_all([user, doc])
    await session.flush()

    chunk = Chunk(
        tenant_id=tid, document_id=doc.id, ordinal=0,
        content="isolation test content", embedding=[0.0] * get_settings().embed_dim,
    )
    conv = Conversation(tenant_id=tid, external_customer_id=f"cust_{slug}")
    session.add_all([chunk, conv])
    await session.flush()

    msg = Message(tenant_id=tid, conversation_id=conv.id, role="customer", content="hello")
    order = Order(tenant_id=tid, order_number=f"TEST-{slug}", external_customer_id=f"cust_{slug}",
                   status="confirmed", items=[])
    session.add_all([msg, order])
    await session.flush()

    trace = AgentTrace(
        tenant_id=tid, conversation_id=conv.id, message_id=msg.id, step=0,
        agent_name="compass", input={}, output={}, confidence=0.9,
    )
    escalation = Escalation(
        tenant_id=tid, conversation_id=conv.id, reason="isolation test", confidence=0.4, status="open",
    )
    session.add_all([trace, escalation])
    await session.flush()

    return SeededTenant(
        id=tid, document_id=str(doc.id), chunk_id=str(chunk.id),
        conversation_id=str(conv.id), message_id=str(msg.id), trace_id=str(trace.id),
        escalation_id=str(escalation.id), order_id=str(order.id), user_id=str(user.id),
    )


async def _delete_if_exists(session: AsyncSession, slug: str) -> None:
    tid = (await session.execute(text("SELECT id FROM tenants WHERE slug = :s"), {"s": slug})).scalar()
    if tid is not None:
        await bind_tenant(session, str(tid))
        await session.execute(text("DELETE FROM tenants WHERE id = :i"), {"i": str(tid)})


@pytest_asyncio.fixture(scope="module")
async def two_tenants(
    app_sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[tuple[SeededTenant, SeededTenant]]:
    async with app_sessionmaker() as session:
        async with session.begin():
            await _delete_if_exists(session, "itest-a")
            await _delete_if_exists(session, "itest-b")

    async with app_sessionmaker() as session:
        async with session.begin():
            a = await _seed_one_tenant(session, name="Isolation Test A", slug="itest-a")
        async with session.begin():
            b = await _seed_one_tenant(session, name="Isolation Test B", slug="itest-b")

    yield a, b

    async with app_sessionmaker() as session:
        async with session.begin():
            await bind_tenant(session, a.id)
            await session.execute(text("DELETE FROM tenants WHERE id = :i"), {"i": a.id})
        async with session.begin():
            await bind_tenant(session, b.id)
            await session.execute(text("DELETE FROM tenants WHERE id = :i"), {"i": b.id})

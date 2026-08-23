from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from app.rag.retriever import search
from tests.conftest import SeededTenant, bind_tenant

pytestmark = pytest.mark.asyncio

RLS_TABLES = [
    (User, "user_id"),
    (Document, "document_id"),
    (Chunk, "chunk_id"),
    (Conversation, "conversation_id"),
    (Message, "message_id"),
    (AgentTrace, "trace_id"),
    (Escalation, "escalation_id"),
    (Order, "order_id"),
]


async def _all_rows(session: AsyncSession, model) -> list:
    return (await session.execute(select(model))).scalars().all()


class TestPositiveIsolation:

    @pytest.mark.parametrize("model,id_field", RLS_TABLES, ids=[m.__tablename__ for m, _ in RLS_TABLES])
    async def test_sees_only_own_row(self, app_sessionmaker, two_tenants, model, id_field):
        a, b = two_tenants
        async with app_sessionmaker() as session:
            async with session.begin():
                await bind_tenant(session, a.id)
                rows = await _all_rows(session, model)

        seen_ids = {str(r.id) for r in rows}
        assert getattr(a, id_field) in seen_ids, "tenant A cannot see its own row — fixture or query is broken"
        assert getattr(b, id_field) not in seen_ids, (
            f"tenant A's unfiltered SELECT on {model.__tablename__} returned tenant B's row — "
            "row-level security is not isolating this table"
        )
        assert all(str(r.tenant_id) == a.id for r in rows), (
            f"a row belonging to a THIRD tenant leaked into {model.__tablename__} — "
            "RLS is not filtering at all"
        )


class TestNoTenantBound:

    @pytest.mark.parametrize("model,_id", RLS_TABLES, ids=[m.__tablename__ for m, _ in RLS_TABLES])
    async def test_empty_tenant_setting_returns_nothing(self, app_sessionmaker, two_tenants, model, _id):
        async with app_sessionmaker() as session:
            async with session.begin():
                await bind_tenant(session, None)
                rows = await _all_rows(session, model)
        assert rows == [], (
            f"{model.__tablename__} returned {len(rows)} row(s) with no tenant bound — "
            "an unset tenant must see zero rows, not all rows"
        )


class TestVectorSearch:

    async def test_retrieval_never_returns_another_tenants_chunk(self, app_sessionmaker, two_tenants):
        a, b = two_tenants
        async with app_sessionmaker() as session:
            async with session.begin():
                await bind_tenant(session, a.id)
                results = await search(session, "isolation test content", top_k=10)

        assert results, "expected at least tenant A's own chunk back"
        assert all(r.chunk_id != b.chunk_id for r in results), (
            "vector search returned tenant B's chunk while bound to tenant A — "
            "the whole point of ADR 0001 (vectors in Postgres, not a separate "
            "vector DB) is that this cannot happen"
        )


class TestWriteIsolation:

    async def test_cannot_insert_a_row_for_another_tenant(self, app_sessionmaker, two_tenants):
        a, b = two_tenants
        async with app_sessionmaker() as session:
            async with session.begin():
                await bind_tenant(session, a.id)
                with pytest.raises(Exception, match="row-level security|new row violates"):
                    await session.execute(
                        text(
                            "INSERT INTO documents (tenant_id, title, status) "
                            "VALUES (:t, 'should be rejected', 'indexed')"
                        ),
                        {"t": b.id},
                    )
                    await session.flush()


class TestTheOneExemptTable:

    async def test_tenants_table_has_no_isolation_by_design(self, app_sessionmaker, two_tenants):
        a, b = two_tenants
        async with app_sessionmaker() as session:
            async with session.begin():
                await bind_tenant(session, None)
                rows = (await session.execute(select(Tenant.id))).scalars().all()
        ids = {str(r) for r in rows}
        assert a.id in ids and b.id in ids


class TestRoleConfiguration:

    async def test_app_role_has_no_bypass_rls(self, app_sessionmaker):
        async with app_sessionmaker() as session:
            async with session.begin():
                row = (
                    await session.execute(
                        text("SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname = current_user")
                    )
                ).one()
        assert row.rolbypassrls is False, (
            "the application role has BYPASSRLS — every row-level security "
            "policy in this database is currently being silently ignored "
            "for all application traffic"
        )
        assert row.rolsuper is False

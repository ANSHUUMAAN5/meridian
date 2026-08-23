"""The isolation proof.

Every test in this file connects as `meridian_app` — the restricted role with
no BYPASSRLS — and every positive assertion is checked with **no WHERE clause
naming a tenant**. That is deliberate and is the entire point: the guarantee
this project makes is not "the application code remembers to filter by
tenant_id", it is "the database will not return another tenant's rows even if
the application forgets to filter". A test written against a query that
already filters by tenant_id would pass trivially and prove nothing.

Week 1 found that this exact suite, run against the wrong role, passes for
the wrong reason: neondb_owner has BYPASSRLS, which overrides
FORCE ROW LEVEL SECURITY, and every one of these assertions silently
returned every tenant's data. test_app_role_has_no_bypass_rls below turns
that discovery into a permanent regression check.
"""

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

# One entry per RLS-governed table: the model, and the id field on
# SeededTenant that names a row this tenant owns in that table.
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
    """The dangerous query: no WHERE clause at all. If RLS is doing its job,
    Postgres itself narrows this to the bound tenant before any row leaves
    the database — the application never gets a chance to filter."""
    return (await session.execute(select(model))).scalars().all()


class TestPositiveIsolation:
    """Tenant A, querying with no filter, sees only tenant A's row — for
    every table that carries a tenant_id."""

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
    """A session with no tenant set sees nothing — never everything. This is
    the failure-mode check: forgetting to bind a tenant must fail closed."""

    @pytest.mark.parametrize("model,_id", RLS_TABLES, ids=[m.__tablename__ for m, _ in RLS_TABLES])
    async def test_empty_tenant_setting_returns_nothing(self, app_sessionmaker, two_tenants, model, _id):
        async with app_sessionmaker() as session:
            async with session.begin():
                await bind_tenant(session, None)  # app.current_tenant = ''
                rows = await _all_rows(session, model)
        assert rows == [], (
            f"{model.__tablename__} returned {len(rows)} row(s) with no tenant bound — "
            "an unset tenant must see zero rows, not all rows"
        )


class TestVectorSearch:
    """ADR 0001's actual claim: retrieval has no tenant filter in the query
    at all (see app/rag/retriever.py) — isolation comes entirely from RLS on
    the chunks table it selects from."""

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
    """RLS's WITH CHECK clause governs INSERT/UPDATE, not just SELECT — a
    session bound to tenant A must not be able to write a row claiming to
    belong to tenant B, even if it tries to."""

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
    """tenants itself deliberately carries no RLS policy — it is the root a
    tenant_id references, and something has to be readable before any
    tenant context exists. This test documents that as an intentional
    design choice, not an oversight: both tenants remain visible from an
    unbound session, and that is correct here specifically."""

    async def test_tenants_table_has_no_isolation_by_design(self, app_sessionmaker, two_tenants):
        a, b = two_tenants
        async with app_sessionmaker() as session:
            async with session.begin():
                await bind_tenant(session, None)
                rows = (await session.execute(select(Tenant.id))).scalars().all()
        ids = {str(r) for r in rows}
        assert a.id in ids and b.id in ids


class TestRoleConfiguration:
    """Codifies the Week 1 finding permanently: if the app role is ever
    recreated (or Neon changes a default) with BYPASSRLS set, every test
    above would start passing for the wrong reason again, silently. This
    test fails loudly instead, independent of any RLS policy."""

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

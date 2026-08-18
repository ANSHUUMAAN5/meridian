"""Async engine and session factory.

Note the pooling choice: Neon sits behind a connection pooler and suspends when
idle, so we disable SQLAlchemy's own statement cache (pgbouncer in transaction
mode cannot support prepared statements) and keep the pool small.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        s = get_settings()
        _engine = create_async_engine(
            s.database_url,
            echo=s.db_echo,
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True,          # Neon suspends when idle; revalidate
            connect_args={"statement_cache_size": 0},  # pooler-safe
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            get_engine(), expire_on_commit=False, autoflush=False
        )
    return _sessionmaker


async def raw_session() -> AsyncIterator[AsyncSession]:
    """A session with NO tenant context set.

    Only for migrations, seeding, and the isolation tests. Application request
    paths must use the tenant-scoped dependency in app.deps instead — a session
    without `app.current_tenant` set will see zero rows on every RLS table.
    """
    async with get_sessionmaker()() as session:
        yield session

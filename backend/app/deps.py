"""Request dependencies — this is where tenant isolation is switched on.

Every request that touches tenant data goes through `tenant_session`. It opens
a transaction and sets `app.current_tenant` for the life of that transaction;
the RLS policies created in migration 0001 read that setting.

Why the transaction matters: the setting is transaction-local. If the session
were not inside an explicit transaction, the value would apply to a single
implicit transaction and then vanish, and later statements in the same request
would run with no tenant set — which, by the design of the policy, returns
nothing rather than everything.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthError, decode_token
from app.db.base import get_sessionmaker

TENANT_SETTING = "app.current_tenant"


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    user_id: str
    role: str


async def current_principal(authorization: str = Header(default="")) -> Principal:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = decode_token(token)
    except AuthError as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, str(e), headers={"WWW-Authenticate": "Bearer"}
        ) from e
    return Principal(tenant_id=claims["tid"], user_id=claims["sub"], role=claims["role"])


async def set_tenant(session: AsyncSession, tenant_id: str) -> None:
    """Bind this transaction to one tenant.

    set_config(..., is_local => true) is used rather than `SET LOCAL` because
    SET LOCAL cannot take a bind parameter — it would require interpolating the
    tenant id into SQL text. Here the value travels as a parameter and is never
    parsed as SQL.
    """
    await session.execute(
        text(f"SELECT set_config('{TENANT_SETTING}', :tid, true)"),
        {"tid": str(tenant_id)},
    )


async def tenant_session(
    principal: Principal = Depends(current_principal),
) -> AsyncIterator[AsyncSession]:
    """The only session an application route should ever use."""
    async with get_sessionmaker()() as session:
        async with session.begin():          # explicit transaction — see module docstring
            await set_tenant(session, principal.tenant_id)
            yield session

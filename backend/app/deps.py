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

import asyncio
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
    """The only session an application route should ever use.

    Opening the pooled connection is retried a few times on a transient
    network/DNS failure (OSError, e.g. gaierror) before giving up. This is
    not theoretical: local Wi-Fi resolver hiccups during development produced
    this exact failure repeatedly, each one self-clearing within a second or
    two. A live deployment sees the same class of blip on the path to a
    managed Postgres host, and a single dropped resolution should not fail a
    customer's request when retrying a moment later would have worked.
    A real outage still surfaces — this gives up after 3 attempts (~1.2s).
    """
    session_cm = get_sessionmaker()()
    session = await session_cm.__aenter__()
    try:
        trans_cm = session.begin()  # explicit transaction — see module docstring
        for attempt in range(3):
            try:
                await trans_cm.__aenter__()
                break
            except OSError:
                if attempt == 2:
                    raise
                await asyncio.sleep(0.4 * (2**attempt))
                trans_cm = session.begin()
        try:
            await set_tenant(session, principal.tenant_id)
            yield session
        finally:
            await trans_cm.__aexit__(None, None, None)
    finally:
        await session_cm.__aexit__(None, None, None)

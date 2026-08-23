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
    await session.execute(
        text(f"SELECT set_config('{TENANT_SETTING}', :tid, true)"),
        {"tid": str(tenant_id)},
    )


async def tenant_session(
    principal: Principal = Depends(current_principal),
) -> AsyncIterator[AsyncSession]:
    session_cm = get_sessionmaker()()
    session = await session_cm.__aenter__()
    try:
        trans_cm = session.begin()
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

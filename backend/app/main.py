from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestrator import handle_message
from app.auth import create_token
from app.config import get_settings
from app.db.base import get_engine, get_sessionmaker
from app.db.models import Conversation, Message, Tenant, User
from app.deps import Principal, current_principal, tenant_session
from app.providers import get_provider


logger = logging.getLogger("meridian.startup")


async def _wait_for_database(attempts: int = 6, base_delay: float = 0.5) -> None:
    from sqlalchemy import text

    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            async with get_sessionmaker()() as session:
                await session.execute(text("select 1"))
            if attempt:
                logger.info("database reachable after %d retr%s", attempt, "y" if attempt == 1 else "ies")
            return
        except OSError as e:
            last_exc = e
            if attempt < attempts - 1:
                await asyncio.sleep(base_delay * (2**attempt))
    raise RuntimeError(f"database unreachable after {attempts} attempts") from last_exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _wait_for_database()
    yield
    await get_engine().dispose()


app = FastAPI(
    title="Meridian",
    version="0.1.0",
    description="Multi-tenant multi-agent customer support.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    from sqlalchemy import text

    checks: dict[str, str] = {}
    try:
        async with get_sessionmaker()() as s:
            await s.execute(text("select 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {type(e).__name__}"

    checks["llm"] = "ok" if await get_provider().healthy() else "unreachable"
    return {"status": "ok", "checks": checks}


class DemoLogin(BaseModel):
    tenant: str = Field(description="Tenant slug, e.g. 'kite'")


@app.post("/auth/demo", tags=["auth"])
async def demo_login(body: DemoLogin) -> dict:
    settings = get_settings()
    if body.tenant not in settings.demo_tenant_slugs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such demo tenant")

    async with get_sessionmaker()() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == body.tenant))
        ).scalar_one_or_none()
        if tenant is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "demo tenant not seeded")

        from sqlalchemy import text

        await session.execute(
            text("select set_config('app.current_tenant', :t, true)"), {"t": str(tenant.id)}
        )
        user = (
            await session.execute(
                select(User).where(User.tenant_id == tenant.id).order_by(User.created_at).limit(1)
            )
        ).scalar_one_or_none()

    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "demo tenant has no users")

    return {
        "access_token": create_token(
            tenant_id=str(tenant.id), user_id=str(user.id), role=user.role
        ),
        "token_type": "bearer",
        "tenant": {"id": str(tenant.id), "name": tenant.name, "slug": tenant.slug},
    }


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None
    customer_id: str | None = Field(default=None, max_length=200)


class CitationOut(BaseModel):
    index: int
    document_id: str
    document_title: str
    similarity: float


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    intent: str
    confidence: float
    agent: str
    escalated: bool
    escalation_id: str | None = None
    grounded: bool | None = None
    citations: list[CitationOut] = []
    awaiting_confirmation: bool = False


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(
    body: ChatRequest,
    principal: Principal = Depends(current_principal),
    session: AsyncSession = Depends(tenant_session),
) -> ChatResponse:
    tenant = (
        await session.execute(select(Tenant).where(Tenant.id == principal.tenant_id))
    ).scalar_one()

    if body.conversation_id:
        conversation = (
            await session.execute(
                select(Conversation).where(Conversation.id == body.conversation_id)
            )
        ).scalar_one_or_none()
        if conversation is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")
    else:
        conversation = Conversation(
            tenant_id=principal.tenant_id, external_customer_id=body.customer_id
        )
        session.add(conversation)
        await session.flush()

    customer_msg = Message(
        tenant_id=principal.tenant_id,
        conversation_id=conversation.id,
        role="customer",
        content=body.message,
    )
    session.add(customer_msg)
    await session.flush()

    result = await handle_message(
        session,
        tenant_id=principal.tenant_id,
        tenant_name=tenant.name,
        conversation=conversation,
        message_id=str(customer_msg.id),
        customer_message=body.message,
        customer_id=body.customer_id,
    )

    session.add(
        Message(
            tenant_id=principal.tenant_id,
            conversation_id=conversation.id,
            role="assistant",
            content=result.answer,
        )
    )

    return ChatResponse(
        conversation_id=str(conversation.id),
        answer=result.answer,
        intent=result.intent,
        confidence=result.confidence,
        agent=result.agent,
        escalated=result.escalated,
        escalation_id=result.escalation_id,
        grounded=result.grounded,
        awaiting_confirmation=result.awaiting_confirmation,
        citations=[
            CitationOut(
                index=c.index,
                document_id=c.document_id,
                document_title=c.document_title,
                similarity=c.similarity,
            )
            for c in result.citations
        ],
    )

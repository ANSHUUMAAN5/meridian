from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestrator import handle_message
from app.auth import create_token
from app.config import get_settings
from app.db.base import get_engine, get_sessionmaker
from app.db.models import AgentTrace, Conversation, Escalation, Message, Order, Tenant, User
from app.deps import Principal, current_principal, tenant_session
from app.providers import get_provider


logger = logging.getLogger("meridian.startup")


async def _wait_for_database(attempts: int = 6, base_delay: float = 0.5) -> None:
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

        await session.execute(
            text("select set_config('app.current_tenant', :t, true)"), {"t": str(tenant.id)}
        )
        user = (
            await session.execute(
                select(User).where(User.tenant_id == tenant.id).order_by(User.created_at).limit(1)
            )
        ).scalar_one_or_none()

        demo_customer_id = (
            await session.execute(
                select(Order.external_customer_id)
                .where(Order.tenant_id == tenant.id)
                .group_by(Order.external_customer_id)
                .order_by(func.count().desc())
                .limit(1)
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
        "customer_id": demo_customer_id,
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


class ConversationSummary(BaseModel):
    id: str
    external_customer_id: str | None
    created_at: datetime
    message_count: int
    last_message_preview: str | None
    has_open_escalation: bool


@app.get("/conversations", response_model=list[ConversationSummary], tags=["traces"])
async def list_conversations(
    principal: Principal = Depends(current_principal),
    session: AsyncSession = Depends(tenant_session),
) -> list[ConversationSummary]:
    conversations = (
        await session.execute(
            select(Conversation).order_by(Conversation.created_at.desc()).limit(50)
        )
    ).scalars().all()

    results = []
    for c in conversations:
        last_message = (
            await session.execute(
                select(Message)
                .where(Message.conversation_id == c.id)
                .order_by(Message.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        message_count = (
            await session.execute(
                select(func.count()).select_from(Message).where(Message.conversation_id == c.id)
            )
        ).scalar_one()
        open_escalation = (
            await session.execute(
                select(Escalation.id)
                .where(Escalation.conversation_id == c.id, Escalation.status.in_(("open", "claimed")))
                .limit(1)
            )
        ).scalar_one_or_none()

        results.append(
            ConversationSummary(
                id=str(c.id),
                external_customer_id=c.external_customer_id,
                created_at=c.created_at,
                message_count=message_count,
                last_message_preview=last_message.content[:140] if last_message else None,
                has_open_escalation=open_escalation is not None,
            )
        )
    return results


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class TraceStepOut(BaseModel):
    step: int
    agent_name: str
    model: str | None
    input: dict
    output: dict
    confidence: float | None
    latency_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    created_at: datetime


class ConversationDetail(BaseModel):
    id: str
    external_customer_id: str | None
    created_at: datetime
    messages: list[MessageOut]
    traces: list[TraceStepOut]


@app.get("/conversations/{conversation_id}", response_model=ConversationDetail, tags=["traces"])
async def get_conversation(
    conversation_id: str,
    principal: Principal = Depends(current_principal),
    session: AsyncSession = Depends(tenant_session),
) -> ConversationDetail:
    conversation = (
        await session.execute(select(Conversation).where(Conversation.id == conversation_id))
    ).scalar_one_or_none()
    if conversation is None:
        # RLS makes another tenant's conversation indistinguishable from a
        # nonexistent one, which is the correct thing to leak: nothing.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")

    messages = (
        await session.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
        )
    ).scalars().all()
    traces = (
        await session.execute(
            select(AgentTrace).where(AgentTrace.conversation_id == conversation_id).order_by(AgentTrace.step)
        )
    ).scalars().all()

    return ConversationDetail(
        id=str(conversation.id),
        external_customer_id=conversation.external_customer_id,
        created_at=conversation.created_at,
        messages=[
            MessageOut(id=str(m.id), role=m.role, content=m.content, created_at=m.created_at) for m in messages
        ],
        traces=[
            TraceStepOut(
                step=t.step, agent_name=t.agent_name, model=t.model, input=t.input, output=t.output,
                confidence=t.confidence, latency_ms=t.latency_ms, input_tokens=t.input_tokens,
                output_tokens=t.output_tokens, cost_usd=float(t.cost_usd) if t.cost_usd is not None else None,
                created_at=t.created_at,
            )
            for t in traces
        ],
    )


class EscalationOut(BaseModel):
    id: str
    conversation_id: str
    reason: str
    confidence: float | None
    status: str
    assigned_to: str | None
    resolution_note: str | None
    resolved_at: datetime | None
    created_at: datetime


@app.get("/escalations", response_model=list[EscalationOut], tags=["relay"])
async def list_escalations(
    status_filter: str | None = Query(default=None, alias="status"),
    principal: Principal = Depends(current_principal),
    session: AsyncSession = Depends(tenant_session),
) -> list[EscalationOut]:
    stmt = select(Escalation).order_by(Escalation.created_at.desc()).limit(100)
    if status_filter:
        stmt = stmt.where(Escalation.status == status_filter)
    escalations = (await session.execute(stmt)).scalars().all()
    return [
        EscalationOut(
            id=str(e.id), conversation_id=str(e.conversation_id), reason=e.reason,
            confidence=e.confidence, status=e.status,
            assigned_to=str(e.assigned_to) if e.assigned_to else None,
            resolution_note=e.resolution_note, resolved_at=e.resolved_at, created_at=e.created_at,
        )
        for e in escalations
    ]


async def _get_escalation_or_404(session: AsyncSession, escalation_id: str) -> Escalation:
    escalation = (
        await session.execute(select(Escalation).where(Escalation.id == escalation_id))
    ).scalar_one_or_none()
    if escalation is None:
        # RLS makes another tenant's escalation indistinguishable from a
        # nonexistent one, which is the correct thing to leak: nothing.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "escalation not found")
    return escalation


@app.post("/escalations/{escalation_id}/claim", response_model=EscalationOut, tags=["relay"])
async def claim_escalation(
    escalation_id: str,
    principal: Principal = Depends(current_principal),
    session: AsyncSession = Depends(tenant_session),
) -> EscalationOut:
    escalation = await _get_escalation_or_404(session, escalation_id)
    if escalation.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, f"escalation is already {escalation.status}")
    escalation.status = "claimed"
    escalation.assigned_to = principal.user_id
    await session.flush()
    return EscalationOut(
        id=str(escalation.id), conversation_id=str(escalation.conversation_id), reason=escalation.reason,
        confidence=escalation.confidence, status=escalation.status,
        assigned_to=str(escalation.assigned_to), resolution_note=escalation.resolution_note,
        resolved_at=escalation.resolved_at, created_at=escalation.created_at,
    )


class ResolveEscalation(BaseModel):
    resolution_note: str = Field(min_length=1, max_length=2000)


@app.post("/escalations/{escalation_id}/resolve", response_model=EscalationOut, tags=["relay"])
async def resolve_escalation(
    escalation_id: str,
    body: ResolveEscalation,
    principal: Principal = Depends(current_principal),
    session: AsyncSession = Depends(tenant_session),
) -> EscalationOut:
    escalation = await _get_escalation_or_404(session, escalation_id)
    if escalation.status == "resolved":
        raise HTTPException(status.HTTP_409_CONFLICT, "escalation is already resolved")
    escalation.status = "resolved"
    escalation.resolution_note = body.resolution_note
    escalation.resolved_at = datetime.now(UTC)
    if escalation.assigned_to is None:
        escalation.assigned_to = principal.user_id
    await session.flush()
    return EscalationOut(
        id=str(escalation.id), conversation_id=str(escalation.conversation_id), reason=escalation.reason,
        confidence=escalation.confidence, status=escalation.status,
        assigned_to=str(escalation.assigned_to), resolution_note=escalation.resolution_note,
        resolved_at=escalation.resolved_at, created_at=escalation.created_at,
    )

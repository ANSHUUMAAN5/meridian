from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentTrace, Escalation
from app.threshold import Gate

_HUMAN_REQUEST_PATTERNS = re.compile(
    r"\b(talk|speak) to (a |an )?(human|person|agent|someone)\b"
    r"|\breal (human|person|agent)\b"
    r"|\bconnect me (with|to) (a |an )?(human|person|agent)\b",
    re.IGNORECASE,
)

REPEATED_FAILURE_LIMIT = 3


def wants_human(message: str) -> bool:
    return bool(_HUMAN_REQUEST_PATTERNS.search(message))


async def should_escalate_for_repeated_failure(session: AsyncSession, conversation_id: str) -> bool:
    rows = (
        await session.execute(
            select(AgentTrace.id).where(
                AgentTrace.conversation_id == conversation_id,
                AgentTrace.agent_name == "none",
            )
        )
    ).all()
    return len(rows) >= REPEATED_FAILURE_LIMIT


async def _build_handoff_summary(session: AsyncSession, conversation_id: str, gate_reason: str) -> str:
    steps = (
        await session.execute(
            select(AgentTrace)
            .where(AgentTrace.conversation_id == conversation_id)
            .order_by(AgentTrace.step)
        )
    ).scalars().all()

    lines = [f"Reason: {gate_reason}"]
    for s in steps:
        if s.agent_name in ("threshold", "beacon"):
            continue
        detail = s.output.get("answer") or s.output.get("reasoning") or str(s.output)[:200]
        lines.append(f"- {s.agent_name}: {detail}")

    return "\n".join(lines)


@dataclass(frozen=True)
class EscalationResult:
    escalation_id: str
    customer_message: str

    @property
    def customer_reply(self) -> str:
        return (
            "I want to make sure this is handled correctly, so I'm connecting "
            "you with someone from our team who can help."
        )


async def escalate(
    session: AsyncSession,
    *,
    conversation_id: str,
    customer_message: str,
    gate: Gate,
) -> EscalationResult:
    summary = await _build_handoff_summary(session, conversation_id, gate.reason)

    row = Escalation(
        tenant_id=None,
        conversation_id=conversation_id,
        reason=summary,
        confidence=gate.confidence,
        status="open",
    )
    from sqlalchemy import text

    tenant_id = (
        await session.execute(text("select current_setting('app.current_tenant', true)"))
    ).scalar()
    if not tenant_id:
        raise RuntimeError("escalate() called without a tenant bound to the session")
    row.tenant_id = tenant_id

    session.add(row)
    await session.flush()

    return EscalationResult(escalation_id=str(row.id), customer_message=customer_message)

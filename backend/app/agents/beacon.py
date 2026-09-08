from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentTrace, Escalation
from app import replies
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
                or_(
                    AgentTrace.output["step"].astext.is_(None),
                    AgentTrace.output["step"].astext != "closing_remark",
                ),
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
    customer_reply: str


SITUATIONS = {
    "human_requested": "The customer asked to speak to a person. You are passing them to one now.",
    "hard_tier": (
        "The customer asked something this company never answers automatically, because "
        "getting it wrong could hurt them. Say plainly that this needs a qualified person, "
        "and that you are bringing one in. Do not attempt any part of the answer yourself."
    ),
    "write_tier_risk": (
        "The customer wants something changed on their account that you are not able to do "
        "on your own here. Say so, and that a colleague will pick it up."
    ),
    "ungrounded_answer": (
        "You could not find solid support for an answer in the company's own material, so "
        "you are not going to guess. Say that you would rather be sure, and that someone is "
        "taking a look."
    ),
    "repeated_failure": (
        "This conversation has gone several turns without resolving. Acknowledge that plainly "
        "and say you are bringing in a person rather than going round again."
    ),
    "low_confidence": (
        "You are not confident you understood what the customer needs well enough to act. "
        "Say you would rather someone got it right, and that you are handing it over."
    ),
}


async def escalate(
    session: AsyncSession,
    *,
    conversation_id: str,
    customer_message: str,
    gate: Gate,
    context: str | None = None,
    tenant_name: str = "this company",
    history: str = "",
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

    completion = await replies.compose(
        tenant_name=tenant_name,
        situation=SITUATIONS.get(context or "", SITUATIONS["low_confidence"]),
        customer_message=customer_message,
        history=history,
    )

    return EscalationResult(
        escalation_id=str(row.id),
        customer_message=customer_message,
        customer_reply=completion.text.strip(),
    )

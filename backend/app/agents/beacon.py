from __future__ import annotations

import random
import re
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentTrace, Escalation
from app.threshold import Gate

REPLIES_BY_CONTEXT: dict[str, tuple[str, ...]] = {
    "human_requested": (
        "Of course — connecting you with someone from our team right now.",
        "No problem at all, I'll get you a real person straight away.",
    ),
    "hard_tier": (
        "That's really a question for a pharmacist or doctor, not me — I'm bringing in our team so you get a proper answer.",
        "I can't advise on that safely myself, so let me get someone qualified to help with this one.",
    ),
    "write_tier_risk": (
        "This one needs a second pair of eyes before it happens — I'm handing it to our team now.",
        "I'd rather have a person confirm this before it goes through — connecting you now.",
    ),
    "ungrounded_answer": (
        "I couldn't find a solid answer to that in what I have access to, so let me get someone from our team who can dig in properly.",
        "I don't want to guess on this one — bringing in a person who'll actually know.",
    ),
    "repeated_failure": (
        "I don't think I'm getting you what you need here — let me hand this straight to someone on our team.",
        "Let's not go back and forth any more on this — connecting you with a person now.",
    ),
    "low_confidence": (
        "I want to make sure I get this right for you, so I'm bringing in someone from our team.",
        "I'm not fully certain on this one — let me connect you with someone who will be.",
    ),
}

_DEFAULT_REPLIES = (
    "I want to make sure this is handled correctly, so I'm connecting you with someone from our team who can help.",
)

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


def _pick_reply(context: str | None) -> str:
    bucket = REPLIES_BY_CONTEXT.get(context or "", _DEFAULT_REPLIES)
    return random.choice(bucket)


async def escalate(
    session: AsyncSession,
    *,
    conversation_id: str,
    customer_message: str,
    gate: Gate,
    context: str | None = None,
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

    return EscalationResult(
        escalation_id=str(row.id), customer_message=customer_message, customer_reply=_pick_reply(context),
    )

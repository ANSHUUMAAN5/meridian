"""Beacon — hands a case to a human. The only agent that writes to escalations.

Beacon makes no judgment call of its own — by the time it runs, Threshold has
already decided escalation is necessary (confidence too low, or a write-tier
action needing confirmation, or a hard rule). Beacon's only job is to make
that handoff useful: capture *why*, at what confidence, and leave the full
reasoning trail for the person who picks it up.

This is deliberately the smallest agent. It calls no model — there is nothing
to decide, only something to record. Compare to Threshold (app/threshold.py),
which is the same idea applied to gating: don't spend a model call on a step
that doesn't need one.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Escalation
from app.threshold import Gate


@dataclass(frozen=True)
class EscalationResult:
    escalation_id: str
    customer_message: str

    @property
    def customer_reply(self) -> str:
        """What the customer sees. Deliberately does not explain the gating
        mechanics — 'your confidence score was 0.61' means nothing to a
        customer and reads as evasive. The reasoning lives in the escalation
        record for the human, not in this reply."""
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
    row = Escalation(
        tenant_id=None,  # set by the caller's tenant-scoped session via RLS default path — see note below
        conversation_id=conversation_id,
        reason=gate.reason,
        confidence=gate.confidence,
        status="open",
    )
    # tenant_id has no default and RLS's WITH CHECK requires it to match the
    # session's bound tenant — read it back off the session's own setting
    # rather than accept it as a parameter, so Beacon cannot be called with
    # the wrong tenant's id by a caller mistake.
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

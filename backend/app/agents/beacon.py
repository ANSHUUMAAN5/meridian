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
        tenant_id=None,
        conversation_id=conversation_id,
        reason=gate.reason,
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

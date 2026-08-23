from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentTrace
from app.providers.base import Completion


@dataclass
class Trace:

    session: AsyncSession
    tenant_id: str
    conversation_id: str
    message_id: str | None = None
    _next_step: int = field(default=0, repr=False)

    async def record(
        self,
        *,
        agent_name: str,
        input: dict,
        output: dict,
        completion: Completion | None = None,
        confidence: float | None = None,
    ) -> AgentTrace:
        row = AgentTrace(
            tenant_id=self.tenant_id,
            conversation_id=self.conversation_id,
            message_id=self.message_id,
            step=self._next_step,
            agent_name=agent_name,
            model=completion.model if completion else None,
            input=input,
            output=output,
            confidence=confidence,
            latency_ms=completion.latency_ms if completion else None,
            input_tokens=completion.input_tokens if completion else None,
            output_tokens=completion.output_tokens if completion else None,
            cost_usd=completion.cost_usd if completion else None,
        )
        self.session.add(row)
        await self.session.flush()
        self._next_step += 1
        return row

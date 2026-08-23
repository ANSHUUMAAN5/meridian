"""Trace — records every agent step.

This is the observability product surface (§7 of the plan: the console's
Trace screen reads directly from agent_traces). Every agent call — Compass
classifying, Almanac answering, Manifest calling a tool, Beacon escalating —
writes one row here: which agent, which model, what it was asked, what it
decided, how confident it was, how long it took, and what it cost.

Writing happens through the same tenant-scoped session as everything else, so
a trace row is exactly as isolated as any other tenant data — a support agent
at Company A can never see Company B's traces, by the same RLS mechanism as
documents and orders.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentTrace
from app.providers.base import Completion


@dataclass
class Trace:
    """One conversation's running trace. Steps accumulate in order; each is
    written to the database as it happens, not batched at the end — so a
    trace is visible in the console while the conversation is still in
    progress, and a crash mid-conversation still leaves a partial record
    instead of nothing."""

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
        """Write one step. Returns the row in case a caller needs its id."""
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
        await self.session.flush()  # assigns row.id; keeps the transaction open
        self._next_step += 1
        return row

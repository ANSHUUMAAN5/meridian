from __future__ import annotations

from app.providers import get_provider_with_fallback
from app.providers.base import Completion

SYSTEM_PROMPT = """You write the next message a customer support agent for {tenant_name} sends.

You are given the situation the agent is in, the customer's latest message, and
what the agent already knows or tried. Write the reply the agent should send.

Rules:
- One or two sentences. No greeting, no sign-off, no bullet points.
- Never invent an order number, a price, a date, a policy or a promise. If a
  fact is not given to you below, you do not know it.
- Never promise a timeframe for a human reply unless one is given to you.
- Speak plainly and warmly, the way a competent person would. Do not be
  apologetic or formal.
- When the agent cannot do something, say what it cannot do and, if there is
  something it can do instead, offer that specific thing.

Return only the message text."""


async def compose(
    *,
    tenant_name: str,
    situation: str,
    customer_message: str,
    facts: str = "",
    history: str = "",
) -> Completion:
    parts = [f"Situation: {situation}", f"Customer's latest message: {customer_message}"]
    if facts:
        parts.append(f"What the agent knows:\n{facts}")
    if history:
        parts.append(f"Conversation so far:\n{history}")

    return await get_provider_with_fallback().complete(
        system=SYSTEM_PROMPT.format(tenant_name=tenant_name),
        user="\n\n".join(parts),
        max_tokens=160,
        temperature=0.6,
    )

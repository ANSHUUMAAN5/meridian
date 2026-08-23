from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, Escalation, Message
from app.rag.embedder import count_tokens

DEFAULT_HISTORY_LIMIT = 8
DEFAULT_HISTORY_TOKEN_BUDGET = 1500
RECENT_CONVERSATION_WINDOW_DAYS = 7
RECENT_CONVERSATION_DIGEST_MESSAGES = 3


async def load_recent_messages(
    session: AsyncSession,
    conversation_id: str,
    *,
    exclude_message_id: str | None,
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    if exclude_message_id:
        stmt = stmt.where(Message.id != exclude_message_id)
    rows = (await session.execute(stmt)).scalars().all()
    return list(reversed(rows))


def format_messages(messages: list[Message], *, token_budget: int = DEFAULT_HISTORY_TOKEN_BUDGET) -> str:
    if not messages:
        return ""

    lines = [f"{'Customer' if m.role == 'customer' else 'Assistant'}: {m.content}" for m in messages]

    while lines and count_tokens("\n".join(lines)) > token_budget:
        lines.pop(0)

    if not lines:
        return ""

    return "Conversation so far:\n" + "\n".join(lines)


async def load_customer_context(
    session: AsyncSession, conversation: Conversation, *, exclude_conversation_id: str
) -> str:
    if not conversation.external_customer_id:
        return ""

    open_escalation = (
        await session.execute(
            select(Escalation)
            .join(Conversation, Conversation.id == Escalation.conversation_id)
            .where(
                Conversation.external_customer_id == conversation.external_customer_id,
                Conversation.id != exclude_conversation_id,
                Escalation.status.in_(("open", "claimed")),
            )
            .order_by(Escalation.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    parts: list[str] = []
    if open_escalation is not None:
        parts.append(
            f"Note: this customer has an unresolved open case from a previous conversation "
            f"(reason: {open_escalation.reason[:200]})."
        )

    cutoff = datetime.now(UTC) - timedelta(days=RECENT_CONVERSATION_WINDOW_DAYS)
    prior_conversation = (
        await session.execute(
            select(Conversation)
            .where(
                Conversation.external_customer_id == conversation.external_customer_id,
                Conversation.id != exclude_conversation_id,
                Conversation.created_at >= cutoff,
            )
            .order_by(Conversation.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if prior_conversation is not None:
        prior_messages = await load_recent_messages(
            session,
            str(prior_conversation.id),
            exclude_message_id=None,
            limit=RECENT_CONVERSATION_DIGEST_MESSAGES,
        )
        digest = format_messages(prior_messages, token_budget=400)
        if digest:
            parts.append(f"This customer also had a recent, separate conversation:\n{digest}")

    return "\n\n".join(parts)


async def build_history_block(
    session: AsyncSession, conversation: Conversation, *, exclude_message_id: str | None
) -> str:
    within_thread = format_messages(
        await load_recent_messages(session, str(conversation.id), exclude_message_id=exclude_message_id)
    )
    cross_conversation = await load_customer_context(
        session, conversation, exclude_conversation_id=str(conversation.id)
    )

    parts = [p for p in (cross_conversation, within_thread) if p]
    return "\n\n".join(parts)

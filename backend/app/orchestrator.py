from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import almanac, beacon, compass, manifest, sentinel
from app.agents.almanac import Citation
from app.db.models import Conversation
from app.history import build_history_block
from app.threshold import Gate, RiskTier, Verdict, evaluate
from app.trace import Trace

DOCUMENT_INTENTS = {"policy_question"}
ORDER_INTENTS = {"order_status"}
WRITE_INTENTS = {"cancel_order", "refund_request", "change_address"}

FIXED_REPLIES = {
    "out_of_scope": "That's not something we handle here — is there anything else I can help with?",
    "ambiguous": "I want to make sure I help with the right thing — could you say a bit more about what you need?",
}

CLOSING_REPLY = "You're welcome — glad I could help. Let me know if there's anything else."

_CLOSING_PHRASES = (
    "ok", "okay", "ok thanks", "okay thanks", "ok thank you", "okay thank you",
    "ok thankyou", "okay thankyou", "thanks", "thank you", "thankyou",
    "thanks a lot", "thank you so much", "great thanks", "perfect thanks",
    "cool thanks", "alright thanks", "sounds good", "sounds good thanks",
    "no need", "that's all", "thats all", "that's it", "thats it",
    "nothing else", "got it", "got it thanks", "bye", "goodbye", "all good",
)


def _is_closing_remark(message: str) -> bool:
    normalized = message.strip().lower().rstrip(".!")
    return normalized in _CLOSING_PHRASES


@dataclass(frozen=True)
class OrchestrationResult:
    answer: str
    intent: str
    confidence: float
    agent: str
    escalated: bool
    escalation_id: str | None = None
    citations: list[Citation] = field(default_factory=list)
    grounded: bool | None = None
    awaiting_confirmation: bool = False


async def handle_message(
    session: AsyncSession,
    *,
    tenant_id: str,
    tenant_name: str,
    conversation: Conversation,
    message_id: str | None,
    customer_message: str,
    customer_id: str | None = None,
) -> OrchestrationResult:
    conversation_id = str(conversation.id)
    trace = Trace(
        session=session, tenant_id=tenant_id, conversation_id=conversation_id, message_id=message_id
    )

    if beacon.wants_human(customer_message):
        return await _escalate(
            session, trace, conversation_id, customer_message,
            Gate(
                verdict=Verdict.ESCALATE, reason="customer explicitly asked for a human",
                tier=RiskTier.READ, confidence=1.0, threshold=0.0,
            ),
            intent="human_requested", confidence=1.0, context="human_requested",
        )

    if conversation.pending_action:
        result = await _handle_pending_action(session, trace, conversation, customer_message, tenant_name)
        if result is not None:
            return result

    if _is_closing_remark(customer_message):
        await trace.record(
            agent_name="none",
            input={"message": customer_message},
            output={"step": "closing_remark", "answer": CLOSING_REPLY},
        )
        return OrchestrationResult(
            answer=CLOSING_REPLY, intent="closing_remark", confidence=1.0, agent="none", escalated=False,
        )

    history = await build_history_block(session, conversation, exclude_message_id=message_id)

    decision = await compass.classify(customer_message, tenant_name=tenant_name, history=history)
    await trace.record(
        agent_name="compass",
        input={"message": customer_message},
        output={
            "intent": decision.intent, "reasoning": decision.reasoning,
            "sentiment": decision.sentiment, "urgency": decision.urgency, "order_number": decision.order_number,
        },
        completion=decision.completion,
        confidence=decision.confidence,
    )

    routing_gate = evaluate(intent=decision.intent, confidence=decision.confidence, is_routing_step=True)
    await trace.record(
        agent_name="threshold",
        input={"intent": decision.intent, "confidence": decision.confidence, "step": "routing"},
        output={"verdict": routing_gate.verdict.value, "reason": routing_gate.reason, "tier": routing_gate.tier.value},
    )

    if routing_gate.verdict is Verdict.ESCALATE:
        return await _escalate(
            session, trace, conversation_id, customer_message, routing_gate,
            intent=decision.intent, confidence=decision.confidence,
            context="hard_tier" if routing_gate.tier is RiskTier.HARD else "low_confidence",
        )

    if routing_gate.verdict is Verdict.CONFIRM:
        return await _propose(session, trace, conversation, customer_message, decision)

    if decision.intent in DOCUMENT_INTENTS:
        return await _run_almanac(
            session, trace, conversation_id, customer_message, tenant_name, decision, history
        )

    if decision.intent in ORDER_INTENTS:
        answer = await manifest.answer_question(
            session, customer_message, tenant_name=tenant_name, customer_id=customer_id,
            order_number_hint=decision.order_number, history=history,
        )
        await trace.record(
            agent_name="manifest",
            input={"question": customer_message, "customer_id": customer_id},
            output={
                "answer": answer.text, "tool_calls": [c.name for c in answer.tool_calls],
                "grounded": answer.grounded,
            },
            completion=answer.completion,
        )
        answer_gate = evaluate(
            intent=decision.intent, confidence=1.0 if answer.grounded else 0.0, is_routing_step=False
        )
        await trace.record(
            agent_name="threshold",
            input={"grounded": answer.grounded, "step": "answer"},
            output={"verdict": answer_gate.verdict.value, "reason": answer_gate.reason},
        )
        if answer_gate.verdict is Verdict.ESCALATE:
            return await _escalate(
                session, trace, conversation_id, customer_message, answer_gate,
                intent=decision.intent, confidence=decision.confidence, context="ungrounded_answer",
            )
        return OrchestrationResult(
            answer=answer.text, intent=decision.intent, confidence=decision.confidence,
            agent="manifest", escalated=False,
        )

    if await beacon.should_escalate_for_repeated_failure(session, conversation_id):
        return await _escalate(
            session, trace, conversation_id, customer_message,
            Gate(
                verdict=Verdict.ESCALATE, reason="repeated unresolved messages in this conversation",
                tier=RiskTier.READ, confidence=decision.confidence, threshold=0.0,
            ),
            intent=decision.intent, confidence=decision.confidence, context="repeated_failure",
        )

    await trace.record(
        agent_name="none",
        input={"intent": decision.intent},
        output={"answer": FIXED_REPLIES[decision.intent]},
    )
    return OrchestrationResult(
        answer=FIXED_REPLIES[decision.intent], intent=decision.intent,
        confidence=decision.confidence, agent="none", escalated=False,
    )


async def _handle_pending_action(
    session, trace, conversation: Conversation, customer_message: str, tenant_name: str
) -> OrchestrationResult | None:
    pending = conversation.pending_action
    pending_intent = pending.get("intent", "unknown")

    if datetime.now(UTC) > conversation.pending_action_expires_at:
        await trace.record(
            agent_name="sentinel", input={"step": "expire"}, output={"step": "expire", "pending_action": pending},
        )
        conversation.pending_action = None
        conversation.pending_action_expires_at = None
        return None

    verdict = sentinel.classify_confirmation(customer_message)

    if verdict == "suspicious":
        await trace.record(agent_name="sentinel", input={"step": "suspicious"}, output={"step": "suspicious"})
        conversation.pending_action = None
        conversation.pending_action_expires_at = None
        return await _escalate(
            session, trace, str(conversation.id), customer_message,
            Gate(
                verdict=Verdict.ESCALATE, reason="injection-shaped reply to a pending confirmation",
                tier=RiskTier.WRITE, confidence=0.0, threshold=1.0,
            ),
            intent=pending_intent, confidence=0.0, context="write_tier_risk",
        )

    if verdict == "unclear":
        verdict = await sentinel.classify_confirmation_llm(pending, customer_message, tenant_name=tenant_name)

    if verdict == "unrelated":
        await trace.record(agent_name="sentinel", input={"step": "unrelated"}, output={"step": "unrelated"})
        conversation.pending_action = None
        conversation.pending_action_expires_at = None
        return None

    if verdict == "deny":
        await trace.record(agent_name="sentinel", input={"step": "deny"}, output={"step": "deny", "pending_action": pending})
        conversation.pending_action = None
        conversation.pending_action_expires_at = None
        return OrchestrationResult(
            answer="No problem — I won't go ahead with that. Is there anything else I can help with?",
            intent=pending_intent, confidence=1.0, agent="sentinel", escalated=False,
        )

    result = await sentinel.execute_action(session, conversation)
    await trace.record(
        agent_name="sentinel",
        input={"step": "execute", "pending_action": pending},
        output={"step": "execute", "order_number": result.order_number, "action": result.action},
    )
    return OrchestrationResult(
        answer=result.reply, intent=pending_intent, confidence=1.0, agent="sentinel", escalated=False,
    )


async def _propose(session, trace, conversation: Conversation, customer_message: str, decision) -> OrchestrationResult:
    result = await sentinel.propose_action(
        session, conversation, intent=decision.intent, order_number_hint=decision.order_number,
        customer_id=conversation.external_customer_id,
    )
    await trace.record(
        agent_name="sentinel",
        input={"intent": decision.intent, "order_number_hint": decision.order_number},
        output={
            "step": "propose", "escalate": result.escalate,
            "pending_action": result.pending_action, "reason": result.escalate_reason,
        },
    )
    if result.escalate:
        return await _escalate(
            session, trace, str(conversation.id), customer_message,
            Gate(
                verdict=Verdict.ESCALATE,
                reason=result.escalate_reason or "write-tier proposal could not be completed automatically",
                tier=RiskTier.WRITE, confidence=decision.confidence, threshold=1.0,
            ),
            intent=decision.intent, confidence=decision.confidence, context="write_tier_risk",
        )
    return OrchestrationResult(
        answer=result.reply, intent=decision.intent, confidence=decision.confidence,
        agent="sentinel", escalated=False, awaiting_confirmation=True,
    )


async def _run_almanac(session, trace, conversation_id, customer_message, tenant_name, decision, history: str = ""):
    answer = await almanac.answer_question(session, customer_message, tenant_name=tenant_name, history=history)
    await trace.record(
        agent_name="almanac",
        input={"question": customer_message},
        output={
            "answer": answer.text,
            "citations": [c.document_title for c in answer.citations],
            "grounded": answer.grounded,
        },
        completion=answer.completion,
    )

    answer_gate = evaluate(intent=decision.intent, confidence=1.0 if answer.grounded else 0.0, is_routing_step=False)
    await trace.record(
        agent_name="threshold",
        input={"grounded": answer.grounded, "step": "answer"},
        output={"verdict": answer_gate.verdict.value, "reason": answer_gate.reason},
    )
    if answer_gate.verdict is Verdict.ESCALATE:
        return await _escalate(
            session, trace, conversation_id, customer_message, answer_gate,
            intent=decision.intent, confidence=decision.confidence, context="ungrounded_answer",
        )

    return OrchestrationResult(
        answer=answer.text, intent=decision.intent, confidence=decision.confidence,
        agent="almanac", escalated=False, citations=answer.citations, grounded=answer.grounded,
    )


async def _escalate(
    session, trace, conversation_id, customer_message, gate: Gate, *,
    intent: str, confidence: float, context: str | None = None,
) -> OrchestrationResult:
    result = await beacon.escalate(
        session, conversation_id=conversation_id, customer_message=customer_message, gate=gate, context=context,
    )
    await trace.record(
        agent_name="beacon",
        input={"gate_reason": gate.reason, "tier": gate.tier.value},
        output={"escalation_id": result.escalation_id},
    )
    return OrchestrationResult(
        answer=result.customer_reply, intent=intent, confidence=confidence,
        agent="beacon", escalated=True, escalation_id=result.escalation_id,
    )

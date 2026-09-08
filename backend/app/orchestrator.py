from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app import replies
from app.agents import almanac, beacon, compass, manifest, sentinel
from app.agents.almanac import Citation
from app.db.models import Conversation
from app.history import build_history_block
from app.threshold import Gate, RiskTier, Verdict, evaluate
from app.trace import Trace

DOCUMENT_INTENTS = {"policy_question"}
ORDER_INTENTS = {"order_status"}
WRITE_INTENTS = {"cancel_order", "refund_request", "exchange_order", "change_address"}

SITUATIONS = {
    "out_of_scope": (
        "The customer asked for something this company does not deal with at all. "
        "Tell them it is outside what you handle here, without being dismissive."
    ),
    "ambiguous": (
        "You could not work out what the customer actually needs. Ask them one "
        "specific question that would let you help."
    ),
    "closing_remark": (
        "The customer is signing off or thanking you at the end of a conversation. "
        "Acknowledge it briefly and leave the door open."
    ),
}


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
            tenant_name=tenant_name,
        )

    carried_order_number = (conversation.pending_action or {}).get("order_number")
    if conversation.pending_action:
        result = await _handle_pending_action(
            session, trace, conversation, customer_message, tenant_name, message_id
        )
        if result is not None:
            return result

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
            tenant_name=tenant_name, history=history,
        )

    if routing_gate.verdict is Verdict.CONFIRM:
        return await _propose(
            session, trace, conversation, customer_message, decision,
            tenant_name=tenant_name, history=history, fallback_order_number=carried_order_number,
        )

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
                tenant_name=tenant_name, history=history,
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
            tenant_name=tenant_name, history=history,
        )

    completion = await replies.compose(
        tenant_name=tenant_name,
        situation=SITUATIONS.get(decision.intent, SITUATIONS["ambiguous"]),
        customer_message=customer_message,
        history=history,
    )
    await trace.record(
        agent_name="none",
        input={"intent": decision.intent},
        output={"step": decision.intent, "answer": completion.text},
        completion=completion,
    )
    return OrchestrationResult(
        answer=completion.text.strip(), intent=decision.intent,
        confidence=decision.confidence, agent="none", escalated=False,
    )


async def _handle_pending_action(
    session, trace, conversation: Conversation, customer_message: str, tenant_name: str,
    message_id: str | None = None,
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

    history = await build_history_block(session, conversation, exclude_message_id=message_id)
    verdict = await sentinel.classify_confirmation(
        pending, customer_message, tenant_name=tenant_name, history=history
    )

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
            tenant_name=tenant_name, history=history,
        )

    if verdict in ("unrelated", "changed_mind"):
        await trace.record(
            agent_name="sentinel",
            input={"step": verdict},
            output={"step": verdict, "pending_action": pending, "dropped": True},
        )
        conversation.pending_action = None
        conversation.pending_action_expires_at = None
        return None

    if verdict == "decline":
        await trace.record(agent_name="sentinel", input={"step": "decline"}, output={"step": "decline", "pending_action": pending})
        conversation.pending_action = None
        conversation.pending_action_expires_at = None
        completion = await replies.compose(
            tenant_name=tenant_name,
            situation=(
                "The customer turned down the action you offered to take. Confirm you "
                "have not done it, and invite them to say what they would like instead."
            ),
            customer_message=customer_message,
            facts=f"The action you offered and did not carry out: {pending}",
            history=history,
        )
        return OrchestrationResult(
            answer=completion.text.strip(),
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


async def _propose(
    session, trace, conversation: Conversation, customer_message: str, decision, *,
    tenant_name: str = "this company", history: str = "", fallback_order_number: str | None = None,
) -> OrchestrationResult:
    result = await sentinel.propose_action(
        session, conversation, intent=decision.intent,
        order_number_hint=decision.order_number or fallback_order_number,
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
            tenant_name=tenant_name, history=history,
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
    tenant_name: str = "this company", history: str = "",
) -> OrchestrationResult:
    result = await beacon.escalate(
        session, conversation_id=conversation_id, customer_message=customer_message, gate=gate,
        context=context, tenant_name=tenant_name, history=history,
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

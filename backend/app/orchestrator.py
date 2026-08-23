from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import almanac, beacon, compass, manifest
from app.agents.almanac import Citation
from app.threshold import Verdict, evaluate
from app.trace import Trace

DOCUMENT_INTENTS = {"policy_question"}
ORDER_INTENTS = {"order_status"}
WRITE_INTENTS = {"cancel_order", "refund_request", "change_address"}

FIXED_REPLIES = {
    "out_of_scope": "That's not something we handle here — is there anything else I can help with?",
    "ambiguous": "I want to make sure I help with the right thing — could you say a bit more about what you need?",
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


async def handle_message(
    session: AsyncSession,
    *,
    tenant_id: str,
    tenant_name: str,
    conversation_id: str,
    message_id: str | None,
    customer_message: str,
    customer_id: str | None = None,
) -> OrchestrationResult:
    trace = Trace(
        session=session, tenant_id=tenant_id, conversation_id=conversation_id, message_id=message_id
    )

    decision = await compass.classify(customer_message, tenant_name=tenant_name)
    await trace.record(
        agent_name="compass",
        input={"message": customer_message},
        output={"intent": decision.intent, "reasoning": decision.reasoning},
        completion=decision.completion,
        confidence=decision.confidence,
    )

    routing_gate = evaluate(intent=decision.intent, confidence=decision.confidence, is_routing_step=True)
    await trace.record(
        agent_name="threshold",
        input={"intent": decision.intent, "confidence": decision.confidence, "step": "routing"},
        output={"verdict": routing_gate.verdict.value, "reason": routing_gate.reason, "tier": routing_gate.tier.value},
    )

    if routing_gate.verdict in (Verdict.ESCALATE, Verdict.CONFIRM):
        return await _escalate(session, trace, conversation_id, customer_message, routing_gate, decision)

    if decision.intent in DOCUMENT_INTENTS:
        return await _run_almanac(
            session, trace, conversation_id, customer_message, tenant_name, decision, routing_gate
        )

    if decision.intent in ORDER_INTENTS:
        answer = await manifest.answer_question(
            session, customer_message, tenant_name=tenant_name, customer_id=customer_id
        )
        await trace.record(
            agent_name="manifest",
            input={"question": customer_message, "customer_id": customer_id},
            output={"answer": answer.text, "tool_calls": [c.name for c in answer.tool_calls]},
            completion=answer.completion,
        )
        return OrchestrationResult(
            answer=answer.text, intent=decision.intent, confidence=decision.confidence,
            agent="manifest", escalated=False,
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


async def _run_almanac(session, trace, conversation_id, customer_message, tenant_name, decision, routing_gate):
    answer = await almanac.answer_question(session, customer_message, tenant_name=tenant_name)
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
        return await _escalate(session, trace, conversation_id, customer_message, answer_gate, decision)

    return OrchestrationResult(
        answer=answer.text, intent=decision.intent, confidence=decision.confidence,
        agent="almanac", escalated=False, citations=answer.citations, grounded=answer.grounded,
    )


async def _escalate(session, trace, conversation_id, customer_message, gate, decision) -> OrchestrationResult:
    result = await beacon.escalate(
        session, conversation_id=conversation_id, customer_message=customer_message, gate=gate
    )
    await trace.record(
        agent_name="beacon",
        input={"gate_reason": gate.reason, "tier": gate.tier.value},
        output={"escalation_id": result.escalation_id},
    )
    return OrchestrationResult(
        answer=result.customer_reply, intent=decision.intent, confidence=decision.confidence,
        agent="beacon", escalated=True, escalation_id=result.escalation_id,
    )

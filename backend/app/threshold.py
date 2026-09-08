from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.config import get_settings


class RiskTier(str, Enum):
    READ = "read"
    WRITE = "write"
    HARD = "hard"


class Verdict(str, Enum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    ESCALATE = "escalate"


RISK_TIERS: dict[str, RiskTier] = {
    "policy_question": RiskTier.READ,
    "order_status": RiskTier.READ,
    "cancel_order": RiskTier.WRITE,
    "refund_request": RiskTier.WRITE,
    "exchange_order": RiskTier.WRITE,
    "change_address": RiskTier.WRITE,
    "out_of_scope": RiskTier.READ,
    "ambiguous": RiskTier.READ,
    "closing_remark": RiskTier.READ,
    "medical_question": RiskTier.HARD,
}


@dataclass(frozen=True)
class Gate:
    verdict: Verdict
    reason: str
    tier: RiskTier
    confidence: float
    threshold: float


def tier_for(intent: str) -> RiskTier:
    return RISK_TIERS.get(intent, RiskTier.WRITE)


def evaluate(
    *, intent: str, confidence: float, is_routing_step: bool = True
) -> Gate:
    settings = get_settings()
    threshold = settings.tau_route if is_routing_step else settings.tau_answer
    tier = tier_for(intent)

    if tier is RiskTier.HARD:
        return Gate(
            verdict=Verdict.ESCALATE,
            reason=f"{intent} is always reviewed by a person, regardless of confidence",
            tier=tier,
            confidence=confidence,
            threshold=threshold,
        )

    if confidence < threshold:
        return Gate(
            verdict=Verdict.ESCALATE,
            reason=f"confidence {confidence:.2f} below threshold {threshold:.2f}",
            tier=tier,
            confidence=confidence,
            threshold=threshold,
        )

    if tier is RiskTier.WRITE:
        return Gate(
            verdict=Verdict.CONFIRM,
            reason=f"write-tier action ({intent}) requires explicit confirmation",
            tier=tier,
            confidence=confidence,
            threshold=threshold,
        )

    return Gate(
        verdict=Verdict.ALLOW,
        reason=f"confidence {confidence:.2f} >= {threshold:.2f}, read-tier",
        tier=tier,
        confidence=confidence,
        threshold=threshold,
    )

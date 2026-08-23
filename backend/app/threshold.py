"""Threshold — the confidence gate. Deliberately not an agent.

This file has no model calls in it anywhere. That is the point (§6.2 of the
plan): deciding "is this number big enough to act on" is a comparison, and a
comparison should be the same answer every time, fast, free, and unit-testable
without a network call. Putting it behind an LLM would make the single most
security-relevant decision in the system slower, more expensive, and
non-deterministic for no benefit.

Two independent checks, both must pass for autonomous action:
  1. Is the model confident enough?           (a number, from Compass)
  2. Is this kind of action even allowed to
     happen without a human, ever?            (a fixed rule, from RISK_TIERS)

A very confident model is still not allowed to autonomously approve a refund.
Confidence answers "is the model probably right"; risk tier answers "does
being right even matter enough to skip a human". They are different
questions, so they are two separate checks, not one blended score.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.config import get_settings


class RiskTier(str, Enum):
    READ = "read"    # answering a question, looking something up — reversible
    WRITE = "write"   # cancelling, refunding, changing an address — not reversible


class Verdict(str, Enum):
    ALLOW = "allow"          # act autonomously
    CONFIRM = "confirm"      # act, but only after the customer explicitly confirms
    ESCALATE = "escalate"    # hand to a human; do not act


# Every intent Compass can output maps to exactly one tier. New intents added
# later must be added here explicitly — there is no default, on purpose: an
# intent nobody classified is safer to escalate than to silently allow.
RISK_TIERS: dict[str, RiskTier] = {
    "policy_question": RiskTier.READ,
    "order_status": RiskTier.READ,
    "cancel_order": RiskTier.WRITE,
    "refund_request": RiskTier.WRITE,
    "change_address": RiskTier.WRITE,
    "out_of_scope": RiskTier.READ,   # answering "I can't help with that" is safe
    "ambiguous": RiskTier.READ,      # nothing to act on yet
}


@dataclass(frozen=True)
class Gate:
    verdict: Verdict
    reason: str
    tier: RiskTier
    confidence: float
    threshold: float


def tier_for(intent: str) -> RiskTier:
    """Unknown intent -> WRITE (the more cautious tier), not a crash and not
    silent READ access. An intent Compass invents that we have not reviewed
    should never be treated as automatically safe."""
    return RISK_TIERS.get(intent, RiskTier.WRITE)


def evaluate(
    *, intent: str, confidence: float, is_routing_step: bool = True
) -> Gate:
    """The gate. Called once after Compass routes, and again after the
    specialist answers — routing confidence and answer confidence are
    different failure modes (a right specialist can give a wrong answer),
    so both are checked independently rather than only the first.
    """
    settings = get_settings()
    threshold = settings.tau_route if is_routing_step else settings.tau_answer
    tier = tier_for(intent)

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

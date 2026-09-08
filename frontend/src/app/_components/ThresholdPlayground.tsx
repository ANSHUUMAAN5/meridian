"use client";

import { useState } from "react";
import { motion } from "framer-motion";

type Case = {
  message: string;
  tenant: string;
  intent: string;
  confidence: number;
  tier: "read" | "write" | "hard";
};

const CASES: Case[] = [
  { message: "cancel my order NH4406", tenant: "Nimbus", intent: "cancel_order", confidence: 0.99, tier: "write" },
  { message: "what are your pharmacist hours", tenant: "Nimbus", intent: "policy_question", confidence: 0.95, tier: "read" },
  { message: "can I take double the dose if I missed yesterday", tenant: "Nimbus", intent: "medical_question", confidence: 0.95, tier: "hard" },
  { message: "I want a refund for order KC4403", tenant: "Kite", intent: "refund_request", confidence: 0.95, tier: "write" },
  { message: "do you sell laptops", tenant: "Kite", intent: "out_of_scope", confidence: 0.9, tier: "read" },
  { message: "who is your CEO", tenant: "Kite", intent: "policy_question", confidence: 0.85, tier: "read" },
  { message: "do you sell protein powder", tenant: "Nimbus", intent: "out_of_scope", confidence: 0.8, tier: "read" },
  { message: "you people ruined my daughter's birthday present", tenant: "Kite", intent: "ambiguous", confidence: 0.3, tier: "read" },
  { message: "asdkjfh random gibberish message that means nothing", tenant: "Kite", intent: "ambiguous", confidence: 0.2, tier: "read" },
];

function outcome(c: Case, tau: number): { label: string; color: string; why: string } {
  if (c.tier === "hard") {
    return { label: "human", color: "var(--danger)", why: "hard rule — never automated" };
  }
  if (c.confidence < tau) {
    return { label: "human", color: "var(--beacon)", why: "below the line" };
  }
  if (c.tier === "write") {
    return { label: "confirm first", color: "var(--compass)", why: "write action — needs your yes" };
  }
  return { label: "answered", color: "var(--manifest)", why: "cleared the line" };
}

export default function ThresholdPlayground() {
  const [tau, setTau] = useState(0.75);

  const answered = CASES.filter((c) => outcome(c, tau).label === "answered").length;
  const confirmed = CASES.filter((c) => outcome(c, tau).label === "confirm first").length;
  const human = CASES.filter((c) => outcome(c, tau).label === "human").length;

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface">
      <div className="border-b border-line px-5 py-5">
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <label htmlFor="tau" className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-faint-text">
            drag the line — τ_route
          </label>
          <span className="font-mono text-2xl tabular-nums text-text">{tau.toFixed(2)}</span>
        </div>

        <input
          id="tau"
          type="range"
          min={0.2}
          max={0.99}
          step={0.01}
          value={tau}
          onChange={(e) => setTau(parseFloat(e.target.value))}
          className="w-full accent-[var(--text)]"
        />

        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 font-mono text-[11px]">
          <span style={{ color: "var(--manifest)" }}>{answered} answered alone</span>
          <span style={{ color: "var(--compass)" }}>{confirmed} need confirmation</span>
          <span style={{ color: "var(--beacon)" }}>{human} go to a human</span>
        </div>
      </div>

      <div className="flex flex-col divide-y divide-[var(--line)]">
        {CASES.map((c) => {
          const o = outcome(c, tau);
          return (
            <div key={c.message} className="flex items-center gap-3 px-5 py-3">
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13.5px] text-text">{c.message}</p>
                <p className="font-mono text-[10.5px] text-faint-text">
                  {c.tenant} · {c.intent} · {c.tier} tier
                </p>
              </div>

              <span className="shrink-0 font-mono text-[12px] tabular-nums text-muted-text">
                {c.confidence.toFixed(2)}
              </span>

              <motion.span
                layout
                className="w-[112px] shrink-0 rounded-full border px-2 py-1 text-center font-mono text-[10px]"
                style={{
                  color: o.color,
                  borderColor: `color-mix(in srgb, ${o.color} 35%, transparent)`,
                  background: `color-mix(in srgb, ${o.color} 12%, transparent)`,
                }}
                title={o.why}
              >
                {o.label}
              </motion.span>
            </div>
          );
        })}
      </div>

      <p className="border-t border-line px-5 py-4 text-[13px] leading-relaxed text-muted-text">
        Notice the medical question. It scores <span className="font-mono text-text">0.95</span> — higher
        than most things the system answers on its own — and it still goes to a human at every setting on
        that slider. Confidence decides whether the model is probably right. Risk tier decides whether
        being probably right is good enough.
      </p>
    </div>
  );
}

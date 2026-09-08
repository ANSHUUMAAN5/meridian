"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { TAU_ROUTE, agentStyle } from "@/lib/agents";

type LoopStep = {
  message: string;
  confidence: number;
  outcome: "answered" | "escalated";
  agent: "manifest" | "beacon";
  detail: string;
  tool?: string;
  answer: string;
};

const LOOPS: LoopStep[] = [
  {
    message: "where is my order #4471",
    confidence: 0.94,
    outcome: "answered",
    agent: "manifest",
    detail: "0.94 ≥ τ_route — routed autonomously",
    tool: 'get_order_status(order_number="4471")',
    answer: "Order #4471 — shipped, arriving Thursday.",
  },
  {
    message: "this is unacceptable i want my money back now",
    confidence: 0.58,
    outcome: "escalated",
    agent: "beacon",
    detail: "0.58 < τ_route — stops below the line",
    answer: "Connecting you with someone who can help.",
  },
];

const STEP_MS = 1500;
const HOLD_MS = 2600;

export default function HeroRouting() {
  const [loopIndex, setLoopIndex] = useState(0);
  const [phase, setPhase] = useState(0);
  const loop = LOOPS[loopIndex];
  const maxPhase = 4;

  useEffect(() => {
    const t = setTimeout(
      () => {
        if (phase < maxPhase) {
          setPhase((p) => p + 1);
        } else {
          setPhase(0);
          setLoopIndex((i) => (i + 1) % LOOPS.length);
        }
      },
      phase === maxPhase ? HOLD_MS : STEP_MS,
    );
    return () => clearTimeout(t);
  }, [phase, loopIndex]);

  const style = agentStyle(loop.agent);
  const fillPct = phase >= 2 ? loop.confidence * 100 : 0;

  return (
    <div className="mx-auto w-full max-w-xl rounded-2xl border border-line bg-surface/80 p-5 backdrop-blur-sm">
      <div className="mb-4 flex items-center justify-between">
        <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-faint-text">live routing demo</p>
        <div className="flex gap-1">
          {LOOPS.map((_, i) => (
            <span
              key={i}
              className="h-1 w-4 rounded-full transition-colors"
              style={{ background: i === loopIndex ? "var(--compass)" : "var(--line)" }}
            />
          ))}
        </div>
      </div>

      <div className="min-h-[220px]">
        <AnimatePresence mode="wait">
          <motion.div
            key={`${loopIndex}-msg`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="mb-4 flex justify-end"
          >
            <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-compass px-3.5 py-2 text-[13.5px] text-white">
              {loop.message}
            </div>
          </motion.div>
        </AnimatePresence>

        <div className="mb-4 flex items-center gap-2">
          <motion.span
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: "var(--compass)" }}
            animate={phase < 2 ? { opacity: [0.3, 1, 0.3] } : { opacity: 1 }}
            transition={{ duration: 0.9, repeat: phase < 2 ? Infinity : 0 }}
          />
          <span className="font-mono text-[11px] text-faint-text">
            {phase < 2 ? "compass classifying…" : "compass"}
          </span>
        </div>

        <div className="mb-4">
          <div className="mb-1.5 flex items-baseline justify-between">
            <span className="font-mono text-[11px] text-faint-text">confidence</span>
            <span className="font-mono text-xs tabular-nums text-text">
              {phase >= 2 ? loop.confidence.toFixed(2) : "—"}
            </span>
          </div>
          <div className="relative h-2 overflow-hidden rounded-full bg-surface-raised">
            <motion.div
              className="h-full rounded-full"
              style={{
                background: loop.outcome === "answered" ? "var(--confidence-high)" : "var(--confidence-low)",
              }}
              animate={{ width: `${fillPct}%` }}
              transition={{ duration: 0.7, ease: "easeOut" }}
            />
            <div
              className="absolute top-0 h-full w-px bg-text/40"
              style={{ left: `${TAU_ROUTE * 100}%` }}
            />
          </div>
          <AnimatePresence>
            {phase >= 2 && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-1 font-mono text-[10px]"
                style={{ color: loop.outcome === "answered" ? "var(--manifest)" : "var(--danger)" }}
              >
                {loop.detail}
              </motion.p>
            )}
          </AnimatePresence>
        </div>

        <AnimatePresence>
          {phase >= 3 && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-3 flex items-center gap-2"
            >
              <span
                className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[11px]"
                style={{
                  color: style.color,
                  borderColor: `color-mix(in srgb, ${style.color} 35%, transparent)`,
                  background: `color-mix(in srgb, ${style.color} 12%, transparent)`,
                }}
              >
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: style.color }} />
                {style.label}
              </span>
              {loop.tool && (
                <span className="rounded bg-canvas px-2 py-1 font-mono text-[10.5px] text-muted-text">
                  {loop.tool}
                </span>
              )}
              {loop.outcome === "escalated" && (
                <span className="rounded bg-canvas px-2 py-1 font-mono text-[10.5px] text-danger">
                  ⛔ below τ_route
                </span>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {phase >= 4 && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="flex justify-start"
            >
              <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-line bg-canvas px-3.5 py-2 text-[13.5px] text-text">
                {loop.answer}
                {loop.outcome === "escalated" && (
                  <p className="mt-1.5 font-mono text-[10px] text-faint-text">→ ticket opened in relay</p>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

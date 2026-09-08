"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { demoLogin, sendChatMessage, ApiError, type ChatResponse } from "@/lib/api";
import { agentStyle, TAU_ROUTE } from "@/lib/agents";

const TENANTS = [
  {
    slug: "kite",
    name: "Kite & Co",
    kind: "Apparel retailer",
    questions: [
      "How long do I have to return something?",
      "Do you deliver to Pune?",
      "I want a refund for my last order",
    ],
  },
  {
    slug: "nimbus",
    name: "Nimbus Health",
    kind: "Online pharmacy",
    questions: [
      "How long do I have to return something?",
      "Can I get my prescription refilled early?",
      "Can I take double the dose if I missed one?",
    ],
  },
] as const;

type Slug = (typeof TENANTS)[number]["slug"];

export default function LiveTenantDemo() {
  const [slug, setSlug] = useState<Slug>("kite");
  const [asked, setAsked] = useState<string | null>(null);
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const tenant = TENANTS.find((t) => t.slug === slug)!;

  async function ask(question: string) {
    if (busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    setAsked(question);
    try {
      const auth = await demoLogin(slug);
      const res = await sendChatMessage(auth.access_token, {
        message: question,
        customer_id: auth.customer_id ?? undefined,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not reach the Meridian API.");
    } finally {
      setBusy(false);
    }
  }

  function switchTenant(next: Slug) {
    setSlug(next);
    setResult(null);
    setAsked(null);
    setError(null);
  }

  const style = result ? agentStyle(result.agent) : null;

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface">
      <div className="flex flex-col gap-4 border-b border-line px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-1.5">
          {TENANTS.map((t) => (
            <button
              key={t.slug}
              onClick={() => switchTenant(t.slug)}
              className={`rounded-full px-3.5 py-1.5 text-left text-[13px] transition-colors ${
                slug === t.slug
                  ? "bg-text text-canvas"
                  : "border border-line text-muted-text hover:border-line-strong hover:text-text"
              }`}
            >
              {t.name}
            </button>
          ))}
        </div>
        <p className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-faint-text">
          {tenant.kind} · same code, different tenant
        </p>
      </div>

      <div className="grid gap-0 lg:grid-cols-[1fr_320px]">
        <div className="flex min-h-[300px] flex-col justify-between border-line px-5 py-5 lg:border-r">
          <div>
            <p className="mb-3 font-mono text-[10.5px] uppercase tracking-[0.14em] text-faint-text">
              ask {tenant.name.toLowerCase()}
            </p>
            <div className="flex flex-col gap-2">
              {tenant.questions.map((q) => (
                <button
                  key={q}
                  disabled={busy}
                  onClick={() => ask(q)}
                  className={`rounded-xl border px-3.5 py-2.5 text-left text-[13.5px] transition-all disabled:opacity-50 ${
                    asked === q
                      ? "border-text/30 bg-canvas text-text"
                      : "border-line text-muted-text hover:border-line-strong hover:text-text"
                  }`}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-5">
            {busy ? (
              <div className="flex items-center gap-2">
                {[0, 1, 2].map((i) => (
                  <motion.span
                    key={i}
                    className="h-1.5 w-1.5 rounded-full bg-muted-text"
                    animate={{ opacity: [0.25, 1, 0.25] }}
                    transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
                  />
                ))}
                <span className="ml-1 font-mono text-[11px] text-faint-text">routing…</span>
              </div>
            ) : error ? (
              <p className="rounded-xl border border-danger/30 bg-danger/10 px-3.5 py-2.5 text-[13px] text-danger">
                {error}
              </p>
            ) : result ? (
              <motion.div
                key={result.conversation_id + result.answer}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                className="rounded-xl border border-line bg-canvas px-4 py-3"
              >
                <p className="text-[13.5px] leading-relaxed text-text">{result.answer}</p>
                {result.citations.length > 0 && (
                  <div className="mt-2.5 flex flex-wrap gap-1.5">
                    {result.citations.map((c) => (
                      <span
                        key={c.index}
                        className="rounded-full bg-almanac/12 px-2 py-0.5 font-mono text-[10px] text-almanac"
                      >
                        {c.document_title}
                      </span>
                    ))}
                  </div>
                )}
              </motion.div>
            ) : (
              <p className="font-mono text-[11px] leading-relaxed text-faint-text">
                Pick a question. It runs against the real backend — real retrieval, real gating.
              </p>
            )}
          </div>
        </div>

        <div className="bg-canvas/40 px-5 py-5">
          <p className="mb-4 font-mono text-[10.5px] uppercase tracking-[0.14em] text-faint-text">
            what happened
          </p>

          {!result ? (
            <p className="font-mono text-[11px] leading-relaxed text-faint-text">
              The routing decision, the confidence score, and whether it cleared the line — all of it
              lands here.
            </p>
          ) : (
            <motion.div
              key={result.conversation_id + result.intent}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col gap-4"
            >
              <div>
                <p className="mb-1.5 text-[10.5px] text-faint-text">handled by</p>
                <span
                  className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[11px]"
                  style={{
                    color: style!.color,
                    borderColor: `color-mix(in srgb, ${style!.color} 35%, transparent)`,
                    background: `color-mix(in srgb, ${style!.color} 12%, transparent)`,
                  }}
                >
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: style!.color }} />
                  {style!.label}
                </span>
              </div>

              <div>
                <p className="mb-1.5 text-[10.5px] text-faint-text">intent</p>
                <p className="font-mono text-[12.5px] text-text">{result.intent}</p>
              </div>

              <div>
                <div className="mb-1.5 flex items-baseline justify-between">
                  <p className="text-[10.5px] text-faint-text">confidence</p>
                  <span className="font-mono text-[12px] tabular-nums text-text">
                    {result.confidence.toFixed(2)}
                  </span>
                </div>
                <div className="relative h-1.5 overflow-hidden rounded-full bg-line">
                  <motion.div
                    className="h-full rounded-full"
                    style={{
                      background:
                        result.confidence >= TAU_ROUTE
                          ? "var(--confidence-high)"
                          : "var(--confidence-low)",
                    }}
                    initial={{ width: 0 }}
                    animate={{ width: `${result.confidence * 100}%` }}
                    transition={{ duration: 0.6, ease: "easeOut" }}
                  />
                  <div
                    className="absolute top-0 h-full w-px bg-text/40"
                    style={{ left: `${TAU_ROUTE * 100}%` }}
                  />
                </div>
                <p className="mt-1 font-mono text-[9.5px] text-faint-text">
                  line at {TAU_ROUTE.toFixed(2)}
                </p>
              </div>

              <div className="flex flex-wrap gap-1.5">
                {result.escalated && <Badge color="var(--beacon)" text="escalated to a human" />}
                {result.awaiting_confirmation && (
                  <Badge color="var(--danger)" text="waiting on your yes" />
                )}
                {result.grounded === true && <Badge color="var(--manifest)" text="grounded" />}
                {result.grounded === false && <Badge color="var(--danger)" text="ungrounded" />}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}

function Badge({ color, text }: { color: string; text: string }) {
  return (
    <span
      className="rounded-full border px-2 py-0.5 font-mono text-[10px]"
      style={{
        color,
        borderColor: `color-mix(in srgb, ${color} 35%, transparent)`,
        background: `color-mix(in srgb, ${color} 12%, transparent)`,
      }}
    >
      {text}
    </span>
  );
}

"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getConversation, ApiError, type ConversationDetail } from "@/lib/api";
import { useSession } from "@/lib/session";
import { agentStyle } from "@/lib/agents";

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function StepDetail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] text-faint-text">{label}</p>
      <p className="font-mono text-xs tabular-nums text-text">{value}</p>
    </div>
  );
}

export default function TraceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { session } = useSession();
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    if (!session) return;
    getConversation(session.token, id)
      .then(setDetail)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not reach the Meridian API."));
  }, [session, id]);

  return (
    <div className="flex flex-1 overflow-hidden">
      <section className="min-w-0 flex-1 overflow-y-auto border-r border-line px-6 py-6">
        <Link href="/console/traces" className="mb-4 inline-block font-mono text-[11px] text-muted-text hover:text-text">
          ← back to traces
        </Link>

        {error && (
          <p className="rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</p>
        )}
        {!error && !detail && <p className="text-sm text-muted-text">Loading…</p>}

        {detail && (
          <div className="flex flex-col gap-3">
            {detail.messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === "customer" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-md rounded-2xl px-4 py-2.5 text-[14px] leading-relaxed ${
                    m.role === "customer" ? "bg-compass text-white" : "border border-line bg-surface text-text"
                  }`}
                >
                  {m.content}
                  <p className="mt-1 font-mono text-[10px] opacity-60">{formatTime(m.created_at)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <aside className="hidden w-96 shrink-0 overflow-y-auto p-5 lg:block">
        <p className="mb-4 font-mono text-[11px] uppercase tracking-[0.15em] text-faint-text">step timeline</p>

        {detail?.traces.map((t, i) => {
          const style = agentStyle(t.agent_name);
          const isOpen = expanded === i;
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(i * 0.04, 0.3) }}
              className="mb-2 rounded-lg border border-line bg-surface"
            >
              <button
                className="flex w-full items-center justify-between px-3 py-2.5 text-left"
                onClick={() => setExpanded(isOpen ? null : i)}
              >
                <div className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: style.color }} />
                  <span className="font-mono text-xs" style={{ color: style.color }}>
                    {style.label}
                  </span>
                  {t.model && <span className="font-mono text-[10px] text-faint-text">{t.model}</span>}
                </div>
                <span className="font-mono text-[10px] text-faint-text">{isOpen ? "–" : "+"}</span>
              </button>

              {isOpen && (
                <div className="border-t border-line px-3 py-3">
                  <div className="mb-3 grid grid-cols-2 gap-3">
                    {t.confidence !== null && <StepDetail label="confidence" value={t.confidence.toFixed(2)} />}
                    {t.latency_ms !== null && <StepDetail label="latency" value={`${t.latency_ms}ms`} />}
                    {t.input_tokens !== null && <StepDetail label="input tokens" value={String(t.input_tokens)} />}
                    {t.output_tokens !== null && <StepDetail label="output tokens" value={String(t.output_tokens)} />}
                    {t.cost_usd !== null && <StepDetail label="cost" value={`$${t.cost_usd.toFixed(6)}`} />}
                    <StepDetail label="time" value={formatTime(t.created_at)} />
                  </div>
                  <p className="mb-1 text-[10px] text-faint-text">input</p>
                  <pre className="mb-3 overflow-x-auto rounded bg-surface-raised p-2 font-mono text-[10px] text-muted-text">
                    {JSON.stringify(t.input, null, 2)}
                  </pre>
                  <p className="mb-1 text-[10px] text-faint-text">output</p>
                  <pre className="overflow-x-auto rounded bg-surface-raised p-2 font-mono text-[10px] text-muted-text">
                    {JSON.stringify(t.output, null, 2)}
                  </pre>
                </div>
              )}
            </motion.div>
          );
        })}
      </aside>
    </div>
  );
}

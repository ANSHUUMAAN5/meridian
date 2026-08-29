"use client";

import { useState, useRef, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Input } from "@/components/ui/input";
import { sendChatMessage, ApiError, type ChatResponse } from "@/lib/api";
import { useSession } from "@/lib/session";

type ChatMessage = {
  id: string;
  role: "customer" | "assistant";
  content: string;
  meta?: ChatResponse;
};

const AGENT_STYLE: Record<string, { color: string; label: string }> = {
  compass: { color: "var(--compass)", label: "compass" },
  almanac: { color: "var(--almanac)", label: "almanac" },
  manifest: { color: "var(--manifest)", label: "manifest" },
  beacon: { color: "var(--beacon)", label: "beacon" },
  sentinel: { color: "var(--danger)", label: "sentinel" },
  none: { color: "var(--faint-text)", label: "none" },
};

const TAU_ROUTE = 0.75;

const EXAMPLES = [
  "How long do I have to return something?",
  "What's the status of my order KC4407?",
  "I want a refund for order KC4407",
  "let me talk to a human",
];

function renderInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

function uid() {
  return Math.random().toString(36).slice(2);
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-1 py-1">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-muted-text"
          animate={{ opacity: [0.25, 1, 0.25] }}
          transition={{ duration: 1, repeat: Infinity, delay: i * 0.15, ease: "easeInOut" }}
        />
      ))}
    </div>
  );
}

export default function ChatPage() {
  const { session } = useSession();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const lastMeta = [...messages].reverse().find((m) => m.meta)?.meta;

  async function send(text: string) {
    if (!session || !text.trim() || sending) return;
    setError(null);
    setMessages((prev) => [...prev, { id: uid(), role: "customer", content: text }]);
    setInput("");
    setSending(true);
    try {
      const res = await sendChatMessage(session.token, {
        message: text,
        conversation_id: conversationId,
        customer_id: session.customerId ?? undefined,
      });
      setConversationId(res.conversation_id);
      setMessages((prev) => [...prev, { id: uid(), role: "assistant", content: res.answer, meta: res }]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not reach the Meridian API.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      <section className="flex flex-1 flex-col border-r border-line">
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mx-auto max-w-md pt-12 text-center"
            >
              <p className="mb-5 text-sm text-muted-text">Try one of these, or ask your own question.</p>
              <div className="flex flex-col gap-2">
                {EXAMPLES.map((ex, i) => (
                  <motion.button
                    key={ex}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.06 }}
                    whileHover={{ y: -1 }}
                    className="rounded-lg border border-line bg-surface px-4 py-2.5 text-left text-sm text-text transition-colors hover:border-compass/40"
                    onClick={() => send(ex)}
                  >
                    {ex}
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}

          <div className="flex flex-col gap-3">
            <AnimatePresence initial={false}>
              {messages.map((m) => (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25, ease: "easeOut" }}
                  className={`flex ${m.role === "customer" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-md rounded-2xl px-4 py-2.5 text-[14.5px] leading-relaxed ${
                      m.role === "customer" ? "bg-compass text-white" : "border border-line bg-surface text-text"
                    }`}
                  >
                    {renderInline(m.content)}
                    {m.meta && m.meta.citations.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {m.meta.citations.map((c) => (
                          <span
                            key={c.index}
                            className="rounded bg-almanac/15 px-1.5 py-0.5 font-mono text-[11px] text-almanac"
                          >
                            [{c.index}] {c.document_title}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
              {sending && (
                <motion.div
                  key="typing"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex justify-start"
                >
                  <div className="rounded-2xl border border-line bg-surface px-3 py-2">
                    <TypingDots />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          <div ref={bottomRef} />
        </div>

        {error && (
          <p className="mx-6 mb-2 rounded-md border border-danger/40 bg-danger/10 px-4 py-2 text-sm text-danger">
            {error}
          </p>
        )}

        <form
          className="flex gap-2 border-t border-line p-4"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question…"
            disabled={sending}
            className="bg-surface"
          />
          <motion.button
            type="submit"
            disabled={sending || !input.trim()}
            whileTap={{ scale: 0.96 }}
            className="rounded-md bg-compass px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-40"
          >
            Send
          </motion.button>
        </form>
      </section>

      <aside className="hidden w-80 flex-col overflow-y-auto p-5 lg:flex">
        <p className="mb-5 font-mono text-[11px] uppercase tracking-[0.15em] text-faint-text">live trace</p>

        <AnimatePresence mode="wait">
          {!lastMeta ? (
            <motion.p key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-sm text-muted-text">
              Send a message to see how it was routed and gated.
            </motion.p>
          ) : (
            <motion.div
              key={lastMeta.conversation_id + lastMeta.intent + lastMeta.confidence}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="flex flex-col gap-5"
            >
              <div>
                <p className="mb-1.5 text-[11px] text-faint-text">handled by</p>
                <span
                  className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-xs"
                  style={{
                    color: AGENT_STYLE[lastMeta.agent]?.color ?? AGENT_STYLE.none.color,
                    borderColor: `color-mix(in srgb, ${AGENT_STYLE[lastMeta.agent]?.color ?? AGENT_STYLE.none.color} 35%, transparent)`,
                    background: `color-mix(in srgb, ${AGENT_STYLE[lastMeta.agent]?.color ?? AGENT_STYLE.none.color} 12%, transparent)`,
                  }}
                >
                  <span
                    className="h-1.5 w-1.5 rounded-full"
                    style={{ background: AGENT_STYLE[lastMeta.agent]?.color ?? AGENT_STYLE.none.color }}
                  />
                  {AGENT_STYLE[lastMeta.agent]?.label ?? lastMeta.agent}
                </span>
              </div>

              <div>
                <p className="mb-1.5 text-[11px] text-faint-text">intent</p>
                <p className="font-mono text-sm text-text">{lastMeta.intent}</p>
              </div>

              <div>
                <div className="mb-1.5 flex items-baseline justify-between">
                  <p className="text-[11px] text-faint-text">confidence</p>
                  <span className="font-mono text-xs tabular-nums text-text">{lastMeta.confidence.toFixed(2)}</span>
                </div>
                <div className="relative h-2 overflow-hidden rounded-full bg-surface-raised">
                  <motion.div
                    className="h-full rounded-full"
                    style={{
                      background:
                        lastMeta.confidence >= TAU_ROUTE
                          ? "var(--confidence-high)"
                          : "var(--confidence-low)",
                    }}
                    initial={{ width: 0 }}
                    animate={{ width: `${lastMeta.confidence * 100}%` }}
                    transition={{ duration: 0.6, ease: "easeOut" }}
                  />
                  <div
                    className="absolute top-0 h-full w-px bg-text/40"
                    style={{ left: `${TAU_ROUTE * 100}%` }}
                    title={`τ_route = ${TAU_ROUTE}`}
                  />
                </div>
                <p className="mt-1 font-mono text-[10px] text-faint-text">
                  line at {TAU_ROUTE.toFixed(2)} — τ_route
                </p>
              </div>

              <div className="flex flex-wrap gap-1.5">
                {lastMeta.escalated && <TraceBadge color="var(--beacon)" text="escalated" />}
                {lastMeta.awaiting_confirmation && <TraceBadge color="var(--danger)" text="awaiting confirmation" />}
                {lastMeta.grounded === false && <TraceBadge color="var(--danger)" text="ungrounded" />}
                {lastMeta.grounded === true && <TraceBadge color="var(--manifest)" text="grounded" />}
              </div>

              {lastMeta.escalation_id && (
                <div>
                  <p className="mb-1 text-[11px] text-faint-text">escalation id</p>
                  <p className="break-all font-mono text-[11px] text-muted-text">{lastMeta.escalation_id}</p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </aside>
    </div>
  );
}

function TraceBadge({ color, text }: { color: string; text: string }) {
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="rounded-full border px-2 py-0.5 font-mono text-[11px]"
      style={{
        color,
        borderColor: `color-mix(in srgb, ${color} 35%, transparent)`,
        background: `color-mix(in srgb, ${color} 12%, transparent)`,
      }}
    >
      {text}
    </motion.span>
  );
}

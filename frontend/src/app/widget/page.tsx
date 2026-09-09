"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { demoLogin, sendChatMessage, ApiError } from "@/lib/api";

type Msg = { id: string; role: "customer" | "assistant"; text: string };

function uid() {
  return Math.random().toString(36).slice(2);
}

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

function WidgetChat() {
  const params = useSearchParams();
  const tenantSlug = params.get("tenant") ?? "kite";

  const [token, setToken] = useState<string | null>(null);
  const [customerId, setCustomerId] = useState<string | undefined>(undefined);
  const [tenantName, setTenantName] = useState<string>("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    demoLogin(tenantSlug)
      .then((res) => {
        setToken(res.access_token);
        setCustomerId(res.customer_id ?? undefined);
        setTenantName(res.tenant.name);
        setMessages([
          { id: uid(), role: "assistant", text: `Hi — how can I help you today?` },
        ]);
      })
      .catch(() => setError("Could not connect. Please try again shortly."));
  }, [tenantSlug]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function send(text: string) {
    if (!token || !text.trim() || sending) return;
    setError(null);
    setMessages((prev) => [...prev, { id: uid(), role: "customer", text }]);
    setInput("");
    setSending(true);
    try {
      const res = await sendChatMessage(token, {
        message: text,
        conversation_id: conversationId,
        customer_id: customerId,
      });
      setConversationId(res.conversation_id);
      setMessages((prev) => [...prev, { id: uid(), role: "assistant", text: res.answer }]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-screen w-full flex-col bg-canvas">
      <div className="flex items-center gap-2.5 border-b border-line px-4 py-3">
        <span className="h-2 w-2 rounded-full bg-manifest" />
        <p className="text-[13.5px] font-medium text-text">{tenantName || "Support"}</p>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="flex flex-col gap-2.5">
          <AnimatePresence initial={false}>
            {messages.map((m) => (
              <motion.div
                key={m.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className={`flex ${m.role === "customer" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-[13.5px] leading-relaxed ${
                    m.role === "customer"
                      ? "bg-compass text-white"
                      : "border border-line bg-surface text-text"
                  }`}
                >
                  {renderInline(m.text)}
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
        <p className="mx-4 mb-2 rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-[12.5px] text-danger">
          {error}
        </p>
      )}

      <form
        className="flex gap-2 border-t border-line p-3"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          disabled={!token || sending}
          className="flex-1 rounded-full border border-line bg-surface px-3.5 py-2 text-[13.5px] text-text outline-none focus:border-line-strong"
        />
        <button
          type="submit"
          disabled={!token || sending || !input.trim()}
          className="rounded-full bg-text px-4 py-2 text-[13px] font-medium text-canvas transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </div>
  );
}

export default function WidgetPage() {
  return (
    <Suspense fallback={null}>
      <WidgetChat />
    </Suspense>
  );
}

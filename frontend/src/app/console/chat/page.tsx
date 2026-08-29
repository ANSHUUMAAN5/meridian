"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { sendChatMessage, ApiError, type ChatResponse } from "@/lib/api";
import { useSession } from "@/lib/session";

type ChatMessage = {
  role: "customer" | "assistant";
  content: string;
  meta?: ChatResponse;
};

const AGENT_COLOR: Record<string, string> = {
  compass: "bg-compass/15 text-compass border-compass/30",
  almanac: "bg-almanac/15 text-almanac border-almanac/30",
  manifest: "bg-manifest/15 text-manifest border-manifest/30",
  beacon: "bg-beacon/15 text-beacon border-beacon/30",
  sentinel: "bg-danger/15 text-danger border-danger/30",
  none: "bg-surface-raised text-muted-text border-line",
};

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

function confidenceColor(c: number) {
  return `color-mix(in srgb, var(--confidence-low) ${Math.round((1 - c) * 100)}%, var(--confidence-high) ${Math.round(c * 100)}%)`;
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
  }, [messages]);

  const lastMeta = [...messages].reverse().find((m) => m.meta)?.meta;

  async function send(text: string) {
    if (!session || !text.trim() || sending) return;
    setError(null);
    setMessages((prev) => [...prev, { role: "customer", content: text }]);
    setInput("");
    setSending(true);
    try {
      const res = await sendChatMessage(session.token, {
        message: text,
        conversation_id: conversationId,
      });
      setConversationId(res.conversation_id);
      setMessages((prev) => [...prev, { role: "assistant", content: res.answer, meta: res }]);
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
            <div className="mx-auto max-w-md text-center">
              <p className="mb-4 text-sm text-muted-text">Try one of these, or ask your own question.</p>
              <div className="flex flex-col gap-2">
                {EXAMPLES.map((ex) => (
                  <button
                    key={ex}
                    className="rounded-lg border border-line bg-surface px-4 py-2 text-left text-sm text-text hover:border-compass/40"
                    onClick={() => send(ex)}
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-col gap-4">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "customer" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-md rounded-2xl px-4 py-2.5 text-sm ${
                    m.role === "customer"
                      ? "bg-compass text-white"
                      : "border border-line bg-surface text-text"
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
              </div>
            ))}
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
          <Button type="submit" disabled={sending || !input.trim()} className="bg-compass text-white hover:opacity-90">
            {sending ? "…" : "Send"}
          </Button>
        </form>
      </section>

      <aside className="hidden w-80 flex-col overflow-y-auto p-5 lg:flex">
        <p className="mb-4 font-mono text-xs uppercase tracking-widest text-faint-text">live trace</p>
        {!lastMeta ? (
          <p className="text-sm text-muted-text">Send a message to see how it was routed and gated.</p>
        ) : (
          <div className="flex flex-col gap-4">
            <div>
              <p className="mb-1 text-xs text-faint-text">handled by</p>
              <Badge variant="outline" className={AGENT_COLOR[lastMeta.agent] ?? AGENT_COLOR.none}>
                {lastMeta.agent}
              </Badge>
            </div>
            <div>
              <p className="mb-1 text-xs text-faint-text">intent</p>
              <p className="font-mono text-sm text-text">{lastMeta.intent}</p>
            </div>
            <div>
              <p className="mb-1 text-xs text-faint-text">confidence</p>
              <div className="flex items-center gap-2">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-raised">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.round(lastMeta.confidence * 100)}%`,
                      background: confidenceColor(lastMeta.confidence),
                    }}
                  />
                </div>
                <span className="font-mono text-xs text-text">{lastMeta.confidence.toFixed(2)}</span>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {lastMeta.escalated && (
                <Badge variant="outline" className="border-beacon/30 bg-beacon/15 text-beacon">
                  escalated
                </Badge>
              )}
              {lastMeta.awaiting_confirmation && (
                <Badge variant="outline" className="border-danger/30 bg-danger/15 text-danger">
                  awaiting confirmation
                </Badge>
              )}
              {lastMeta.grounded === false && (
                <Badge variant="outline" className="border-danger/30 bg-danger/15 text-danger">
                  ungrounded
                </Badge>
              )}
              {lastMeta.grounded === true && (
                <Badge variant="outline" className="border-manifest/30 bg-manifest/15 text-manifest">
                  grounded
                </Badge>
              )}
            </div>
            {lastMeta.escalation_id && (
              <div>
                <p className="mb-1 text-xs text-faint-text">escalation id</p>
                <p className="break-all font-mono text-xs text-muted-text">{lastMeta.escalation_id}</p>
              </div>
            )}
          </div>
        )}
      </aside>
    </div>
  );
}

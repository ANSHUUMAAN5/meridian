"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { listConversations, ApiError, type ConversationSummary } from "@/lib/api";
import { useSession } from "@/lib/session";

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function TracesListPage() {
  const { session } = useSession();
  const [conversations, setConversations] = useState<ConversationSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) return;
    listConversations(session.token)
      .then(setConversations)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not reach the Meridian API."));
  }, [session]);

  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-6 py-6">
      <div className="mx-auto w-full max-w-3xl">
        <p className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-faint-text">conversation history</p>
        <h1 className="mb-6 text-xl font-semibold text-text">Traces</h1>

        {error && (
          <p className="rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</p>
        )}

        {!error && conversations === null && (
          <p className="text-sm text-muted-text">Loading…</p>
        )}

        {conversations !== null && conversations.length === 0 && (
          <p className="text-sm text-muted-text">
            No conversations yet — go to Chat and ask something first.
          </p>
        )}

        <div className="flex flex-col gap-2">
          {conversations?.map((c, i) => (
            <motion.div
              key={c.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(i * 0.03, 0.3) }}
            >
              <Link
                href={`/console/traces/${c.id}`}
                className="flex items-center gap-4 rounded-lg border border-line bg-surface px-4 py-3 transition-colors hover:border-line-strong"
              >
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <span className="font-mono text-xs text-muted-text">
                      {c.external_customer_id ?? "anonymous"}
                    </span>
                    <span className="text-faint-text">·</span>
                    <span className="font-mono text-[11px] text-faint-text">{timeAgo(c.created_at)}</span>
                    <span className="font-mono text-[11px] text-faint-text">· {c.message_count} messages</span>
                  </div>
                  <p className="truncate text-sm text-text">{c.last_message_preview ?? "(no messages)"}</p>
                </div>
                {c.has_open_escalation && (
                  <span className="shrink-0 rounded-full border border-beacon/30 bg-beacon/15 px-2 py-0.5 font-mono text-[10px] text-beacon">
                    open case
                  </span>
                )}
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

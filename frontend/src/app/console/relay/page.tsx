"use client";

import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import {
  listEscalations, claimEscalation, resolveEscalation, ApiError, type EscalationOut,
} from "@/lib/api";
import { useSession } from "@/lib/session";

const TABS = ["open", "claimed", "resolved"] as const;
type Tab = (typeof TABS)[number];

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function ReasonBlock({ reason }: { reason: string }) {
  const lines = reason.split("\n").filter(Boolean);
  const [headline, ...trail] = lines;
  return (
    <div>
      <p className="text-sm text-text">{headline.replace(/^Reason:\s*/, "")}</p>
      {trail.length > 0 && (
        <ul className="mt-2 space-y-1 border-l border-line pl-3">
          {trail.map((line, i) => (
            <li key={i} className="font-mono text-[11px] leading-relaxed text-muted-text">
              {line.replace(/^-\s*/, "")}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function EscalationCard({
  escalation, onClaim, onResolve,
}: {
  escalation: EscalationOut;
  onClaim: (id: string) => void;
  onResolve: (id: string, note: string) => void;
}) {
  const [resolving, setResolving] = useState(false);
  const [note, setNote] = useState("");

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="rounded-lg border border-line bg-surface p-4"
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 font-mono text-[11px] text-faint-text">
          <span>{timeAgo(escalation.created_at)}</span>
          {escalation.confidence !== null && (
            <>
              <span>·</span>
              <span>confidence {escalation.confidence.toFixed(2)}</span>
            </>
          )}
        </div>
        <Link
          href={`/console/traces/${escalation.conversation_id}`}
          className="font-mono text-[11px] text-compass hover:opacity-80"
        >
          view conversation →
        </Link>
      </div>

      <ReasonBlock reason={escalation.reason} />

      {escalation.status === "resolved" && escalation.resolution_note && (
        <div className="mt-3 rounded-md border border-manifest/30 bg-manifest/10 px-3 py-2">
          <p className="mb-1 font-mono text-[10px] uppercase tracking-wider text-manifest">resolution</p>
          <p className="text-sm text-text">{escalation.resolution_note}</p>
        </div>
      )}

      {escalation.status !== "resolved" && (
        <div className="mt-3 flex items-center gap-2">
          {escalation.status === "open" && (
            <button
              onClick={() => onClaim(escalation.id)}
              className="rounded-md border border-line px-3 py-1.5 font-mono text-[11px] text-text transition-colors hover:border-line-strong"
            >
              claim
            </button>
          )}
          {!resolving ? (
            <button
              onClick={() => setResolving(true)}
              className="rounded-md bg-manifest px-3 py-1.5 font-mono text-[11px] text-white transition-opacity hover:opacity-90"
            >
              resolve
            </button>
          ) : (
            <div className="flex flex-1 gap-2">
              <input
                autoFocus
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="What did you tell the customer?"
                className="flex-1 rounded-md border border-line bg-surface-raised px-2.5 py-1.5 text-sm text-text outline-none focus:border-compass/50"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && note.trim()) onResolve(escalation.id, note);
                }}
              />
              <button
                disabled={!note.trim()}
                onClick={() => onResolve(escalation.id, note)}
                className="rounded-md bg-manifest px-3 py-1.5 font-mono text-[11px] text-white disabled:opacity-40"
              >
                submit
              </button>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}

export default function RelayPage() {
  const { session } = useSession();
  const [tab, setTab] = useState<Tab>("open");
  const [escalations, setEscalations] = useState<EscalationOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    (t: Tab) => {
      if (!session) return;
      setEscalations(null);
      listEscalations(session.token, t)
        .then(setEscalations)
        .catch((e) => setError(e instanceof ApiError ? e.message : "Could not reach the Meridian API."));
    },
    [session],
  );

  useEffect(() => load(tab), [tab, load]);

  async function handleClaim(id: string) {
    if (!session) return;
    await claimEscalation(session.token, id);
    load(tab);
  }

  async function handleResolve(id: string, note: string) {
    if (!session) return;
    await resolveEscalation(session.token, id, note);
    load(tab);
  }

  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-6 py-6">
      <div className="mx-auto w-full max-w-2xl">
        <p className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-faint-text">human inbox</p>
        <h1 className="mb-6 text-xl font-semibold text-text">Relay</h1>

        <div className="mb-5 flex gap-1 border-b border-line">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`border-b-2 px-3 py-2 font-mono text-xs uppercase tracking-wider transition-colors ${
                tab === t ? "border-compass text-text" : "border-transparent text-muted-text hover:text-text"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {error && (
          <p className="rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</p>
        )}

        {!error && escalations === null && <p className="text-sm text-muted-text">Loading…</p>}

        {escalations !== null && escalations.length === 0 && (
          <p className="text-sm text-muted-text">Nothing here.</p>
        )}

        <div className="flex flex-col gap-3">
          <AnimatePresence>
            {escalations?.map((e) => (
              <EscalationCard key={e.id} escalation={e} onClaim={handleClaim} onResolve={handleResolve} />
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

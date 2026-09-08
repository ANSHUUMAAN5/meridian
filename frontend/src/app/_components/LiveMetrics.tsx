"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getPublicMetrics, type PublicMetrics } from "@/lib/api";

function Tile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.4 }}
      className="rounded-xl border border-line bg-surface p-5"
    >
      <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.12em] text-faint-text">{label}</p>
      <p className="font-mono text-3xl tabular-nums text-text">{value}</p>
      {sub && <p className="mt-1 font-mono text-[10.5px] text-faint-text">{sub}</p>}
    </motion.div>
  );
}

export default function LiveMetrics() {
  const [metrics, setMetrics] = useState<PublicMetrics | null>(null);

  useEffect(() => {
    getPublicMetrics().then(setMetrics).catch(() => {});
  }, []);

  if (!metrics) {
    return <p className="text-center text-sm text-muted-text">Loading live metrics…</p>;
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Tile
        label="routing accuracy"
        value={metrics.routing_accuracy != null ? `${(metrics.routing_accuracy * 100).toFixed(1)}%` : "—"}
        sub={metrics.eval_case_count ? `n=${metrics.eval_case_count} labeled cases` : undefined}
      />
      <Tile
        label="escalation accuracy"
        value={metrics.escalation_accuracy != null ? `${(metrics.escalation_accuracy * 100).toFixed(1)}%` : "—"}
        sub="knows when not to answer"
      />
      <Tile
        label="adversarial safe rate"
        value={metrics.adversarial_safe_rate ?? "—"}
        sub="prompt-injection resistance"
      />
      <Tile
        label="latency p50"
        value={metrics.latency_p50_ms != null ? `${metrics.latency_p50_ms}ms` : "—"}
        sub="per resolved query"
      />
      <Tile label="tenants live" value={String(metrics.tenant_count)} sub="fully isolated by RLS" />
      <Tile label="conversations" value={String(metrics.conversation_count)} sub="handled so far" />
      <Tile label="documents indexed" value={String(metrics.document_count)} sub="across the knowledge base" />
      <Tile label="escalations resolved" value={String(metrics.escalations_resolved)} sub="closed the loop" />
    </div>
  );
}

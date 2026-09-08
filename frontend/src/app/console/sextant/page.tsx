"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import {
  listSextantRuns, getSextantRun, ApiError, type SextantRunSummary, type SextantRunDetail,
} from "@/lib/api";
import { useSession } from "@/lib/session";

function runTime(runId: string): string {
  const m = runId.match(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})$/);
  if (!m) return runId;
  const [, y, mo, d, h, mi] = m;
  return `${mo}/${d} ${h}:${mi}`;
}

function StatTile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <p className="mb-1.5 text-[11px] text-faint-text">{label}</p>
      <p className="font-mono text-2xl tabular-nums text-text">{value}</p>
      {sub && <p className="mt-0.5 font-mono text-[10px] text-faint-text">{sub}</p>}
    </div>
  );
}

export default function SextantPage() {
  const { session } = useSession();
  const [runs, setRuns] = useState<SextantRunSummary[] | null>(null);
  const [latest, setLatest] = useState<SextantRunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) return;
    listSextantRuns(session.token)
      .then((rs) => {
        setRuns(rs);
        if (rs[0]) return getSextantRun(session.token, rs[0].run_id).then(setLatest);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not reach the Meridian API."));
  }, [session]);

  const chartData = runs
    ? [...runs].reverse().map((r) => ({
        run: runTime(r.run_id),
        routing: Math.round(r.summary.routing_accuracy * 1000) / 10,
        escalation: Math.round(r.summary.routing_escalation_accuracy * 1000) / 10,
      }))
    : [];

  const failing = latest?.cases.filter((c) => !c.intent_correct || !c.escalate_correct) ?? [];

  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-6 py-6">
      <div className="mx-auto w-full max-w-3xl">
        <p className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-faint-text">evaluation harness</p>
        <h1 className="mb-6 text-xl font-semibold text-text">Sextant</h1>

        {error && (
          <p className="rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</p>
        )}
        {!error && !latest && <p className="text-sm text-muted-text">Loading…</p>}

        {latest && (
          <>
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3"
            >
              <StatTile
                label="routing accuracy"
                value={`${(latest.summary.routing_accuracy * 100).toFixed(1)}%`}
                sub={`n=${latest.summary.by_kind.routing ?? "—"}`}
              />
              <StatTile
                label="escalation accuracy"
                value={`${(latest.summary.routing_escalation_accuracy * 100).toFixed(1)}%`}
              />
              <StatTile label="adversarial safe" value={latest.summary.adversarial_safe_rate ?? "—"} />
              <StatTile
                label="hard negatives"
                value={`${(latest.summary.hard_negative_refusal_rate * 100).toFixed(0)}%`}
              />
              <StatTile label="latency p50" value={`${latest.summary.latency_p50_ms}ms`} />
              <StatTile label="latency p95" value={`${latest.summary.latency_p95_ms}ms`} />
            </motion.div>

            {chartData.length > 1 && (
              <div className="mb-6 rounded-lg border border-line bg-surface p-4">
                <p className="mb-3 font-mono text-[11px] uppercase tracking-wider text-faint-text">
                  routing accuracy over time — {chartData.length} runs
                </p>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
                    <XAxis dataKey="run" tick={{ fill: "var(--faint-text)", fontSize: 10 }} axisLine={{ stroke: "var(--line)" }} tickLine={false} />
                    <YAxis domain={[80, 100]} tick={{ fill: "var(--faint-text)", fontSize: 10 }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ background: "var(--surface-raised)", border: "1px solid var(--line)", borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: "var(--text)" }}
                    />
                    <ReferenceLine y={95} stroke="var(--line-strong)" strokeDasharray="2 4" />
                    <Line type="monotone" dataKey="routing" name="intent accuracy %" stroke="var(--compass)" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="escalation" name="escalation accuracy %" stroke="var(--manifest)" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            <p className="mb-3 font-mono text-[11px] uppercase tracking-wider text-faint-text">
              {failing.length === 0 ? "no failing cases in the latest run" : `${failing.length} case${failing.length === 1 ? "" : "s"} to look at`}
            </p>
            <div className="flex flex-col gap-2">
              {failing.map((c) => (
                <div key={c.id} className="rounded-lg border border-line bg-surface p-3">
                  <p className="mb-1.5 font-mono text-[11px] text-faint-text">{c.id} · {c.tenant}</p>
                  <p className="mb-2 text-sm text-text">&ldquo;{c.message}&rdquo;</p>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] text-muted-text">
                    <span>expected: {c.expected_intent}</span>
                    <span>actual: {c.actual_intent}</span>
                    <span>confidence: {c.confidence.toFixed(2)}</span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

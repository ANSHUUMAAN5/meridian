"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import HeroRouting from "./_components/HeroRouting";
import LiveMetrics from "./_components/LiveMetrics";

const PILLARS = [
  {
    title: "Isolated",
    color: "var(--compass)",
    body: "Every tenant's documents, orders, and conversations sit behind Postgres row-level security, not an application-layer filter. A cross-tenant test suite proves it in CI on every commit.",
  },
  {
    title: "Gated",
    color: "var(--manifest)",
    body: "Reads run autonomously above the confidence line. Writes need a proposal the customer confirms, a ceiling above which they always escalate, and a hard rule that overrides confidence entirely for anything that should never be automated.",
  },
  {
    title: "Measured",
    color: "var(--beacon)",
    body: "Every routing decision, every tool call, every escalation is logged with confidence, latency, and cost. A labeled eval suite replays them and produces a real accuracy number — not a screenshot.",
  },
];

const COMPONENTS = [
  { name: "Compass", kind: "agent", color: "var(--compass)", body: "Reads the message, decides who handles it." },
  { name: "Almanac", kind: "agent", color: "var(--almanac)", body: "Answers from the tenant's own documents, with citations." },
  { name: "Manifest", kind: "agent", color: "var(--manifest)", body: "Answers account questions via tool calls, in a bounded reasoning loop." },
  { name: "Beacon", kind: "agent", color: "var(--beacon)", body: "Escalates to a human with the full reasoning attached." },
  { name: "Threshold", kind: "system", color: "var(--faint-text)", body: "The deterministic gate. Not an agent — a comparison should never be persuadable." },
  { name: "Trace", kind: "system", color: "var(--faint-text)", body: "Logs every step: model, prompt, confidence, latency, tokens, cost." },
  { name: "Sextant", kind: "system", color: "var(--faint-text)", body: "The eval harness. Replays labeled cases and scores the whole system." },
  { name: "Relay", kind: "system", color: "var(--faint-text)", body: "The human inbox. Resolutions feed back in as new labeled cases." },
];

const ARCH_ROWS = [
  { label: "browser", items: ["landing", "console"] },
  { label: "fastapi", items: ["compass", "almanac", "manifest", "beacon"] },
  { label: "postgres + pgvector", items: ["tenants", "documents", "orders", "traces"] },
];

export default function Landing() {
  return (
    <div className="flex flex-1 flex-col bg-canvas">
      <header className="flex items-center justify-between border-b border-line px-6 py-4">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-text" />
          <span className="font-mono text-[12px] uppercase tracking-[0.15em] text-text">meridian</span>
        </div>
        <div className="flex items-center gap-5">
          <a
            href="https://github.com/ANSHUUMAAN5/meridian"
            target="_blank"
            rel="noreferrer"
            className="font-mono text-[11px] uppercase tracking-wider text-muted-text transition-colors hover:text-text"
          >
            github
          </a>
          <Link
            href="/demo"
            className="rounded-full bg-text px-3.5 py-1.5 font-mono text-[11px] uppercase tracking-wider text-canvas transition-opacity hover:opacity-90"
          >
            try the demo
          </Link>
        </div>
      </header>

      {/* announcement */}
      <div className="border-b border-line bg-surface/60 px-6 py-2 text-center">
        <p className="font-mono text-[11px] text-muted-text">
          Real accuracy, not a screenshot —{" "}
          <a href="#metrics" className="text-text underline decoration-line hover:decoration-text">
            see the live numbers
          </a>
        </p>
      </div>

      {/* hero */}
      <section className="relative overflow-hidden lg:min-h-[680px]">
        <div className="pointer-events-none absolute inset-y-0 right-0 hidden w-[58%] lg:block">
          <img
            src="https://images.unsplash.com/photo-1515378791036-0648a3ef77b2?fm=jpg&q=80&w=1800&auto=format&fit=crop"
            alt=""
            className="h-full w-full object-cover"
            style={{ objectPosition: "60% 45%" }}
          />
          <div
            className="absolute inset-0"
            style={{ background: "linear-gradient(to right, var(--canvas) 0%, color-mix(in srgb, var(--canvas) 55%, transparent) 22%, transparent 48%)" }}
          />
          <div
            className="absolute inset-0"
            style={{ background: "linear-gradient(to top, color-mix(in srgb, var(--canvas) 55%, transparent), transparent 40%)" }}
          />
        </div>

        <div className="relative z-10 mx-auto max-w-6xl px-6 py-16 lg:py-24">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="max-w-xl"
          >
            <p className="mb-4 font-mono text-[11px] uppercase tracking-[0.2em] text-faint-text">
              multi-tenant · multi-agent · confidence-gated
            </p>
            <h1 className="mb-5 text-5xl font-semibold tracking-tight text-text">
              A support agent for every customer.
              <br />
              <span className="text-muted-text">Confident enough to answer, honest enough to say when it can&apos;t.</span>
            </h1>
            <p className="mb-8 max-w-md text-[15px] leading-relaxed text-muted-text">
              Meridian reads the question, picks the specialist who actually knows the answer — from a
              company&apos;s own documents, or its order data — and hands anything risky to a person instead
              of guessing. Every one of those decisions is logged and measured, not just claimed.
            </p>
            <div className="flex items-center gap-4">
              <Link
                href="/demo"
                className="rounded-full bg-text px-5 py-2.5 text-sm font-medium text-canvas transition-opacity hover:opacity-90"
              >
                Try the demo →
              </Link>
              <a href="#components" className="font-mono text-[11px] uppercase tracking-wider text-muted-text hover:text-text">
                see how it works
              </a>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-10 max-w-md lg:absolute lg:right-8 lg:bottom-0 lg:mt-0 lg:w-[380px] xl:right-16"
          >
            <HeroRouting />
          </motion.div>
        </div>

        <div className="lg:hidden">
          <img
            src="https://images.unsplash.com/photo-1515378791036-0648a3ef77b2?fm=jpg&q=80&w=1200&auto=format&fit=crop"
            alt=""
            className="h-48 w-full object-cover"
            style={{ objectPosition: "50% 45%" }}
          />
        </div>
      </section>

      {/* live metrics */}
      <section id="metrics" className="border-t border-line px-6 py-16">
        <div className="mx-auto max-w-5xl">
          <p className="mb-1 text-center font-mono text-[11px] uppercase tracking-[0.15em] text-faint-text">
            live from the database
          </p>
          <h2 className="mb-8 text-center text-2xl font-semibold text-text">Not hardcoded. Not a screenshot.</h2>
          <LiveMetrics />
        </div>
      </section>

      {/* pillars */}
      <section className="border-t border-line px-6 py-16">
        <div className="mx-auto max-w-5xl">
          <h2 className="mb-10 text-center text-2xl font-semibold text-text">Three properties, enforced structurally</h2>
          <div className="grid gap-5 sm:grid-cols-3">
            {PILLARS.map((p, i) => (
              <motion.div
                key={p.title}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
                className="rounded-xl border border-line bg-surface p-5"
              >
                <div className="mb-3 h-[2px] w-8 rounded-full" style={{ background: p.color }} />
                <h3 className="mb-2 text-base font-semibold text-text">{p.title}</h3>
                <p className="text-sm leading-relaxed text-muted-text">{p.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* components */}
      <section id="components" className="border-t border-line px-6 py-16">
        <div className="mx-auto max-w-5xl">
          <p className="mb-1 text-center font-mono text-[11px] uppercase tracking-[0.15em] text-faint-text">
            the pieces
          </p>
          <h2 className="mb-10 text-center text-2xl font-semibold text-text">Four agents. Four systems.</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {COMPONENTS.map((c, i) => (
              <motion.div
                key={c.name}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ duration: 0.35, delay: (i % 4) * 0.06 }}
                className="relative overflow-hidden rounded-xl border border-line bg-surface p-4"
              >
                <div className="absolute inset-x-0 top-0 h-[2px] opacity-70" style={{ background: c.color }} />
                <div className="mb-1.5 flex items-baseline justify-between">
                  <span className="text-sm font-medium text-text">{c.name}</span>
                  <span className="font-mono text-[10px] uppercase tracking-wider text-faint-text">{c.kind}</span>
                </div>
                <p className="text-[13px] leading-relaxed text-muted-text">{c.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* architecture */}
      <section className="border-t border-line px-6 py-16">
        <div className="mx-auto max-w-4xl">
          <p className="mb-1 text-center font-mono text-[11px] uppercase tracking-[0.15em] text-faint-text">
            architecture
          </p>
          <h2 className="mb-10 text-center text-2xl font-semibold text-text">Three tiers, one guarantee</h2>
          <div className="flex flex-col gap-3">
            {ARCH_ROWS.map((row, i) => (
              <motion.div
                key={row.label}
                initial={{ opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className="rounded-xl border border-line bg-surface p-4"
              >
                <p className="mb-2.5 font-mono text-[10px] uppercase tracking-[0.15em] text-faint-text">{row.label}</p>
                <div className="flex flex-wrap gap-2">
                  {row.items.map((item) => (
                    <span key={item} className="rounded-md bg-canvas px-2.5 py-1 font-mono text-[11.5px] text-text">
                      {item}
                    </span>
                  ))}
                </div>
                {i < ARCH_ROWS.length - 1 && (
                  <div className="mt-3 flex justify-center text-faint-text">↓</div>
                )}
              </motion.div>
            ))}
          </div>
          <p className="mt-6 text-center text-sm text-muted-text">
            Row-level security governs the postgres tier — the application layer cannot leak across tenants
            even with a broken query. It&apos;s proven, not assumed: an automated cross-tenant test suite runs
            in CI on every commit.
          </p>
        </div>
      </section>

      {/* CTA + footer */}
      <section className="border-t border-line px-6 py-20 text-center">
        <h2 className="mb-3 text-2xl font-semibold text-text">See it route a question in real time.</h2>
        <p className="mx-auto mb-8 max-w-md text-sm text-muted-text">
          Pick a demo company, ask something clean, then ask something vague — and watch it decide it doesn&apos;t
          know.
        </p>
        <Link
          href="/demo"
          className="inline-block rounded-full bg-text px-6 py-3 text-sm font-medium text-canvas transition-opacity hover:opacity-90"
        >
          Try the demo →
        </Link>
      </section>

      <footer className="border-t border-line px-6 py-6">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-3 sm:flex-row">
          <p className="font-mono text-[11px] text-faint-text">meridian — built end to end on free-tier infrastructure</p>
          <a
            href="https://github.com/ANSHUUMAAN5/meridian"
            target="_blank"
            rel="noreferrer"
            className="font-mono text-[11px] uppercase tracking-wider text-muted-text hover:text-text"
          >
            source on github
          </a>
        </div>
      </footer>
    </div>
  );
}

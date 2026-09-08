"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import SiteNav from "./_components/SiteNav";
import HeroRouting from "./_components/HeroRouting";
import LiveMetrics from "./_components/LiveMetrics";
import LiveTenantDemo from "./_components/LiveTenantDemo";
import ThresholdPlayground from "./_components/ThresholdPlayground";

const SETUP = [
  {
    n: "01",
    title: "Bring your own documents",
    body: "Drop in return policies, shipping rules, whatever your support team already answers from. Meridian chunks and embeds them on upload — searchable in a couple of seconds, scoped to you.",
    detail: "txt · md · 500KB per file",
  },
  {
    n: "02",
    title: "Point it at your order system",
    body: "Manifest calls a tool interface, not a specific vendor. The demo is backed by a Postgres orders table; swapping that for a real commerce API is an adapter, not a rewrite.",
    detail: "get_order_status · list_recent_orders · get_return_window",
  },
  {
    n: "03",
    title: "Draw your own line",
    body: "Confidence thresholds are configuration, not constants — a pharmacy needs a different line than a clothing store. Mark whole categories as never-automate and no score can override it.",
    detail: "τ_route · τ_answer · read / write / hard tiers",
  },
  {
    n: "04",
    title: "Watch every decision it makes",
    body: "Each step is logged with the model, the confidence, the latency and the cost. Anything it refuses lands in a human inbox with the full reasoning already attached.",
    detail: "trace · relay · sextant",
  },
];

const PLATFORM = [
  { name: "Compass", kind: "agent", color: "var(--compass)", body: "Reads the message and decides who handles it. Cannot read documents or orders itself — it only routes." },
  { name: "Almanac", kind: "agent", color: "var(--almanac)", body: "Answers from your documents, with a citation for every claim. Has no access to order data at all." },
  { name: "Manifest", kind: "agent", color: "var(--manifest)", body: "Answers account questions through real tool calls, reasoning across as many lookups as it needs." },
  { name: "Beacon", kind: "agent", color: "var(--beacon)", body: "Hands off to a person with a written summary of what was asked, tried and found." },
  { name: "Threshold", kind: "system", color: "var(--faint-text)", body: "The gate. Plain code, no model — a comparison should behave identically every single time." },
  { name: "Sentinel", kind: "agent", color: "var(--danger)", body: "Proposes a refund or cancellation, waits for a genuine confirmation, and only then executes it." },
  { name: "Trace", kind: "system", color: "var(--faint-text)", body: "Records every step: prompt, response, confidence, latency, tokens, cost." },
  { name: "Sextant", kind: "system", color: "var(--faint-text)", body: "Replays a labeled evaluation set and scores the whole system, so the numbers are measured." },
];

const STACK = ["FastAPI", "Postgres + pgvector", "Row-level security", "Next.js", "Groq", "Gemini"];

export default function Landing() {
  return (
    <div className="flex flex-1 flex-col bg-canvas">
      <SiteNav />

      {/* hero */}
      <section className="relative overflow-hidden lg:min-h-[640px]">
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
            style={{ background: "linear-gradient(to top, color-mix(in srgb, var(--canvas) 60%, transparent), transparent 42%)" }}
          />
        </div>

        <div className="relative z-10 mx-auto max-w-6xl px-6 pt-14 pb-16 lg:pt-20 lg:pb-24">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="max-w-xl"
          >
            <p className="mb-4 font-mono text-[11px] uppercase tracking-[0.2em] text-faint-text">
              multi-tenant · multi-agent · confidence-gated
            </p>
            <h1 className="mb-5 text-[42px] font-semibold leading-[1.08] tracking-tight text-text sm:text-5xl">
              Support agents that know
              <br />
              when to stop talking.
            </h1>
            <p className="mb-8 max-w-md text-[15.5px] leading-relaxed text-muted-text">
              Meridian answers your customers from your own documents and order data, routes each question
              to a specialist that can actually reach the right information, and hands anything risky to a
              human instead of guessing — with an accuracy number it can show you.
            </p>
            <div className="flex flex-wrap items-center gap-4">
              <a
                href="#demo"
                className="rounded-full bg-text px-5 py-2.5 text-sm font-medium text-canvas transition-opacity hover:opacity-90"
              >
                See it answer something →
              </a>
              <a href="#setup" className="text-[13.5px] text-muted-text transition-colors hover:text-text">
                How you&apos;d set it up
              </a>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-10 max-w-md lg:absolute lg:right-8 lg:bottom-4 lg:mt-0 lg:w-[370px] xl:right-16"
          >
            <HeroRouting />
          </motion.div>
        </div>

        <div className="lg:hidden">
          <img
            src="https://images.unsplash.com/photo-1515378791036-0648a3ef77b2?fm=jpg&q=80&w=1200&auto=format&fit=crop"
            alt=""
            className="h-44 w-full object-cover"
            style={{ objectPosition: "50% 45%" }}
          />
        </div>
      </section>

      {/* stack strip */}
      <section className="border-y border-line bg-surface/50">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-3 px-6 py-4">
          <span className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-faint-text">
            built on
          </span>
          {STACK.map((s) => (
            <span key={s} className="font-mono text-[12px] text-muted-text">
              {s}
            </span>
          ))}
        </div>
      </section>

      {/* live demo */}
      <Section
        id="demo"
        eyebrow="try it right here"
        title="Two companies. One codebase. Different answers."
        lede="This runs against the live backend — real retrieval, real routing, real gating. Ask both companies the same question and watch them diverge, because each one only ever sees its own data."
      >
        <LiveTenantDemo />
      </Section>

      {/* setup */}
      <Section
        id="setup"
        eyebrow="for your own company"
        title="Four things to make it yours"
        lede="The agents are generic. The knowledge, the data and the limits are not — that's the whole design. Point it at a clothing store and it answers about sizing; point it at a pharmacy and it refuses to answer about dosages."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          {SETUP.map((s, i) => (
            <motion.div
              key={s.n}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.4, delay: (i % 2) * 0.08 }}
              className="rounded-2xl border border-line bg-surface p-6"
            >
              <span className="font-mono text-[11px] tracking-[0.1em] text-faint-text">{s.n}</span>
              <h3 className="mt-3 mb-2 text-[17px] font-semibold text-text">{s.title}</h3>
              <p className="mb-4 text-[14px] leading-relaxed text-muted-text">{s.body}</p>
              <p className="font-mono text-[10.5px] text-faint-text">{s.detail}</p>
            </motion.div>
          ))}
        </div>
      </Section>

      {/* gating */}
      <Section
        id="gating"
        eyebrow="the mechanic"
        title="Move the line yourself"
        lede="Every answer is scored, and one number decides whether the system acts alone. These are real confidence values from a real evaluation run — drag the threshold and watch what changes hands."
      >
        <ThresholdPlayground />
      </Section>

      {/* platform */}
      <Section
        id="platform"
        eyebrow="the platform"
        title="Five agents, three systems, separate keys to the building"
        lede="Almanac physically cannot read order data. Manifest physically cannot read documents. Only Sentinel can execute a write, and only after a customer confirms it. A compromised document can produce a bad sentence — never a bad action."
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {PLATFORM.map((c, i) => (
            <motion.div
              key={c.name}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.35, delay: (i % 4) * 0.06 }}
              className="relative overflow-hidden rounded-2xl border border-line bg-surface p-5"
            >
              <div className="absolute inset-x-0 top-0 h-[2px] opacity-70" style={{ background: c.color }} />
              <div className="mb-2 flex items-baseline justify-between gap-2">
                <span className="text-[15px] font-semibold text-text">{c.name}</span>
                <span className="font-mono text-[9.5px] uppercase tracking-wider text-faint-text">{c.kind}</span>
              </div>
              <p className="text-[13px] leading-relaxed text-muted-text">{c.body}</p>
            </motion.div>
          ))}
        </div>
      </Section>

      {/* evidence */}
      <Section
        id="evidence"
        eyebrow="evidence, not adjectives"
        title="Every number here is read from the database"
        lede="Accuracy comes from a hand-labeled evaluation set replayed against the running system. Nothing on this page is a screenshot, and nothing is typed in by hand."
      >
        <LiveMetrics />

        <div className="mt-8 rounded-2xl border border-line bg-surface p-6">
          <p className="mb-4 font-mono text-[10.5px] uppercase tracking-[0.14em] text-faint-text">
            how the isolation actually works
          </p>
          <div className="flex flex-col gap-2.5">
            {[
              { label: "browser", items: ["landing", "console"] },
              { label: "fastapi", items: ["compass", "almanac", "manifest", "beacon", "sentinel"] },
              { label: "postgres + pgvector", items: ["tenants", "documents", "orders", "traces"] },
            ].map((row, i, arr) => (
              <div key={row.label}>
                <div className="rounded-xl border border-line bg-canvas p-4">
                  <p className="mb-2.5 font-mono text-[10px] uppercase tracking-[0.15em] text-faint-text">
                    {row.label}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {row.items.map((item) => (
                      <span
                        key={item}
                        className="rounded-full border border-line px-2.5 py-1 font-mono text-[11.5px] text-text"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
                {i < arr.length - 1 && <div className="py-1 text-center text-faint-text">↓</div>}
              </div>
            ))}
          </div>
          <p className="mt-5 text-[14px] leading-relaxed text-muted-text">
            Tenant separation is enforced by Postgres row-level security, not by application code
            remembering to filter. A deliberately unfiltered query still returns only the current
            tenant&apos;s rows — and an automated cross-tenant test suite proves it on every commit.
          </p>
        </div>
      </Section>

      {/* CTA */}
      <section className="border-t border-line px-6 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="mb-4 text-3xl font-semibold tracking-tight text-text">
            Ask it something it can&apos;t answer.
          </h2>
          <p className="mx-auto mb-8 max-w-md text-[15px] leading-relaxed text-muted-text">
            The console is open — no signup. Ask something clean and watch it answer with a citation.
            Then ask something vague, and watch it decline instead of inventing one.
          </p>
          <Link
            href="/demo"
            className="inline-block rounded-full bg-text px-6 py-3 text-sm font-medium text-canvas transition-opacity hover:opacity-90"
          >
            Open the console →
          </Link>
        </div>
      </section>

      {/* footer */}
      <footer className="border-t border-line bg-surface/40">
        <div className="mx-auto max-w-6xl px-6 py-12">
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <div className="mb-3 flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-text" />
                <span className="font-mono text-[12px] uppercase tracking-[0.15em] text-text">meridian</span>
              </div>
              <p className="text-[13px] leading-relaxed text-muted-text">
                Multi-tenant, multi-agent customer support — built end to end on free-tier infrastructure.
              </p>
            </div>

            <FooterCol
              title="Product"
              links={[
                { label: "Live demo", href: "#demo" },
                { label: "Set it up", href: "#setup" },
                { label: "Gating", href: "#gating" },
                { label: "Platform", href: "#platform" },
              ]}
            />
            <FooterCol
              title="The console"
              links={[
                { label: "Chat playground", href: "/demo" },
                { label: "Traces", href: "/demo" },
                { label: "Relay inbox", href: "/demo" },
                { label: "Evaluation", href: "/demo" },
              ]}
            />
            <FooterCol
              title="Engineering"
              links={[
                { label: "Source on GitHub", href: "https://github.com/ANSHUUMAAN5/meridian" },
                { label: "Decision records", href: "https://github.com/ANSHUUMAAN5/meridian/tree/main/docs/adr" },
                { label: "Evaluation harness", href: "https://github.com/ANSHUUMAAN5/meridian/tree/main/sextant" },
              ]}
            />
          </div>

          <div className="mt-10 border-t border-line pt-6">
            <p className="font-mono text-[10.5px] text-faint-text">
              Kite &amp; Co and Nimbus Health are fictional demo tenants. Their documents and orders were
              written for this project.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Section({
  id,
  eyebrow,
  title,
  lede,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  lede: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-16 border-t border-line px-6 py-20">
      <div className="mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.45 }}
          className="mb-10 max-w-2xl"
        >
          <p className="mb-3 font-mono text-[10.5px] uppercase tracking-[0.16em] text-faint-text">
            {eyebrow}
          </p>
          <h2 className="mb-4 text-[30px] font-semibold leading-[1.15] tracking-tight text-text">
            {title}
          </h2>
          <p className="text-[15px] leading-relaxed text-muted-text">{lede}</p>
        </motion.div>
        {children}
      </div>
    </section>
  );
}

function FooterCol({ title, links }: { title: string; links: { label: string; href: string }[] }) {
  return (
    <div>
      <p className="mb-3 font-mono text-[10.5px] uppercase tracking-[0.14em] text-faint-text">{title}</p>
      <ul className="flex flex-col gap-2">
        {links.map((l) => (
          <li key={l.label}>
            <a
              href={l.href}
              className="text-[13px] text-muted-text transition-colors hover:text-text"
              {...(l.href.startsWith("http") ? { target: "_blank", rel: "noreferrer" } : {})}
            >
              {l.label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

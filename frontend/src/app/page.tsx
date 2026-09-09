"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import SiteNav from "./_components/SiteNav";
import HeroRouting from "./_components/HeroRouting";
import LiveMetrics from "./_components/LiveMetrics";
import LiveTenantDemo from "./_components/LiveTenantDemo";
import ThresholdPlayground from "./_components/ThresholdPlayground";
import BenefitCards from "./_components/BenefitCards";

const HERO_PHOTO =
  "https://images.unsplash.com/photo-1515378791036-0648a3ef77b2?fm=jpg&q=80&w=1800&auto=format&fit=crop";
const SUPPORT_PHOTO =
  "https://images.unsplash.com/photo-1626863905121-3b0c0ed7b94c?fm=jpg&q=80&w=1200&auto=format&fit=crop";

const SETUP = [
  {
    n: "01",
    title: "Add what you already know",
    body: "Your policies, searchable in seconds.",
  },
  {
    n: "02",
    title: "Connect your orders",
    body: "Real answers from your real system.",
  },
  {
    n: "03",
    title: "Say what it may decide alone",
    body: "Mark what should always reach a person.",
  },
  {
    n: "04",
    title: "Watch it work",
    body: "Every answer, every refusal, in one place.",
  },
];

const TEAM = [
  { name: "Compass", role: "Decides who should handle it", color: "var(--compass)" },
  { name: "Almanac", role: "Answers from your documents", color: "var(--almanac)" },
  { name: "Manifest", role: "Looks up real order details", color: "var(--manifest)" },
  { name: "Beacon", role: "Hands over to your team", color: "var(--beacon)" },
  { name: "Sentinel", role: "Asks before changing anything", color: "var(--danger)" },
];

export default function Landing() {
  return (
    <div className="flex flex-1 flex-col bg-canvas">
      <SiteNav />

      {/* hero */}
      <section className="relative overflow-hidden lg:min-h-[620px]">
        <div
          className="pointer-events-none absolute -left-40 -top-40 h-[560px] w-[560px] opacity-40 lg:opacity-60"
          style={{
            background:
              "radial-gradient(circle farthest-corner at 30% 30%, rgba(202,248,255,0.9) 0%, rgba(186,204,227,0.55) 45%, transparent 75%)",
          }}
        />
        <div className="pointer-events-none absolute inset-y-0 right-0 hidden w-[56%] lg:block">
          <img src={HERO_PHOTO} alt="" className="h-full w-full object-cover" style={{ objectPosition: "60% 45%" }} />
          <div
            className="absolute inset-0"
            style={{ background: "linear-gradient(to right, var(--canvas) 0%, color-mix(in srgb, var(--canvas) 55%, transparent) 24%, transparent 50%)" }}
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
            <h1 className="mb-8 text-[42px] font-semibold leading-[1.08] tracking-tight text-text sm:text-[52px]">
              Answer your customers.
              <br />
              Know when not to.
            </h1>
            <div className="flex flex-wrap items-center gap-4">
              <a
                href="#demo"
                className="rounded-full bg-text px-5 py-2.5 text-sm font-medium text-canvas transition-opacity hover:opacity-90"
              >
                See it answer something
              </a>
              <a href="#setup" className="text-[14px] text-muted-text transition-colors hover:text-text">
                How you&apos;d set it up →
              </a>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-10 max-w-md lg:absolute lg:right-8 lg:bottom-4 lg:mt-0 lg:w-[360px] xl:right-16"
          >
            <HeroRouting />
          </motion.div>
        </div>

        <div className="lg:hidden">
          <img src={HERO_PHOTO} alt="" className="h-44 w-full object-cover" style={{ objectPosition: "50% 45%" }} />
        </div>
      </section>

      {/* benefit cards */}
      <section className="px-6 py-16">
        <div className="mx-auto max-w-6xl">
          <motion.h2
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            className="mb-8 max-w-2xl text-[30px] font-semibold leading-[1.15] tracking-tight text-text"
          >
            What it actually does
          </motion.h2>
          <BenefitCards />
        </div>
      </section>

      {/* live demo */}
      <Section
        id="demo"
        bg="var(--panel-sage)"
        title="Try it on two different companies"
        lede="This is the real thing, not a video."
      >
        <LiveTenantDemo />
      </Section>

      {/* setup */}
      <Section
        id="setup"
        bg="var(--panel-sand)"
        title="Four steps to point it at your business"
        lede="Same system for everyone. What it knows is entirely yours."
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
              <h3 className="mt-3 mb-2 text-[18px] font-semibold text-text">{s.title}</h3>
              <p className="text-[14px] leading-relaxed text-muted-text">{s.body}</p>
            </motion.div>
          ))}
        </div>
      </Section>

      {/* safety */}
      <Section
        id="safety"
        bg="var(--panel-blush)"
        title="It asks a person when it should"
        lede="Drag the slider. These are real scores from a real test run."
      >
        <div className="grid gap-6 lg:grid-cols-[1fr_300px] lg:items-start">
          <ThresholdPlayground />
          <div className="overflow-hidden rounded-2xl border border-line">
            <img src={SUPPORT_PHOTO} alt="Support team at work" className="h-[240px] w-full object-cover lg:h-[300px]" />
            <p className="bg-surface px-5 py-4 text-[13.5px] leading-relaxed text-muted-text">
              Refusals land in your team&apos;s inbox — question, context, and all.
            </p>
          </div>
        </div>
      </Section>

      {/* the team */}
      <Section
        id="team"
        title="A small team of specialists, not one know-it-all"
        lede="Each one has a single job, and can only reach what that job needs."
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {TEAM.map((c, i) => (
            <motion.div
              key={c.name}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.35, delay: i * 0.06 }}
              className="rounded-2xl border border-line bg-surface p-5"
            >
              <span className="mb-3 block h-2 w-2 rounded-full" style={{ background: c.color }} />
              <p className="mb-1.5 text-[15px] font-semibold text-text">{c.name}</p>
              <p className="text-[13px] leading-relaxed text-muted-text">{c.role}</p>
            </motion.div>
          ))}
        </div>
      </Section>

      {/* numbers */}
      <Section
        id="numbers"
        bg="var(--panel-sky)"
        title="The numbers come from the running system"
        lede="Not a screenshot. Not typed in by hand."
      >
        <LiveMetrics />
      </Section>

      {/* CTA */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="mb-4 text-[32px] font-semibold tracking-tight text-text">
            Try to catch it out.
          </h2>
          <p className="mx-auto mb-8 max-w-md text-[15.5px] leading-relaxed text-muted-text">
            No sign-up. Ask it something it shouldn&apos;t know.
          </p>
          <Link
            href="/demo"
            className="inline-block rounded-full bg-text px-6 py-3 text-sm font-medium text-canvas transition-opacity hover:opacity-90"
          >
            Open the demo
          </Link>
        </div>
      </section>

      {/* footer */}
      <footer className="border-t border-line bg-surface">
        <div className="mx-auto max-w-6xl px-6 py-12">
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <div className="mb-3 flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-text" />
                <span className="font-mono text-[12px] uppercase tracking-[0.15em] text-text">meridian</span>
              </div>
              <p className="text-[13px] leading-relaxed text-muted-text">
                Support answered from your own data. A human, always in the loop.
              </p>
            </div>

            <FooterCol
              title="Product"
              links={[
                { label: "See it work", href: "#demo" },
                { label: "Set it up", href: "#setup" },
                { label: "Why it's safe", href: "#safety" },
                { label: "The numbers", href: "#numbers" },
              ]}
            />
            <FooterCol
              title="Try it"
              links={[
                { label: "Open the demo", href: "/demo" },
                { label: "Kite & Co — retail", href: "/demo" },
                { label: "Nimbus Health — pharmacy", href: "/demo" },
              ]}
            />
            <FooterCol
              title="For engineers"
              links={[
                { label: "Source on GitHub", href: "https://github.com/ANSHUUMAAN5/meridian" },
                { label: "Decision records", href: "https://github.com/ANSHUUMAAN5/meridian/tree/main/docs/adr" },
                { label: "Evaluation harness", href: "https://github.com/ANSHUUMAAN5/meridian/tree/main/sextant" },
              ]}
            />
          </div>

          <div className="mt-10 border-t border-line pt-6">
            <p className="text-[12px] text-faint-text">
              Kite &amp; Co and Nimbus Health are fictional companies built to demonstrate this. Their
              documents and orders were written for the project.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Section({
  id,
  title,
  lede,
  bg,
  children,
}: {
  id: string;
  title: string;
  lede: string;
  bg?: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-16 px-6 py-20" style={bg ? { background: bg } : undefined}>
      <div className="mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.45 }}
          className="mb-10 max-w-2xl"
        >
          <h2 className="mb-4 text-[30px] font-semibold leading-[1.15] tracking-tight text-text">{title}</h2>
          <p className="text-[15.5px] leading-relaxed text-muted-text">{lede}</p>
        </motion.div>
        {children}
      </div>
    </section>
  );
}

function FooterCol({ title, links }: { title: string; links: { label: string; href: string }[] }) {
  return (
    <div>
      <p className="mb-3 text-[13px] font-semibold text-text">{title}</p>
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

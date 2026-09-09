"use client";

import { motion } from "framer-motion";
import Link from "next/link";

const DEMO_TENANTS = [
  {
    slug: "kite",
    name: "Kite & Co",
    kind: "Clothing retailer",
    photo:
      "https://images.unsplash.com/photo-1769107805465-bfd41863f1a0?fm=jpg&q=80&w=1000&auto=format&fit=crop",
    pitch:
      "Returns, sizing and delivery — plus a refund it can actually process, once you confirm it.",
    tint: "var(--panel-sage)",
    accent: "var(--manifest)",
    tryThese: [
      "How long do I have to return something?",
      "Where is my order KC4407?",
      "I want a refund for order KC4407",
    ],
  },
  {
    slug: "nimbus",
    name: "Nimbus Health",
    kind: "Online pharmacy",
    photo:
      "https://images.unsplash.com/photo-1580281657527-47f249e8f4df?fm=jpg&q=80&w=1000&auto=format&fit=crop",
    pitch:
      "Prescriptions and refills — with one rule that never bends: nothing medical is ever answered without a person.",
    tint: "var(--panel-sky)",
    accent: "var(--almanac)",
    tryThese: [
      "Can I get my prescription refilled early?",
      "Can I take double the dose if I missed one?",
      "How do I store my medicine?",
    ],
  },
];

export default function DemoPicker() {
  return (
    <div className="flex flex-1 flex-col bg-canvas">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-text" />
            <span className="font-mono text-[12px] uppercase tracking-[0.15em] text-text">meridian</span>
          </Link>
          <Link href="/" className="text-[13.5px] text-muted-text transition-colors hover:text-text">
            ← Back to site
          </Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-14">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="mb-10 max-w-xl"
        >
          <h1 className="mb-3 text-[34px] font-semibold leading-tight tracking-tight text-text">
            Pick a company to try
          </h1>
          <p className="text-[15.5px] leading-relaxed text-muted-text">
            Both run on exactly the same system. Everything that makes them behave differently — their
            documents, their orders, what they&apos;re allowed to decide alone — belongs to them.
            No sign-up, nothing to install.
          </p>
        </motion.div>

        <div className="grid gap-5 md:grid-cols-2">
          {DEMO_TENANTS.map((t, i) => (
            <motion.div
              key={t.slug}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.1 + i * 0.1 }}
              className="flex flex-col overflow-hidden rounded-3xl border border-line"
              style={{ background: t.tint }}
            >
              <div className="relative h-44 overflow-hidden">
                <img src={t.photo} alt="" className="h-full w-full object-cover" />
                <span className="absolute left-4 top-4 rounded-full bg-canvas/90 px-3 py-1 text-[11.5px] font-medium text-text backdrop-blur-sm">
                  {t.kind}
                </span>
              </div>

              <div className="flex flex-1 flex-col p-6">
                <h2 className="mb-2 text-[22px] font-semibold text-text">{t.name}</h2>
                <p className="mb-5 text-[14px] leading-relaxed text-muted-text">{t.pitch}</p>

                <p className="mb-2.5 text-[12px] font-medium text-muted-text">Things worth asking</p>
                <ul className="mb-6 flex flex-col gap-1.5">
                  {t.tryThese.map((q) => (
                    <li
                      key={q}
                      className="rounded-xl border border-line bg-surface px-3.5 py-2 text-[13px] text-text"
                    >
                      {q}
                    </li>
                  ))}
                </ul>

                <Link
                  href={`/store/${t.slug}`}
                  className="mt-auto rounded-full px-5 py-3 text-center text-[14px] font-medium text-canvas transition-opacity hover:opacity-90"
                  style={{ background: "var(--text)" }}
                >
                  Visit {t.name}&apos;s website →
                </Link>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="mt-10 rounded-2xl border border-line bg-surface px-6 py-5"
        >
          <p className="text-[14px] leading-relaxed text-muted-text">
            <span className="font-medium text-text">Try to catch it out.</span> Ask the pharmacy
            something medical and it will refuse, no matter how confidently it could have guessed. Ask
            either one something vague and watch it pass you to a person instead of inventing an answer.
          </p>
        </motion.div>
      </main>
    </div>
  );
}

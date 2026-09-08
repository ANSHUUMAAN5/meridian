"use client";

import { motion } from "framer-motion";

function Card({
  title,
  body,
  from,
  to,
  span,
  children,
}: {
  title: string;
  body: string;
  from: string;
  to: string;
  span?: boolean;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5 }}
      className={`relative flex min-h-[300px] flex-col justify-between overflow-hidden rounded-3xl p-7 ${
        span ? "lg:col-span-3" : ""
      }`}
      style={{ background: `linear-gradient(145deg, ${from}, ${to})` }}
    >
      <h3 className="relative z-10 max-w-[15ch] text-[22px] font-semibold leading-tight text-white">
        {title}
      </h3>

      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        {children}
      </div>

      <p className="relative z-10 max-w-[34ch] text-[13.5px] leading-relaxed text-white/85">{body}</p>
    </motion.div>
  );
}

function Chip({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-xl border border-white/25 bg-white/15 px-3 py-2 text-[12px] text-white backdrop-blur-sm ${className}`}
    >
      {children}
    </div>
  );
}

export default function BenefitCards() {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {/* wide: answers from your own documents */}
      <Card
        span
        title="It answers from your words, not the internet"
        body="Upload the policies your team already answers from. Every reply points back to the document it came from, so you can check it."
        from="#4a8b54"
        to="#356b41"
      >
        <div className="flex w-full max-w-2xl -translate-y-2 items-center justify-center gap-3 px-8 opacity-90">
          <Chip className="hidden sm:block">Returns policy.md</Chip>
          <motion.div
            className="h-px flex-1 bg-white/40"
            initial={{ scaleX: 0 }}
            whileInView={{ scaleX: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.2 }}
            style={{ transformOrigin: "left" }}
          />
          <Chip>
            <span className="opacity-70">30 days from delivery</span>{" "}
            <span className="rounded bg-white/25 px-1.5 py-0.5 text-[10px]">Returns</span>
          </Chip>
        </div>
      </Card>

      {/* knows when to stop */}
      <Card
        title="It knows when to stop and ask"
        body="When it isn't sure enough, it hands the conversation to a person instead of inventing an answer."
        from="#d08a2c"
        to="#a86a18"
      >
        <div className="w-full max-w-[220px] px-2">
          <div className="mb-2 flex justify-between text-[11px] text-white/80">
            <span>how sure</span>
            <span className="tabular-nums">58%</span>
          </div>
          <div className="relative h-2 overflow-hidden rounded-full bg-white/25">
            <motion.div
              className="h-full rounded-full bg-white"
              initial={{ width: 0 }}
              whileInView={{ width: "58%" }}
              viewport={{ once: true }}
              transition={{ duration: 0.9, delay: 0.2 }}
            />
            <div className="absolute inset-y-0 left-[75%] w-px bg-white" />
          </div>
          <p className="mt-2 text-[11px] text-white/80">below the line → a person takes over</p>
        </div>
      </Card>

      {/* never crosses companies */}
      <Card
        title="One company never sees another"
        body="Separation is enforced by the database itself, not by code remembering to filter. An automated test proves it on every change."
        from="#2e7da8"
        to="#1f5e80"
      >
        <div className="flex w-full max-w-[240px] items-center gap-2 px-2">
          <Chip className="flex-1 text-center">Kite &amp; Co</Chip>
          <motion.span
            className="text-[18px] text-white/70"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.4 }}
          >
            ⊘
          </motion.span>
          <Chip className="flex-1 text-center">Nimbus</Chip>
        </div>
      </Card>

      {/* every decision recorded */}
      <Card
        title="Every decision is on the record"
        body="Which specialist answered, how sure it was, what it cost, how long it took — written down for every single message."
        from="#9c5a7d"
        to="#7a4260"
      >
        <div className="flex w-full max-w-[210px] flex-col gap-1.5 px-2">
          {["compass · routed", "almanac · found it", "answer · sent"].map((s, i) => (
            <motion.div
              key={s}
              initial={{ opacity: 0, x: -8 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.15 * i + 0.2 }}
            >
              <Chip>{s}</Chip>
            </motion.div>
          ))}
        </div>
      </Card>
    </div>
  );
}

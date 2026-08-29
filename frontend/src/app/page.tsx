"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { demoLogin, ApiError } from "@/lib/api";
import { useSession } from "@/lib/session";

const DEMO_TENANTS = [
  {
    slug: "kite",
    name: "Kite & Co",
    blurb: "Apparel retailer",
    detail: "Returns, sizing, shipping — and a refund it can actually approve, with your say-so.",
    accent: "var(--compass)",
  },
  {
    slug: "nimbus",
    name: "Nimbus Health",
    blurb: "Online pharmacy",
    detail: "Prescriptions, refills — and one hard rule: medical questions never get answered alone.",
    accent: "var(--almanac)",
  },
];

export default function Home() {
  const router = useRouter();
  const { setSession } = useSession();
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function enterDemo(slug: string) {
    setPending(slug);
    setError(null);
    try {
      const result = await demoLogin(slug);
      setSession({ token: result.access_token, tenant: result.tenant });
      router.push("/console/chat");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not reach the Meridian API.");
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="relative flex flex-1 flex-col items-center justify-center overflow-hidden bg-canvas px-6">
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.4]"
        style={{
          backgroundImage:
            "linear-gradient(to right, color-mix(in srgb, var(--line) 60%, transparent) 1px, transparent 1px), linear-gradient(to bottom, color-mix(in srgb, var(--line) 60%, transparent) 1px, transparent 1px)",
          backgroundSize: "56px 56px",
          maskImage: "radial-gradient(ellipse 60% 50% at 50% 40%, black 0%, transparent 75%)",
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="relative z-10 w-full max-w-xl"
      >
        <div className="mb-12 text-center">
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1, duration: 0.4 }}
            className="mb-4 font-mono text-[11px] uppercase tracking-[0.2em] text-faint-text"
          >
            multi-tenant · multi-agent · confidence-gated
          </motion.p>
          <h1 className="text-5xl font-semibold tracking-tight text-text">Meridian</h1>

          <div className="relative my-6 flex items-center justify-center">
            <div className="h-px w-full max-w-[280px] bg-gradient-to-r from-transparent via-line-strong to-transparent" />
            <motion.div
              className="absolute h-1.5 w-1.5 rounded-full bg-compass"
              style={{ boxShadow: "0 0 12px 2px var(--compass)" }}
              animate={{ left: ["18%", "82%", "18%"] }}
              transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
            />
          </div>

          <p className="text-[15px] leading-relaxed text-muted-text">
            Above the line, the system answers on its own.
            <br />
            Below it, a human takes over. Pick a company to watch it happen.
          </p>
        </div>

        <div className="flex flex-col gap-3">
          {DEMO_TENANTS.map((t, i) => (
            <motion.button
              key={t.slug}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 + i * 0.1, duration: 0.4, ease: "easeOut" }}
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.99 }}
              disabled={pending !== null}
              onClick={() => enterDemo(t.slug)}
              className="group relative overflow-hidden rounded-xl border border-line bg-surface px-5 py-4 text-left transition-colors hover:border-line-strong disabled:opacity-60"
            >
              <div
                className="absolute inset-x-0 top-0 h-[2px] opacity-70"
                style={{ background: t.accent }}
              />
              <div className="flex items-baseline justify-between">
                <span className="text-base font-medium text-text">{t.name}</span>
                <span className="font-mono text-[11px] uppercase tracking-wider text-faint-text">
                  {t.blurb}
                </span>
              </div>
              <p className="mt-1.5 text-sm text-muted-text">{t.detail}</p>
              <div className="mt-3 flex items-center gap-1.5 font-mono text-xs" style={{ color: t.accent }}>
                {pending === t.slug ? (
                  <span>entering…</span>
                ) : (
                  <>
                    <span>enter as {t.name.toLowerCase()}</span>
                    <motion.span
                      className="inline-block"
                      animate={{ x: [0, 3, 0] }}
                      transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
                    >
                      →
                    </motion.span>
                  </>
                )}
              </div>
            </motion.button>
          ))}
        </div>

        {error && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4 rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger"
          >
            {error}
          </motion.p>
        )}
      </motion.div>
    </div>
  );
}

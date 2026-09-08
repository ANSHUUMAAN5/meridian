"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useSession } from "@/lib/session";

const NAV = [
  { href: "/console/chat", label: "chat" },
  { href: "/console/traces", label: "traces" },
  { href: "/console/relay", label: "relay" },
  { href: "/console/knowledge", label: "knowledge" },
  { href: "/console/sextant", label: "sextant" },
];

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { session, loaded, clearSession } = useSession();

  useEffect(() => {
    if (loaded && !session) router.replace("/");
  }, [loaded, session, router]);

  if (!loaded) return null;
  if (!session) return null;

  return (
    <div className="flex flex-1 flex-col bg-canvas">
      <header className="flex flex-col gap-3 border-b border-line px-6 py-3.5 sm:flex-row sm:items-center sm:justify-between sm:gap-5">
        <div className="flex items-center justify-between gap-5 sm:justify-start">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-compass" style={{ boxShadow: "0 0 8px 1px var(--compass)" }} />
            <span className="shrink-0 font-mono text-[11px] uppercase tracking-[0.15em] text-compass">meridian</span>
            <span className="shrink-0 text-sm text-faint-text">/</span>
            <span className="truncate text-sm text-text">{session.tenant.name}</span>
          </div>
          <button
            className="shrink-0 font-mono text-[11px] uppercase tracking-wider text-muted-text transition-colors hover:text-text sm:hidden"
            onClick={() => {
              clearSession();
              router.push("/");
            }}
          >
            exit
          </button>
        </div>
        <nav className="flex items-center gap-4 overflow-x-auto">
          {NAV.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`shrink-0 font-mono text-[11px] uppercase tracking-wider transition-colors ${
                  active ? "text-text" : "text-muted-text hover:text-text"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <button
          className="hidden shrink-0 font-mono text-[11px] uppercase tracking-wider text-muted-text transition-colors hover:text-text sm:block"
          onClick={() => {
            clearSession();
            router.push("/");
          }}
        >
          exit demo
        </button>
      </header>
      <main className="flex flex-1 overflow-hidden">{children}</main>
    </div>
  );
}

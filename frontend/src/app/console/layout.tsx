"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/session";

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { session, loaded, clearSession } = useSession();

  useEffect(() => {
    if (loaded && !session) router.replace("/");
  }, [loaded, session, router]);

  if (!loaded) return null;
  if (!session) return null;

  return (
    <div className="flex flex-1 flex-col bg-canvas">
      <header className="flex items-center justify-between border-b border-line px-6 py-3.5">
        <div className="flex items-center gap-2.5">
          <span className="h-1.5 w-1.5 rounded-full bg-compass" style={{ boxShadow: "0 0 8px 1px var(--compass)" }} />
          <span className="font-mono text-[11px] uppercase tracking-[0.15em] text-compass">meridian</span>
          <span className="text-sm text-faint-text">/</span>
          <span className="text-sm text-text">{session.tenant.name}</span>
        </div>
        <button
          className="font-mono text-[11px] uppercase tracking-wider text-muted-text transition-colors hover:text-text"
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

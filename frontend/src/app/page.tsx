"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { demoLogin, ApiError } from "@/lib/api";
import { useSession } from "@/lib/session";

const DEMO_TENANTS = [
  { slug: "kite", name: "Kite & Co", blurb: "Apparel retailer — returns, sizing, shipping." },
  { slug: "nimbus", name: "Nimbus Health", blurb: "Online pharmacy — prescriptions, refills, hard medical rule." },
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
    <div className="flex flex-1 flex-col items-center justify-center bg-canvas px-6">
      <div className="w-full max-w-xl">
        <div className="mb-10 text-center">
          <p className="mb-2 font-mono text-xs uppercase tracking-widest text-compass">
            multi-tenant · multi-agent
          </p>
          <h1 className="text-4xl font-semibold tracking-tight text-text">Meridian</h1>
          <p className="mt-3 text-muted-text">
            Pick a demo company to see the routing, the gating, and the escalation happen live.
          </p>
        </div>

        <div className="flex flex-col gap-4">
          {DEMO_TENANTS.map((t) => (
            <Card key={t.slug} className="border-line bg-surface">
              <CardHeader>
                <CardTitle className="text-text">{t.name}</CardTitle>
                <CardDescription className="text-muted-text">{t.blurb}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  className="w-full bg-compass text-white hover:opacity-90"
                  disabled={pending !== null}
                  onClick={() => enterDemo(t.slug)}
                >
                  {pending === t.slug ? "Entering…" : `Enter demo as ${t.name}`}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>

        {error && (
          <p className="mt-4 rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

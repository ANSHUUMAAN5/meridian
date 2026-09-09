"use client";

import { use, useState } from "react";
import Script from "next/script";
import { demoLogin, ApiError } from "@/lib/api";
import { useSession } from "@/lib/session";

type StoreConfig = {
  name: string;
  tagline: string;
  blurb: string;
  nav: string[];
  products: string[];
};

const STORES: Record<string, StoreConfig> = {
  kite: {
    name: "KITE & CO",
    tagline: "Everyday essentials, well made.",
    blurb:
      "This page stands in for Kite & Co's own website — plain fonts, ordinary layout, none of Meridian's design. The chat bubble in the corner is the only thing added, by one script tag.",
    nav: ["Men", "Women", "New Arrivals", "Sale"],
    products: ["Linen Camp Shirt", "Wide-Leg Trouser", "Cotton Crew Tee", "Merino Cardigan"],
  },
  nimbus: {
    name: "NIMBUS HEALTH",
    tagline: "Your prescriptions, refilled without the wait.",
    blurb:
      "This page stands in for Nimbus Health's own website — plain fonts, ordinary layout, none of Meridian's design. The chat bubble in the corner is the only thing added, by one script tag.",
    nav: ["Prescriptions", "OTC", "Refills", "Contact"],
    products: ["Cetirizine 10mg (OTC)", "Multivitamin", "Amoxicillin 250mg", "Metformin 500mg"],
  },
};

export default function StorePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const store = STORES[slug] ?? STORES.kite;
  const { setSession } = useSession();
  const [openingConsole, setOpeningConsole] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function openConsole() {
    setOpeningConsole(true);
    setError(null);
    try {
      const result = await demoLogin(slug);
      setSession({ token: result.access_token, tenant: result.tenant, customerId: result.customer_id });
      // A hard navigation, not router.push: the embed script mounts a real DOM
      // node outside React's tree, so a client-side route change would leave
      // the widget bubble stuck on top of the console. Leaving the storefront
      // for the internal tool is a real page boundary anyway.
      window.location.href = "/console/chat";
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not reach the Meridian API.");
      setOpeningConsole(false);
    }
  }

  return (
    <div style={{ fontFamily: "Arial, Helvetica, sans-serif", background: "#fff", color: "#222", minHeight: "100vh" }}>
      <header
        style={{
          borderBottom: "1px solid #e0e0e0",
          padding: "16px 32px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <strong style={{ fontSize: 20 }}>{store.name}</strong>
        <nav style={{ display: "flex", gap: 24, fontSize: 14 }}>
          {store.nav.map((n) => (
            <span key={n}>{n}</span>
          ))}
        </nav>
      </header>

      <section style={{ padding: "64px 32px", textAlign: "center", background: "#f5f5f5" }}>
        <h1 style={{ fontSize: 32, margin: "0 0 12px" }}>{store.tagline}</h1>
        <p style={{ color: "#555", maxWidth: 480, margin: "0 auto" }}>{store.blurb}</p>
      </section>

      <section
        style={{
          padding: "48px 32px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 24,
          maxWidth: 900,
          margin: "0 auto",
        }}
      >
        {store.products.map((name) => (
          <div key={name} style={{ border: "1px solid #e0e0e0", padding: 16, textAlign: "center" }}>
            <div style={{ background: "#eaeaea", height: 120, marginBottom: 12 }} />
            <p style={{ fontSize: 14, margin: 0 }}>{name}</p>
          </div>
        ))}
      </section>

      <footer style={{ borderTop: "1px solid #e0e0e0", padding: "24px 32px", fontSize: 12, color: "#888" }}>
        © {store.name} — a fictional demo storefront.{" "}
        <button
          onClick={openConsole}
          disabled={openingConsole}
          style={{
            marginLeft: 8,
            background: "none",
            border: "none",
            color: "#3355cc",
            textDecoration: "underline",
            cursor: "pointer",
            fontSize: 12,
            padding: 0,
          }}
        >
          {openingConsole ? "Opening…" : "Open the internal console (see how it decided that) →"}
        </button>
        {error && <span style={{ color: "#a33", marginLeft: 8 }}>{error}</span>}
        <span style={{ marginLeft: 12 }}>
          {/* A plain <a>, not next/link: leaving this storefront must be a
              real page load, or the embed script's bubble/iframe -- raw DOM
              nodes outside React's tree -- stay mounted on whatever page
              a client-side transition lands on next. */}
          <a href="/demo" style={{ color: "#888" }}>
            ← back to company picker
          </a>
        </span>
      </footer>

      <Script src="/embed.js" data-tenant={slug} strategy="afterInteractive" />
    </div>
  );
}

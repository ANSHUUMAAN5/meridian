"use client";

import { useEffect } from "react";
import Script from "next/script";

export default function EmbedDemoPage() {
  useEffect(() => {
    document.title = "Kite & Co — Everyday Essentials";
  }, []);

  return (
    <div
      style={{
        fontFamily: "Arial, Helvetica, sans-serif",
        background: "#ffffff",
        color: "#222222",
        minHeight: "100vh",
      }}
    >
      <header
        style={{
          borderBottom: "1px solid #e0e0e0",
          padding: "16px 32px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <strong style={{ fontSize: 20 }}>KITE &amp; CO</strong>
        <nav style={{ display: "flex", gap: 24, fontSize: 14 }}>
          <span>Men</span>
          <span>Women</span>
          <span>New Arrivals</span>
          <span>Sale</span>
        </nav>
      </header>

      <section style={{ padding: "64px 32px", textAlign: "center", background: "#f5f5f5" }}>
        <h1 style={{ fontSize: 32, margin: "0 0 12px" }}>Everyday essentials, well made.</h1>
        <p style={{ color: "#555", maxWidth: 480, margin: "0 auto" }}>
          This page is a stand-in for an ordinary retailer&apos;s own website — plain fonts, plain
          layout, none of Meridian&apos;s own styling. The chat bubble in the corner is the only
          thing added, via one script tag.
        </p>
      </section>

      <section style={{ padding: "48px 32px", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 24, maxWidth: 900, margin: "0 auto" }}>
        {["Linen Camp Shirt", "Wide-Leg Trouser", "Cotton Crew Tee", "Merino Cardigan"].map((name) => (
          <div key={name} style={{ border: "1px solid #e0e0e0", padding: 16, textAlign: "center" }}>
            <div style={{ background: "#eaeaea", height: 120, marginBottom: 12 }} />
            <p style={{ fontSize: 14, margin: 0 }}>{name}</p>
          </div>
        ))}
      </section>

      <footer style={{ borderTop: "1px solid #e0e0e0", padding: "24px 32px", fontSize: 12, color: "#888" }}>
        © Kite &amp; Co — a fictional demo storefront.
      </footer>

      <Script src="/embed.js" data-tenant="kite" strategy="afterInteractive" />
    </div>
  );
}

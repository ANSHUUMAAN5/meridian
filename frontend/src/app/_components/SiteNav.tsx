"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const LINKS = [
  { href: "#demo", label: "See it work" },
  { href: "#setup", label: "Set it up" },
  { href: "#embed", label: "On your website" },
  { href: "#safety", label: "Why it's safe" },
  { href: "#team", label: "The team" },
  { href: "#numbers", label: "The numbers" },
];

export default function SiteNav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-50 transition-colors duration-300 ${
        scrolled ? "border-b border-line bg-canvas/85 backdrop-blur-md" : "border-b border-transparent"
      }`}
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-6 py-3.5">
        <Link href="/" className="flex shrink-0 items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-text" />
          <span className="font-mono text-[12px] uppercase tracking-[0.15em] text-text">meridian</span>
        </Link>

        <nav className="hidden items-center gap-7 lg:flex">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-[13.5px] text-muted-text transition-colors hover:text-text"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="flex shrink-0 items-center gap-4">
          <a
            href="https://github.com/ANSHUUMAAN5/meridian"
            target="_blank"
            rel="noreferrer"
            className="hidden text-[13.5px] text-muted-text transition-colors hover:text-text sm:block"
          >
            Source
          </a>
          <Link
            href="/demo"
            className="rounded-full bg-text px-4 py-2 text-[13.5px] font-medium text-canvas transition-opacity hover:opacity-90"
          >
            Open the console
          </Link>
          <button
            onClick={() => setOpen((v) => !v)}
            aria-label="Menu"
            className="text-muted-text transition-colors hover:text-text lg:hidden"
          >
            <span className="block h-px w-5 bg-current" />
            <span className="mt-1.5 block h-px w-5 bg-current" />
          </button>
        </div>
      </div>

      {open && (
        <div className="border-t border-line bg-canvas px-6 py-3 lg:hidden">
          <nav className="flex flex-col gap-1">
            {LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                onClick={() => setOpen(false)}
                className="py-2 text-[14px] text-muted-text transition-colors hover:text-text"
              >
                {l.label}
              </a>
            ))}
          </nav>
        </div>
      )}
    </header>
  );
}

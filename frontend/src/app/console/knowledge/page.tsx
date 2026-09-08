"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { listDocuments, uploadDocument, ApiError, type DocumentOut } from "@/lib/api";
import { useSession } from "@/lib/session";

const STATUS_COLOR: Record<string, string> = {
  indexed: "var(--manifest)",
  pending: "var(--faint-text)",
  chunking: "var(--beacon)",
  embedding: "var(--beacon)",
  failed: "var(--danger)",
};

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function KnowledgePage() {
  const { session } = useSession();
  const [documents, setDocuments] = useState<DocumentOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    if (!session) return;
    listDocuments(session.token).then(setDocuments).catch(() => {});
  }, [session]);

  useEffect(load, [load]);

  async function handleFile(file: File) {
    if (!session) return;
    setError(null);
    setUploading(true);
    try {
      const title = file.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " ");
      await uploadDocument(session.token, title, file);
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not reach the Meridian API.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-6 py-6">
      <div className="mx-auto w-full max-w-2xl">
        <p className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-faint-text">knowledge base</p>
        <h1 className="mb-6 text-xl font-semibold text-text">Documents</h1>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const file = e.dataTransfer.files[0];
            if (file) handleFile(file);
          }}
          onClick={() => fileInput.current?.click()}
          className={`mb-6 cursor-pointer rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
            dragOver ? "border-compass bg-compass/5" : "border-line hover:border-line-strong"
          }`}
        >
          <input
            ref={fileInput}
            type="file"
            accept=".txt,.md"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
              e.target.value = "";
            }}
          />
          {uploading ? (
            <p className="font-mono text-sm text-muted-text">indexing…</p>
          ) : (
            <>
              <p className="text-sm text-text">Drop a .txt or .md file here, or click to browse.</p>
              <p className="mt-1 font-mono text-[11px] text-faint-text">
                Chunked, embedded, and searchable within a couple seconds.
              </p>
            </>
          )}
        </div>

        {error && (
          <p className="mb-4 rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</p>
        )}

        {documents === null && <p className="text-sm text-muted-text">Loading…</p>}

        <div className="flex flex-col gap-2">
          <AnimatePresence>
            {documents?.map((d) => (
              <motion.div
                key={d.id}
                layout
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between rounded-lg border border-line bg-surface px-4 py-3"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm text-text">{d.title}</p>
                  <p className="font-mono text-[11px] text-faint-text">
                    {d.source ?? "—"} · {timeAgo(d.uploaded_at)} · {d.chunk_count} chunk
                    {d.chunk_count === 1 ? "" : "s"}
                  </p>
                </div>
                <span
                  className="shrink-0 rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase"
                  style={{
                    color: STATUS_COLOR[d.status] ?? "var(--faint-text)",
                    borderColor: `color-mix(in srgb, ${STATUS_COLOR[d.status] ?? "var(--faint-text)"} 35%, transparent)`,
                    background: `color-mix(in srgb, ${STATUS_COLOR[d.status] ?? "var(--faint-text)"} 12%, transparent)`,
                  }}
                >
                  {d.status}
                </span>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

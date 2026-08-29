"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "meridian_session";

export type Session = {
  token: string;
  tenant: { id: string; name: string; slug: string };
};

function readSession(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    return null;
  }
}

export function useSession() {
  const [session, setSessionState] = useState<Session | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setSessionState(readSession());
    setLoaded(true);
  }, []);

  const setSession = useCallback((next: Session) => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setSessionState(next);
  }, []);

  const clearSession = useCallback(() => {
    window.localStorage.removeItem(STORAGE_KEY);
    setSessionState(null);
  }, []);

  return { session, loaded, setSession, clearSession };
}

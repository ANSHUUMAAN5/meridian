export const AGENT_STYLE: Record<string, { color: string; label: string }> = {
  compass: { color: "var(--compass)", label: "compass" },
  almanac: { color: "var(--almanac)", label: "almanac" },
  manifest: { color: "var(--manifest)", label: "manifest" },
  beacon: { color: "var(--beacon)", label: "beacon" },
  sentinel: { color: "var(--danger)", label: "sentinel" },
  threshold: { color: "var(--faint-text)", label: "threshold" },
  none: { color: "var(--faint-text)", label: "none" },
};

export const TAU_ROUTE = 0.75;

export function agentStyle(name: string) {
  return AGENT_STYLE[name] ?? AGENT_STYLE.none;
}

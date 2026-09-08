const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Citation = {
  index: number;
  document_id: string;
  document_title: string;
  similarity: number;
};

export type ChatResponse = {
  conversation_id: string;
  answer: string;
  intent: string;
  confidence: number;
  agent: string;
  escalated: boolean;
  escalation_id: string | null;
  grounded: boolean | null;
  citations: Citation[];
  awaiting_confirmation: boolean;
};

export type DemoLoginResponse = {
  access_token: string;
  token_type: string;
  tenant: { id: string; name: string; slug: string };
  customer_id: string | null;
};

export type ConversationSummary = {
  id: string;
  external_customer_id: string | null;
  created_at: string;
  message_count: number;
  last_message_preview: string | null;
  has_open_escalation: boolean;
};

export type MessageOut = {
  id: string;
  role: "customer" | "assistant" | "system";
  content: string;
  created_at: string;
};

export type TraceStepOut = {
  step: number;
  agent_name: string;
  model: string | null;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  confidence: number | null;
  latency_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  created_at: string;
};

export type ConversationDetail = {
  id: string;
  external_customer_id: string | null;
  created_at: string;
  messages: MessageOut[];
  traces: TraceStepOut[];
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json();
}

export function demoLogin(tenant: string): Promise<DemoLoginResponse> {
  return request("/auth/demo", { method: "POST", body: JSON.stringify({ tenant }) });
}

export function listConversations(token: string): Promise<ConversationSummary[]> {
  return request("/conversations", { headers: { Authorization: `Bearer ${token}` } });
}

export function getConversation(token: string, id: string): Promise<ConversationDetail> {
  return request(`/conversations/${id}`, { headers: { Authorization: `Bearer ${token}` } });
}

export type SextantSummary = {
  total_cases: number;
  by_kind: Record<string, number>;
  routing_accuracy: number;
  routing_escalation_accuracy: number;
  escalation_slice_correct: string;
  adversarial_safe_rate?: string;
  hard_negative_refusal_rate: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
};

export type SextantRunSummary = { run_id: string; summary: SextantSummary };
export type SextantCase = {
  id: string;
  kind: string;
  tenant: string;
  message: string;
  expected_intent: string;
  actual_intent: string;
  intent_correct: boolean;
  expected_escalate: boolean;
  actual_escalate: boolean;
  escalate_correct: boolean;
  agent: string;
  confidence: number;
  answer?: string;
  latency_ms: number;
};
export type SextantRunDetail = { run_id: string; summary: SextantSummary; cases: SextantCase[] };

export function listSextantRuns(token: string): Promise<SextantRunSummary[]> {
  return request("/sextant/runs", { headers: { Authorization: `Bearer ${token}` } });
}

export function getSextantRun(token: string, runId: string): Promise<SextantRunDetail> {
  return request(`/sextant/runs/${runId}`, { headers: { Authorization: `Bearer ${token}` } });
}

export type EscalationOut = {
  id: string;
  conversation_id: string;
  reason: string;
  confidence: number | null;
  status: "open" | "claimed" | "resolved";
  assigned_to: string | null;
  resolution_note: string | null;
  resolved_at: string | null;
  created_at: string;
};

export function listEscalations(token: string, status?: string): Promise<EscalationOut[]> {
  const qs = status ? `?status=${status}` : "";
  return request(`/escalations${qs}`, { headers: { Authorization: `Bearer ${token}` } });
}

export function claimEscalation(token: string, id: string): Promise<EscalationOut> {
  return request(`/escalations/${id}/claim`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
}

export type DocumentOut = {
  id: string;
  title: string;
  source: string | null;
  status: string;
  chunk_count: number;
  uploaded_at: string;
};

export function listDocuments(token: string): Promise<DocumentOut[]> {
  return request("/documents", { headers: { Authorization: `Bearer ${token}` } });
}

export async function uploadDocument(token: string, title: string, file: File): Promise<DocumentOut> {
  const form = new FormData();
  form.append("title", title);
  form.append("file", file);
  const res = await fetch(`${API_URL}/documents`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json();
}

export function resolveEscalation(token: string, id: string, resolutionNote: string): Promise<EscalationOut> {
  return request(`/escalations/${id}/resolve`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ resolution_note: resolutionNote }),
  });
}

export function sendChatMessage(
  token: string,
  input: { message: string; conversation_id?: string; customer_id?: string },
): Promise<ChatResponse> {
  return request("/chat", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(input),
  });
}

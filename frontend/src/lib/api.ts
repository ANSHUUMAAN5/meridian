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

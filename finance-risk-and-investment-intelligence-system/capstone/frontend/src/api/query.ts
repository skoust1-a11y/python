import { api, BASE, ApiError } from "./client";
import { tokenStorage } from "../auth/tokenStorage";
import type { ChatSession, ChatTurn, PolicyDocument, PolicyDocumentDetail, PortfolioBook, QueryResponse, User } from "./types";

export function runQuery(
  query: string,
  evidence_mode: "corpus" | "current" = "corpus",
  symbol?: string,
  profile_id?: string,
  replace_note = false,
  session_id?: string,
) {
  return api<QueryResponse>("/api/v1/query", {
    method: "POST",
    body: JSON.stringify({
      query,
      session_id: session_id || undefined,
      options: { evidence_mode, explain_routing: true, symbol, profile_id, replace_note },
    }),
  });
}

export async function streamQuery(
  query: string,
  evidence_mode: "corpus" | "current" = "corpus",
  onEvent?: (event: string, data: unknown) => void,
  symbol?: string,
  profile_id?: string,
  replace_note = false,
  session_id?: string,
): Promise<QueryResponse> {
  const headers = new Headers();
  headers.set("Content-Type", "application/json");
  const token = tokenStorage.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${BASE}/api/v1/query/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      query,
      session_id: session_id || undefined,
      options: { evidence_mode, explain_routing: true, symbol, profile_id, replace_note },
    }),
  });
  if (res.status === 401) {
    tokenStorage.clear();
    window.location.assign("/login");
    throw new ApiError(401, await res.json().catch(() => ({})));
  }
  if (!res.ok) {
    throw new ApiError(res.status, await res.json().catch(() => ({})));
  }
  const reader = res.body?.getReader();
  if (!reader) {
    throw new Error("Streaming is not available in this browser");
  }
  const decoder = new TextDecoder();
  let buf = "";
  let donePayload: QueryResponse | null = null;
  let skipTokens = false;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const blocks = buf.split("\n\n");
    buf = blocks.pop() || "";
    for (const block of blocks) {
      const ev = block.match(/^event: (.+)$/m)?.[1]?.trim();
      const dataLine = block.match(/^data: (.*)$/m)?.[1];
      if (!ev || dataLine == null) continue;
      const data = JSON.parse(dataLine);
      if (ev === "error") {
        throw new ApiError(400, data);
      }
      if (ev === "escalation") skipTokens = true;
      if (ev === "token" && skipTokens) continue;
      onEvent?.(ev, data);
      if (ev === "done") donePayload = data as QueryResponse;
    }
  }
  if (!donePayload) {
    throw new Error("Stream ended without a done event");
  }
  return donePayload;
}

export function listSessions() {
  return api<{ sessions: ChatSession[] }>("/api/v1/sessions");
}

export function renameSession(sessionId: string, title: string) {
  return api<{ session_id: string; title: string }>(`/api/v1/sessions/${encodeURIComponent(sessionId)}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

export function getSessionTurns(sessionId: string) {
  return api<{ session_id: string; title: string; turns: ChatTurn[] }>(
    `/api/v1/sessions/${encodeURIComponent(sessionId)}/turns`,
  );
}

export function deleteSession(sessionId: string) {
  return api<{ deleted: string }>(`/api/v1/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
}

export function clearSessions() {
  return api<{ deleted: number }>("/api/v1/sessions", { method: "DELETE" });
}

export function listEscalations() {
  return api<{
    escalations: Array<{
      escalation_id: string;
      trace_id: string;
      triggers: string[];
      reviewer?: string;
      created_at?: string;
    }>;
  }>("/api/v1/escalations");
}

export function getTrace(traceId: string) {
  return api<Record<string, unknown>>(`/admin/traces/${traceId}`);
}

export function reindex() {
  return api<{ reindexed: number; chunk_count: number }>("/admin/reindex", { method: "POST" });
}

export function listPortfolios() {
  return api<{ portfolios: PortfolioBook[]; disclaimer: string }>("/api/v1/portfolios");
}

export async function uploadPortfolio(form: FormData) {
  const headers = new Headers();
  const token = tokenStorage.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${BASE}/api/v1/portfolios/upload`, { method: "POST", headers, body: form });
  if (res.status === 401) {
    tokenStorage.clear();
    window.location.assign("/login");
    throw new ApiError(401, await res.json().catch(() => ({})));
  }
  if (!res.ok) {
    throw new ApiError(res.status, await res.json().catch(() => ({})));
  }
  return res.json() as Promise<{
    portfolio: {
      portfolio_id: number;
      portfolio_name: string;
      holding_count: number;
    };
    portfolio_ids: number[];
    disclaimer: string;
  }>;
}

export async function uploadDocument(form: FormData) {
  const headers = new Headers();
  const token = tokenStorage.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${BASE}/api/v1/documents`, { method: "POST", headers, body: form });
  if (res.status === 401) {
    tokenStorage.clear();
    window.location.assign("/login");
    throw new ApiError(401, await res.json().catch(() => ({})));
  }
  if (!res.ok) {
    throw new ApiError(res.status, await res.json().catch(() => ({})));
  }
  return res.json() as Promise<{ document: PolicyDocument; disclaimer: string }>;
}

export function deleteDocument(docId: string) {
  return api<{ deleted: string; disclaimer: string }>(`/api/v1/documents/${encodeURIComponent(docId)}`, {
    method: "DELETE",
  });
}

export function listDocuments(symbol?: string, profileId?: string) {
  const q = new URLSearchParams();
  if (symbol) q.set("symbol", symbol);
  if (profileId) q.set("profile_id", profileId);
  const suffix = q.toString() ? `?${q}` : "";
  return api<{ documents: PolicyDocument[]; disclaimer: string }>(`/api/v1/documents${suffix}`);
}

export function getDocument(docId: string) {
  return api<PolicyDocumentDetail>(`/api/v1/documents/${encodeURIComponent(docId)}`);
}

export async function openDocumentFile(docId: string) {
  const headers = new Headers();
  const token = tokenStorage.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${BASE}/api/v1/documents/${encodeURIComponent(docId)}/file`, { headers });
  if (!res.ok) {
    throw new ApiError(res.status, await res.json().catch(() => ({})));
  }
  const url = URL.createObjectURL(await res.blob());
  window.open(url, "_blank", "noopener");
}

export function listTemplates() {
  return api<{ templates: Array<{ query_id: string; description: string; tables: string[] }> }>(
    "/admin/templates",
  );
}

export function listUsers() {
  return api<{ users: User[] }>("/api/v1/admin/users");
}

export function patchUser(userId: string, body: { role?: string; portfolio_ids?: number[]; status?: string }) {
  return api(`/api/v1/admin/users/${userId}`, { method: "PATCH", body: JSON.stringify(body) });
}

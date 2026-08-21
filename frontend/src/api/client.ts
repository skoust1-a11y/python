import { ApiError } from "@/models/errors";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions extends Omit<RequestInit, "body"> {
  query?: Record<string, QueryValue>;
  body?: unknown;
  parseJson?: boolean;
}

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const url = `${API_BASE}${path}`;
  if (!query) {
    return url;
  }
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === null || value === undefined || value === "") {
      continue;
    }
    params.set(key, String(value));
  }
  const encoded = params.toString();
  return encoded ? `${url}?${encoded}` : url;
}

async function readBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { query, body, parseJson = true, headers, ...init } = options;
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
  const payloadHeaders = new Headers(headers);

  if (body !== undefined && !isFormData && !payloadHeaders.has("Content-Type")) {
    payloadHeaders.set("Content-Type", "application/json");
  }

  const response = await fetch(buildUrl(path, query), {
    ...init,
    headers: payloadHeaders,
    body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
  });

  const payload = await readBody(response);
  if (!response.ok) {
    throw ApiError.fromResponse(
      response.status,
      payload,
      `Request failed (${response.status})`,
    );
  }
  if (!parseJson) {
    return undefined as T;
  }
  return payload as T;
}

export function getJson<T>(path: string, query?: Record<string, QueryValue>): Promise<T> {
  return request<T>(path, { method: "GET", query });
}

export function postJson<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body });
}

export function deleteJson<T>(path: string): Promise<T> {
  return request<T>(path, { method: "DELETE" });
}

export function postForm<T>(path: string, form: FormData): Promise<T> {
  return request<T>(path, { method: "POST", body: form });
}

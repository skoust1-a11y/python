import { tokenStorage } from "../auth/tokenStorage";

export const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(typeof body === "object" && body && "detail" in body ? JSON.stringify((body as { detail: unknown }).detail) : `HTTP ${status}`);
    this.status = status;
    this.body = body;
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) headers.set("Content-Type", "application/json");
  const token = tokenStorage.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (res.status === 401) {
    tokenStorage.clear();
    if (!path.includes("/auth/login")) {
      window.location.assign("/login");
    }
    throw new ApiError(401, await res.json().catch(() => ({})));
  }
  if (!res.ok) {
    throw new ApiError(res.status, await res.json().catch(() => ({})));
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : {}) as T;
}

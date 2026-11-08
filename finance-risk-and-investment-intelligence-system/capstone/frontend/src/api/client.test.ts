import { afterEach, describe, expect, it, vi } from "vitest";
import { tokenStorage } from "../auth/tokenStorage";
import { api, ApiError } from "./client";

function mockFetch(res: Response) {
  const fn = vi.fn(async (_url: string, _init?: RequestInit) => res);
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("api", () => {
  it("sends the bearer token and JSON content type", async () => {
    tokenStorage.set("tok");
    const fetch = mockFetch(new Response(JSON.stringify({ ok: true })));
    expect(await api("/x", { method: "POST", body: "{}" })).toEqual({ ok: true });
    const headers = fetch.mock.calls[0][1]?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer tok");
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("returns undefined for 204", async () => {
    mockFetch(new Response(null, { status: 204 }));
    expect(await api("/x")).toBeUndefined();
  });

  it("raises ApiError with the server detail", async () => {
    mockFetch(new Response(JSON.stringify({ detail: "nope" }), { status: 403 }));
    await expect(api("/x")).rejects.toMatchObject({ status: 403, message: '"nope"' });
  });

  it("clears the token on a failed login without redirecting", async () => {
    tokenStorage.set("tok");
    mockFetch(new Response("{}", { status: 401 }));
    await expect(api("/api/v1/auth/login")).rejects.toBeInstanceOf(ApiError);
    expect(tokenStorage.get()).toBeNull();
  });
});

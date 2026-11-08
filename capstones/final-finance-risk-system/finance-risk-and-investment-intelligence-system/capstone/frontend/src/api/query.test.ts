import { afterEach, describe, expect, it, vi } from "vitest";
import { streamQuery } from "./query";

function sse(...chunks: string[]) {
  const enc = new TextEncoder();
  const body = new ReadableStream({
    start(controller) {
      chunks.forEach((c) => controller.enqueue(enc.encode(c)));
      controller.close();
    },
  });
  vi.stubGlobal("fetch", vi.fn(async () => new Response(body)));
}

afterEach(() => vi.unstubAllGlobals());

describe("streamQuery", () => {
  it("parses events split across chunks and returns the done payload", async () => {
    sse('event: token\ndata: {"t":"Hel', 'lo"}\n\nevent: done\ndata: {"outcome":"answered"}\n\n');
    const events: string[] = [];
    const res = await streamQuery("q", "corpus", (ev) => events.push(ev));
    expect(events).toEqual(["token", "done"]);
    expect(res.outcome).toBe("answered");
  });

  it("drops tokens after an escalation event", async () => {
    sse('event: escalation\ndata: {}\n\nevent: token\ndata: {"t":"x"}\n\nevent: done\ndata: {"outcome":"escalated"}\n\n');
    const events: string[] = [];
    await streamQuery("q", "corpus", (ev) => events.push(ev));
    expect(events).toEqual(["escalation", "done"]);
  });

  it("throws on an error event or a missing done event", async () => {
    sse('event: error\ndata: {"detail":"bad"}\n\n');
    await expect(streamQuery("q")).rejects.toMatchObject({ status: 400 });
    sse('event: token\ndata: {"t":"x"}\n\n');
    await expect(streamQuery("q")).rejects.toThrow("Stream ended without a done event");
  });
});

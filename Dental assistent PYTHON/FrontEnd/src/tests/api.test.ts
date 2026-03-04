import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { invalidateCache } from "../api";

// ---------------------------------------------------------------------------
// Shared SSE helpers — tested via the public streaming functions.
// We use a ReadableStream to simulate backend SSE responses.
// ---------------------------------------------------------------------------

function makeSSEResponse(lines: string[]): Response {
  const body = lines.join("\n") + "\n";
  return new Response(body, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

beforeEach(() => {
  invalidateCache(); // clear TTL cache between tests
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("invalidateCache", () => {
  it("clears all cache entries without throwing", () => {
    expect(() => invalidateCache()).not.toThrow();
  });

  it("clears a specific cache key without throwing", () => {
    expect(() => invalidateCache("checkModelStatus")).not.toThrow();
  });
});

describe("summarizeTextStream", () => {
  it("calls onChunk for each token and onComplete with full text", async () => {
    const { summarizeTextStream } = await import("../api");

    const sseLines = [
      'data: {"chunk":"Hello"}',
      'data: {"chunk":" world"}',
      "data: [DONE]",
    ];
    vi.mocked(fetch).mockResolvedValueOnce(makeSSEResponse(sseLines));

    const chunks: string[] = [];
    let completed = "";

    await summarizeTextStream(
      "transcript",
      (c) => chunks.push(c),
      (full) => { completed = full; },
    );

    expect(chunks).toEqual(["Hello", " world"]);
    expect(completed).toBe("Hello world");
  });

  it("calls onError when the backend returns an error payload", async () => {
    const { summarizeTextStream } = await import("../api");

    const sseLines = ['data: {"error":"Model not loaded"}'];
    vi.mocked(fetch).mockResolvedValueOnce(makeSSEResponse(sseLines));

    const onError = vi.fn();
    await summarizeTextStream("text", vi.fn(), vi.fn(), onError);
    expect(onError).toHaveBeenCalledOnce();
    expect(onError.mock.calls[0][0].message).toBe("Model not loaded");
  });

  it("calls onError when fetch returns a non-ok status", async () => {
    const { summarizeTextStream } = await import("../api");
    vi.mocked(fetch).mockResolvedValue(
      new Response("Internal Server Error", { status: 500 })
    );

    const onError = vi.fn();
    await summarizeTextStream("text", vi.fn(), vi.fn(), onError);
    expect(onError).toHaveBeenCalled();
  });
});

describe("summarizeTextStreamRAG", () => {
  it("fires onRAGStatus when rag_enhanced field is present", async () => {
    const { summarizeTextStreamRAG } = await import("../api");

    const sseLines = [
      'data: {"rag_enhanced":true}',
      'data: {"chunk":"Note"}',
      "data: [DONE]",
    ];
    vi.mocked(fetch).mockResolvedValueOnce(makeSSEResponse(sseLines));

    const onRAGStatus = vi.fn();
    const chunks: string[] = [];
    await summarizeTextStreamRAG("text", (c) => chunks.push(c), vi.fn(), onRAGStatus);

    expect(onRAGStatus).toHaveBeenCalledWith(true);
    expect(chunks).toEqual(["Note"]);
  });
});

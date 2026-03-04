import { invoke } from "@tauri-apps/api/core";

// Use environment variable for backend URL, fallback to default
const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:9000";

// ---------------------------------------------------------------------------
// Resilience: retry with backoff, request deduplication, response caching
// ---------------------------------------------------------------------------

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

/**
 * Fetch wrapper that retries on network errors and 5xx responses.
 * Does NOT retry 4xx client errors (auth failures, validation, etc.).
 */
async function fetchWithRetry(
  input: string | URL,
  init?: RequestInit,
  retries = 2,
  baseDelayMs = 500,
): Promise<Response> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(input, init);
      if (res.ok || (res.status >= 400 && res.status < 500)) return res;
      lastError = new Error(`HTTP ${res.status}`);
    } catch (err) {
      lastError = err;
    }
    if (attempt < retries) {
      await sleep(baseDelayMs * 2 ** attempt);
    }
  }
  throw lastError;
}

/** In-flight deduplication: concurrent identical calls share one Promise. */
const _inflight = new Map<string, Promise<unknown>>();

function deduplicated<T>(key: string, fn: () => Promise<T>): Promise<T> {
  const existing = _inflight.get(key);
  if (existing) return existing as Promise<T>;
  const p = fn().finally(() => _inflight.delete(key));
  _inflight.set(key, p);
  return p;
}

/** Simple TTL cache for read-only status endpoints. */
const _cache = new Map<string, { data: unknown; exp: number }>();
const STATUS_CACHE_TTL = 5_000;

function withCache<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
  const hit = _cache.get(key);
  if (hit && Date.now() < hit.exp) return Promise.resolve(hit.data as T);
  return fn().then((data) => {
    _cache.set(key, { data, exp: Date.now() + ttlMs });
    return data;
  });
}

/** Invalidate one or all cached entries (call after mutations). */
export function invalidateCache(key?: string): void {
  if (key) _cache.delete(key);
  else _cache.clear();
}

// Default development API key for local development
// This is safe because the app runs entirely on localhost
const DEFAULT_DEV_KEY = "dental-assistant-local-dev-key";

// Use environment variable for dev API key, or fall back to default for local development
// In production Tauri app, API key comes from the backend
const DEV_API_KEY = import.meta.env.VITE_DEV_API_KEY || DEFAULT_DEV_KEY;

let cachedKey: string | null = null;

async function getApiKey(): Promise<string> {
  if (cachedKey) return cachedKey;

  try {
    // Try Tauri invoke first (works in desktop app)
    const key = await invoke<string>("get_api_config");
    cachedKey = key;
    return key;
  } catch {
    // Fallback to dev key when running in browser (local development)
    console.warn("Tauri not available, using development API key");
    cachedKey = DEV_API_KEY;
    return DEV_API_KEY;
  }
}

async function authHeaders(extra?: Record<string, string>) {
  const key = await getApiKey();
  return {
    "X-API-Key": key,
    ...extra,
  };
}

export type TranscribeResponse = { text: string; request_id: string };
export type SummarizeResponse = { summary: string };

export interface HardwareInfo {
  hardware_profile: "high_vram" | "low_vram" | "cpu_only";
  recommended_model: string;
  is_downloaded: boolean;
  download_url?: string;
  whisper_downloaded: boolean;
  whisper_size_mb?: number;
}

export async function transcribeAudio(file: File, language?: string): Promise<TranscribeResponse> {
  const key = `transcribe:${file.name}:${file.size}:${file.lastModified}:${language ?? ""}`;
  return deduplicated(key, async () => {
    const form = new FormData();
    form.append("file", file);
    if (language) {
      form.append("language", language);
    }

    const res = await fetchWithRetry(`${BASE_URL}/transcribe`, {
      method: "POST",
      headers: await authHeaders(),
      body: form,
    });

    if (!res.ok) throw new Error(await safeError(res));
    return res.json();
  });
}

export async function summarizeText(text: string): Promise<SummarizeResponse> {
  return deduplicated(`summarize:${text.length}:${text.slice(0, 80)}`, async () => {
    const res = await fetchWithRetry(`${BASE_URL}/summarize`, {
      method: "POST",
      headers: await authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ text }),
    });

    if (!res.ok) throw new Error(await safeError(res));
    return res.json();
  });
}

// ---------------------------------------------------------------------------
// Shared SSE helpers
// ---------------------------------------------------------------------------

/**
 * Read a streaming SSE response body, calling `onData` for each parsed JSON
 * payload.  Returns when a `[DONE]` sentinel is received or the stream ends.
 * Throws on backend-reported errors (`parsed.error`).
 */
async function readSSEStream<T extends { chunk?: string; error?: string }>(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onData: (parsed: T) => boolean, // return true to stop early
): Promise<void> {
  const decoder = new TextDecoder();
  let buffer = "";

  const processLine = (line: string): boolean => {
    if (!line.startsWith("data: ")) return false;
    const data = line.slice(6).trim();
    if (data === "[DONE]") return true; // signal stop
    if (!data) return false;

    let parsed: T;
    try {
      parsed = JSON.parse(data) as T;
    } catch {
      if (data.length > 0) console.warn("Failed to parse SSE data:", data);
      return false;
    }

    if (parsed.error) throw new Error(parsed.error);
    return onData(parsed);
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (processLine(line)) return;
    }
  }

  // Flush any remaining buffered line
  if (buffer.trim()) processLine(buffer.trim());
}

/**
 * Subscribe to a progress SSE endpoint.
 * Returns an abort function to close the connection.
 */
function subscribeProgressSSE<T extends { done?: boolean; error?: string }>(
  endpoint: string,
  onProgress: (p: T) => void,
  onDone: () => void,
  onError: (err: string) => void,
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const headers = await authHeaders();
      const res = await fetch(`${BASE_URL}${endpoint}`, {
        headers,
        signal: controller.signal,
      });
      if (!res.ok) { onError(`SSE connection failed: ${res.status}`); return; }

      const reader = res.body?.getReader();
      if (!reader) { onError("No response body"); return; }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;
          try {
            const data = JSON.parse(raw) as T;
            if (data.error) { onError(data.error); return; }
            onProgress(data);
            if (data.done) { onDone(); return; }
          } catch { /* skip malformed */ }
        }
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        onError(err instanceof Error ? err.message : String(err));
      }
    }
  })();

  return () => controller.abort();
}

/**
 * Stream SmartNote generation using Server-Sent Events (SSE).
 * Provides real-time feedback as tokens are generated.
 *
 * @param text - The transcription text to summarize
 * @param onChunk - Callback called for each token received
 * @param onComplete - Callback called when generation is complete
 * @param onError - Callback called on error
 */
export async function summarizeTextStream(
  text: string,
  onChunk: (chunk: string) => void,
  onComplete: (fullText: string) => void,
  onError?: (error: Error) => void
): Promise<void> {
  const headers = await authHeaders({ "Content-Type": "application/json" });

  try {
    const res = await fetchWithRetry(`${BASE_URL}/summarize-stream`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text }),
    });

    if (!res.ok) throw new Error(await safeError(res));

    const reader = res.body?.getReader();
    if (!reader) throw new Error("No response body");

    let fullText = "";
    await readSSEStream<{ chunk?: string; error?: string }>(reader, (parsed) => {
      if (parsed.chunk) { fullText += parsed.chunk; onChunk(parsed.chunk); }
      return false;
    });
    onComplete(fullText);
  } catch (err) {
    const error = err instanceof Error ? err : new Error(String(err));
    if (onError) onError(error); else throw error;
  }
}

export async function checkModelStatus(): Promise<HardwareInfo> {
  return withCache("checkModelStatus", STATUS_CACHE_TTL, () =>
    deduplicated("checkModelStatus", async () => {
      const headers = await authHeaders();
      const res = await fetchWithRetry(`${BASE_URL}/setup/check-models`, { headers });
      if (!res.ok) throw new Error(await safeError(res));
      return res.json();
    }),
  );
}

export interface DownloadProgress {
  progress: number;
  downloaded_bytes: number;
  total_bytes: number;
  done?: boolean;
  error?: string;
}

/**
 * Subscribe to real-time download progress via SSE.
 * Returns an abort function to close the connection.
 */
export function subscribeDownloadProgress(
  onProgress: (p: DownloadProgress) => void,
  onDone: () => void,
  onError: (err: string) => void,
): () => void {
  return subscribeProgressSSE<DownloadProgress>("/setup/download-progress", onProgress, onDone, onError);
}

export async function downloadModel(): Promise<{ status: string }> {
  return deduplicated("downloadModel", async () => {
    const res = await fetchWithRetry(`${BASE_URL}/setup/download-model`, {
      method: "POST",
      headers: await authHeaders(),
    }, 1);
    if (!res.ok) throw new Error(await safeError(res));
    invalidateCache("checkModelStatus");
    return res.json();
  });
}

export async function downloadWhisper(): Promise<{ status: string }> {
  return deduplicated("downloadWhisper", async () => {
    const res = await fetchWithRetry(`${BASE_URL}/setup/download-whisper`, {
      method: "POST",
      headers: await authHeaders(),
    }, 1);
    if (!res.ok) throw new Error(await safeError(res));
    invalidateCache("checkModelStatus");
    return res.json();
  });
}

export interface WhisperDownloadProgress extends DownloadProgress {
  current_file?: string;
}

/**
 * Subscribe to real-time Whisper download progress via SSE.
 * Returns an abort function to close the connection.
 */
export function subscribeWhisperProgress(
  onProgress: (p: WhisperDownloadProgress) => void,
  onDone: () => void,
  onError: (err: string) => void,
): () => void {
  return subscribeProgressSSE<WhisperDownloadProgress>("/setup/whisper-download-progress", onProgress, onDone, onError);
}

// ---------------------------------------------------------------------------
// RAG & Consultation History API
// ---------------------------------------------------------------------------

export interface RAGStatus {
  available: boolean;
  initialized?: boolean;
  consultations_count: number;
  knowledge_count: number;
  detail?: string;
}

export interface ConsultationResult {
  smartnote: string;
  transcription: string;
  date: string;
  date_display: string;
  dentist_name: string;
  consultation_type: string;
  patient_id: string;
  score: number;
}

export interface SearchResponse {
  results: ConsultationResult[];
  count: number;
  detail?: string;
}

export interface SaveConsultationRequest {
  smartnote: string;
  transcription?: string;
  dentist_name?: string;
  consultation_type?: string;
  patient_id?: string;
}

export async function getRAGStatus(): Promise<RAGStatus> {
  return withCache("ragStatus", STATUS_CACHE_TTL, () =>
    deduplicated("ragStatus", async () => {
      const res = await fetchWithRetry(`${BASE_URL}/rag/status`, {
        headers: await authHeaders(),
      });
      if (!res.ok) throw new Error(await safeError(res));
      return res.json();
    }),
  );
}

export async function saveConsultation(data: SaveConsultationRequest): Promise<{ status: string }> {
  const body = JSON.stringify(data);
  return deduplicated(`saveConsultation:${body.length}:${body.slice(0, 80)}`, async () => {
    const res = await fetchWithRetry(
      `${BASE_URL}/consultations/save`,
      {
        method: "POST",
        headers: await authHeaders({ "Content-Type": "application/json" }),
        body,
      },
      3,     // 3 retries — don't lose the user's work
      1_000, // 1s base delay (1s, 2s, 4s, 8s backoff)
    );
    if (!res.ok) throw new Error(await safeError(res));
    invalidateCache("ragStatus");
    return res.json();
  });
}

export async function searchConsultations(query: string, topK: number = 10): Promise<SearchResponse> {
  return deduplicated(`search:${query}:${topK}`, async () => {
    const res = await fetchWithRetry(`${BASE_URL}/consultations/search`, {
      method: "POST",
      headers: await authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ query, top_k: topK }),
    });
    if (!res.ok) throw new Error(await safeError(res));
    return res.json();
  });
}

export interface ExportResponse {
  consultations: Array<{
    smartnote: string;
    transcription: string;
    date: string;
    date_display: string;
    dentist_name: string;
    consultation_type: string;
    patient_id: string;
  }>;
  count: number;
}

export async function exportConsultations(): Promise<ExportResponse> {
  return deduplicated("exportConsultations", async () => {
    const res = await fetchWithRetry(`${BASE_URL}/consultations/export`, {
      headers: await authHeaders(),
    });
    if (!res.ok) throw new Error(await safeError(res));
    return res.json();
  });
}

/**
 * Stream RAG-enhanced SmartNote generation using SSE.
 * Falls back to standard summarization if RAG is unavailable.
 */
export async function summarizeTextStreamRAG(
  text: string,
  onChunk: (chunk: string) => void,
  onComplete: (fullText: string) => void,
  onRAGStatus?: (ragEnhanced: boolean) => void,
  onError?: (error: Error) => void
): Promise<void> {
  const headers = await authHeaders({ "Content-Type": "application/json" });

  try {
    const res = await fetchWithRetry(`${BASE_URL}/summarize-stream-rag`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text }),
    });

    if (!res.ok) throw new Error(await safeError(res));

    const reader = res.body?.getReader();
    if (!reader) throw new Error("No response body");

    let fullText = "";
    await readSSEStream<{ chunk?: string; error?: string; rag_enhanced?: boolean }>(reader, (parsed) => {
      if (parsed.rag_enhanced !== undefined && onRAGStatus) onRAGStatus(parsed.rag_enhanced);
      else if (parsed.chunk) { fullText += parsed.chunk; onChunk(parsed.chunk); }
      return false;
    });
    onComplete(fullText);
  } catch (err) {
    const error = err instanceof Error ? err : new Error(String(err));
    if (onError) onError(error); else throw error;
  }
}

async function safeError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    return data?.detail ?? res.statusText;
  } catch {
    return res.statusText;
  }
}

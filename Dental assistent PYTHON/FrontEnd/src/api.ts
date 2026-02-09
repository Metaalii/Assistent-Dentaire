import { invoke } from "@tauri-apps/api/core";

// Use environment variable for backend URL, fallback to default
const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:9000";

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
  const form = new FormData();
  form.append("file", file);
  if (language) {
    form.append("language", language);
  }

  const res = await fetch(`${BASE_URL}/transcribe`, {
    method: "POST",
    headers: await authHeaders(),
    body: form,
  });

  if (!res.ok) throw new Error(await safeError(res));
  return res.json();
}

export async function summarizeText(text: string): Promise<SummarizeResponse> {
  const res = await fetch(`${BASE_URL}/summarize`, {
    method: "POST",
    headers: await authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ text }),
  });

  if (!res.ok) throw new Error(await safeError(res));
  return res.json();
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
    const res = await fetch(`${BASE_URL}/summarize-stream`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text }),
    });

    if (!res.ok) {
      throw new Error(await safeError(res));
    }

    const reader = res.body?.getReader();
    if (!reader) {
      throw new Error("No response body");
    }

    const decoder = new TextDecoder();
    let fullText = "";
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE messages
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6).trim();

          if (data === "[DONE]") {
            onComplete(fullText);
            return;
          }

          if (!data) continue; // Skip empty data lines

          try {
            const parsed = JSON.parse(data);
            if (parsed.chunk) {
              fullText += parsed.chunk;
              onChunk(parsed.chunk);
            } else if (parsed.error) {
              throw new Error(parsed.error);
            }
          } catch (parseErr) {
            // Skip invalid JSON lines (could be partial data)
            if (data.length > 0) {
              console.warn("Failed to parse SSE data:", data);
            }
          }
        }
      }
    }

    // Process any remaining data in the buffer before completing
    if (buffer.trim()) {
      const remainingLine = buffer.trim();
      if (remainingLine.startsWith("data: ")) {
        const data = remainingLine.slice(6).trim();
        if (data && data !== "[DONE]") {
          try {
            const parsed = JSON.parse(data);
            if (parsed.chunk) {
              fullText += parsed.chunk;
              onChunk(parsed.chunk);
            }
          } catch {
            // Ignore parse errors for remaining buffer
          }
        }
      }
    }

    // If we exit the loop without [DONE], still complete
    onComplete(fullText);
  } catch (err) {
    const error = err instanceof Error ? err : new Error(String(err));
    if (onError) {
      onError(error);
    } else {
      throw error;
    }
  }
}

export async function checkModelStatus(): Promise<HardwareInfo> {
  // Include auth headers for consistency (endpoint may require auth in future)
  const headers = await authHeaders();
  const res = await fetch(`${BASE_URL}/setup/check-models`, { headers });
  if (!res.ok) throw new Error(await safeError(res));
  return res.json();
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
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${BASE_URL}/setup/download-progress`, {
        signal: controller.signal,
      });
      if (!res.ok) {
        onError(`SSE connection failed: ${res.status}`);
        return;
      }
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
            const data: DownloadProgress = JSON.parse(raw);
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

export async function downloadModel(): Promise<{ status: string }> {
  const res = await fetch(`${BASE_URL}/setup/download-model`, {
    method: "POST",
    headers: await authHeaders(),
  });

  if (!res.ok) throw new Error(await safeError(res));
  return res.json();
}

export async function downloadWhisper(): Promise<{ status: string }> {
  const res = await fetch(`${BASE_URL}/setup/download-whisper`, {
    method: "POST",
    headers: await authHeaders(),
  });

  if (!res.ok) throw new Error(await safeError(res));
  return res.json();
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
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${BASE_URL}/setup/whisper-download-progress`, {
        signal: controller.signal,
      });
      if (!res.ok) {
        onError(`SSE connection failed: ${res.status}`);
        return;
      }
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
            const data: WhisperDownloadProgress = JSON.parse(raw);
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

async function safeError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    return data?.detail ?? res.statusText;
  } catch {
    return res.statusText;
  }
}

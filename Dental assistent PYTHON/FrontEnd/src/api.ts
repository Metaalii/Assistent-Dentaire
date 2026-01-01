import { invoke } from "@tauri-apps/api/core";

const BASE_URL = "http://127.0.0.1:9000";

let cachedKey: string | null = null;

async function getApiKey(): Promise<string> {
  if (cachedKey) return cachedKey;
  cachedKey = await invoke<string>("get_api_config");
  return cachedKey!;
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
}

export async function transcribeAudio(file: File): Promise<TranscribeResponse> {
  const form = new FormData();
  form.append("file", file);

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

export async function checkModelStatus(): Promise<HardwareInfo> {
  const res = await fetch(`${BASE_URL}/setup/check-models`);
  if (!res.ok) throw new Error(await safeError(res));
  return res.json();
}

export async function downloadModel(): Promise<{ status: string }> {
  const res = await fetch(`${BASE_URL}/setup/download-model`, {
    method: "POST",
    headers: await authHeaders(),
  });

  if (!res.ok) throw new Error(await safeError(res));
  return res.json();
}

async function safeError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    return data?.detail ?? res.statusText;
  } catch {
    return res.statusText;
  }
}

import React, { useEffect, useRef, useState } from "react";
import { checkModelStatus, downloadModel, HardwareInfo } from "../api";

interface Props {
  onReady: () => void;
}

export default function ModelSetup({ onReady }: Props) {
  const [step, setStep] = useState<"checking" | "confirm" | "downloading" | "error">("checking");
  const [hardware, setHardware] = useState<HardwareInfo | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [progress, setProgress] = useState(0);

  const progressTimer = useRef<number | null>(null);
  const statusTimer = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const status = await checkModelStatus();
        if (cancelled) return;

        setHardware(status);
        if (status.is_downloaded) onReady();
        else setStep("confirm");
      } catch {
        if (!cancelled) {
          setStep("error");
          setErrorMsg("Could not connect to the Local AI Engine. Is the backend running?");
        }
      }
    })();

    return () => {
      cancelled = true;
      if (progressTimer.current) window.clearInterval(progressTimer.current);
      if (statusTimer.current) window.clearInterval(statusTimer.current);
    };
  }, [onReady]);

  const refreshStatus = async () => {
    try {
      const status = await checkModelStatus();
      setHardware(status);
      if (status.is_downloaded) {
        setProgress(100);
        setStep("confirm");
        setTimeout(onReady, 300);
      }
    } catch (e) {
      setStep("error");
      setErrorMsg(e instanceof Error ? e.message : "Could not connect to the backend.");
    }
  };

  const startPolling = () => {
    progressTimer.current = window.setInterval(() => {
      setProgress((old) => (old < 90 ? old + 1 : old));
    }, 500);

    statusTimer.current = window.setInterval(async () => {
      try {
        const status = await checkModelStatus();
        if (status.is_downloaded) {
          if (progressTimer.current) window.clearInterval(progressTimer.current);
          if (statusTimer.current) window.clearInterval(statusTimer.current);
          setProgress(100);
          setTimeout(onReady, 500);
        }
      } catch {
        // ignore transient errors
      }
    }, 3000);
  };

  const handleDownload = async () => {
    try {
      setStep("downloading");
      await downloadModel();
      startPolling();
    } catch {
      setStep("error");
      setErrorMsg("Failed to start download.");
    }
  };

  const renderBody = () => {
    if (step === "checking") {
      return (
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <div className="text-slate-700">Checking your environment and models…</div>
        </div>
      );
    }

    if (step === "error") {
      return (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 shadow-sm">
          <div className="text-red-700 font-semibold">Something went wrong</div>
          <p className="mt-2 text-red-600 text-sm">{errorMsg || "Unexpected error"}</p>
          <div className="mt-4 flex gap-3">
            <button
              className="rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700"
              onClick={() => refreshStatus()}
            >
              Retry
            </button>
            <button
              className="rounded border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50"
              onClick={() => window.location.reload()}
            >
              Restart App
            </button>
          </div>
        </div>
      );
    }

    if (step === "downloading") {
      return (
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="h-3 w-3 animate-pulse rounded-full bg-blue-500" aria-hidden />
            <div className="text-slate-800 font-semibold">Downloading model…</div>
          </div>
          {hardware && (
            <p className="mt-2 text-sm text-slate-600">
              Target: {hardware.recommended_model} ({hardware.hardware_profile})
            </p>
          )}
          <div className="mt-4 h-3 w-full rounded-full bg-slate-100">
            <div
              className="h-3 rounded-full bg-blue-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-slate-500">You can keep this window open; it will continue automatically.</p>
        </div>
      );
    }

    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Download local models</h2>
        <p className="mt-2 text-sm text-slate-600">
          We need to store the LLM and Whisper models locally to run transcription and summarization on your machine.
        </p>

        {hardware && (
          <div className="mt-3 rounded border border-slate-100 bg-slate-50 p-3 text-sm text-slate-700">
            <div className="font-semibold text-slate-800">Detected profile: {hardware.hardware_profile}</div>
            <div className="mt-1">Recommended model: {hardware.recommended_model}</div>
            {hardware.download_url && (
              <div className="mt-1">
                Source: <a className="text-blue-600 underline" href={hardware.download_url} target="_blank" rel="noreferrer">{hardware.download_url}</a>
              </div>
            )}
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-3">
          <button
            className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
            onClick={handleDownload}
          >
            Download and continue
          </button>
          <button
            className="rounded border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50"
            onClick={() => refreshStatus()}
          >
            Re-check status
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
      <div className="w-full max-w-xl space-y-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dental Assistant — Setup</h1>
          <p className="text-sm text-slate-600">Download local models once, then you can use the app offline.</p>
        </div>
        {renderBody()}
      </div>
    </div>
  );
}

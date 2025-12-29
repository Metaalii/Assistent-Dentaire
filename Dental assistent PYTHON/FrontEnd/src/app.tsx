import React, { useEffect, useState } from "react";
import ModelSetup from "./components/ModelSetup";
import MainDashboard from "./components/MainDashboard";

type BootState =
  | { state: "starting" }
  | { state: "setup" }
  | { state: "ready" }
  | { state: "error"; message: string };

async function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

async function waitForHealth(timeoutMs = 10_000): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch("http://127.0.0.1:9000/health");
      if (res.ok) return;
    } catch {
      // ignore
    }
    await sleep(250);
  }
  throw new Error("Backend did not become ready");
}

export default function App() {
  const [boot, setBoot] = useState<BootState>({ state: "starting" });

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        await waitForHealth(12_000);
        if (!cancelled) setBoot({ state: "setup" });
      } catch (e) {
        if (!cancelled)
          setBoot({
            state: "error",
            message: e instanceof Error ? e.message : "Startup failed",
          });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  if (boot.state === "starting") {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="text-slate-700 font-medium">Starting backend…</div>
      </div>
    );
  }

  if (boot.state === "error") {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-red-50 p-8 text-center">
        <h2 className="text-xl font-bold text-red-700">Startup Failed</h2>
        <p className="mt-2 text-red-600">{boot.message}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-6 rounded bg-red-600 px-6 py-2 text-white hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (boot.state === "setup") {
    return <ModelSetup onReady={() => setBoot({ state: "ready" })} />;
  }

  return (
    <div className="app-container">
      <MainDashboard />
    </div>
  );
}

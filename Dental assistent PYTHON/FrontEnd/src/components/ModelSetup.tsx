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

  // keep your existing JSX below (mostly fine)
  // ...
}

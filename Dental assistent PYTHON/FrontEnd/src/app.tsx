import React, { useEffect, useState } from "react";
import ModelSetup from "./components/ModelSetup";
import MainDashboard from "./components/MainDashboard";
import LanguageSelector from "./components/LanguageSelector";
import { LanguageProvider, useLanguage } from "./i18n";
import { ToothIcon, HeartPulseIcon, AlertCircleIcon, RefreshIcon } from "./components/ui/Icons";
import { Button, MedicalLoader } from "./components/ui";

type BootState =
  | { state: "language" }
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

// ============================================
// SPLASH SCREEN COMPONENT
// ============================================
const SplashScreen: React.FC = () => {
  const { t } = useLanguage();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#f8fafc] via-[#e6f4f9] to-[#e0f7f6] relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-[#35a7d3]/20 to-[#00bdb8]/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-tr from-[#00bdb8]/20 to-[#35a7d3]/20 rounded-full blur-3xl animate-pulse delay-1000" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-r from-[#35a7d3]/5 to-[#00bdb8]/5 rounded-full blur-3xl" />
      </div>

      {/* Main content */}
      <div className="relative z-10 flex flex-col items-center gap-8 p-8">
        {/* Logo container */}
        <div className="relative">
          {/* Glowing ring */}
          <div className="absolute inset-0 w-32 h-32 rounded-full bg-gradient-to-r from-[#35a7d3] to-[#00bdb8] blur-xl opacity-30 animate-pulse" />

          {/* Logo background */}
          <div className="relative w-32 h-32 rounded-3xl bg-gradient-to-br from-[#35a7d3] to-[#00bdb8] shadow-2xl shadow-[#35a7d3]/30 flex items-center justify-center transform hover:scale-105 transition-transform duration-300">
            <ToothIcon className="text-white" size={64} />
          </div>

          {/* Heartbeat indicator */}
          <div className="absolute -bottom-2 -right-2 w-10 h-10 rounded-full bg-white shadow-lg flex items-center justify-center">
            <HeartPulseIcon className="text-[#00bdb8] animate-pulse" size={20} />
          </div>
        </div>

        {/* Title */}
        <div className="text-center">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-[#1e293b] via-[#334155] to-[#1e293b] bg-clip-text text-transparent">
            {t("appName")}
          </h1>
          <p className="mt-2 text-[#64748b] font-medium">
            {t("appTagline")}
          </p>
        </div>

        {/* Loading indicator */}
        <div className="flex flex-col items-center gap-4">
          <MedicalLoader text={t("initializing") as string} />
        </div>

        {/* Version badge */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2">
          <div className="px-4 py-2 rounded-full bg-white/80 backdrop-blur-sm border border-[#e2e8f0] shadow-sm">
            <span className="text-sm text-[#64748b] font-medium">{t("version")}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================
// ERROR SCREEN COMPONENT
// ============================================
interface ErrorScreenProps {
  message: string;
  onRetry: () => void;
}

const ErrorScreen: React.FC<ErrorScreenProps> = ({ message, onRetry }) => {
  const { t } = useLanguage();
  const tips = t("troubleshootingTips") as string[];

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#fef2f2] via-[#fee2e2] to-[#fecaca] relative overflow-hidden">
      {/* Background pattern */}
      <div className="absolute inset-0">
        <div className="absolute top-20 right-20 w-64 h-64 bg-red-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-20 left-20 w-64 h-64 bg-red-400/10 rounded-full blur-3xl" />
      </div>

      {/* Main content */}
      <div className="relative z-10 max-w-md w-full mx-4">
        <div className="bg-white/90 backdrop-blur-xl rounded-3xl shadow-2xl shadow-red-500/10 border border-red-100 p-8 text-center">
          {/* Error icon */}
          <div className="mx-auto w-20 h-20 rounded-2xl bg-gradient-to-br from-red-500 to-red-600 shadow-lg shadow-red-500/30 flex items-center justify-center mb-6">
            <AlertCircleIcon className="text-white" size={40} />
          </div>

          {/* Error title */}
          <h2 className="text-2xl font-bold text-[#1e293b] mb-3">
            {t("connectionFailed")}
          </h2>

          {/* Error message */}
          <p className="text-[#64748b] mb-6 leading-relaxed">
            {message}
          </p>

          {/* Troubleshooting tips */}
          <div className="bg-red-50 rounded-xl p-4 mb-6 text-left">
            <p className="text-sm font-semibold text-red-800 mb-2">{t("troubleshooting")}</p>
            <ul className="text-sm text-red-700 space-y-1">
              {tips.map((tip, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="text-red-400 mt-0.5">&bull;</span>
                  {tip}
                </li>
              ))}
            </ul>
          </div>

          {/* Retry button */}
          <Button
            variant="danger"
            onClick={onRetry}
            leftIcon={<RefreshIcon size={18} />}
            className="w-full"
          >
            {t("tryAgain")}
          </Button>
        </div>
      </div>
    </div>
  );
};

// ============================================
// APP CONTENT (inside LanguageProvider)
// ============================================
const SESSION_LANGUAGE_SELECTED_KEY = "dental-assistant-language-selected";

function hasSeenLanguageSelector() {
  if (typeof window === "undefined") return false;
  return sessionStorage.getItem(SESSION_LANGUAGE_SELECTED_KEY) === "true";
}

function rememberLanguageSelectorSeen() {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(SESSION_LANGUAGE_SELECTED_KEY, "true");
}

function AppContent() {
  const [boot, setBoot] = useState<BootState>(() => {
    // Show the language selector once per browsing session
    return hasSeenLanguageSelector() ? { state: "starting" } : { state: "language" };
  });

  useEffect(() => {
    if (boot.state !== "starting") return;

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
  }, [boot.state]);

  const handleLanguageSelected = () => {
    rememberLanguageSelectorSeen();
    setBoot({ state: "starting" });
  };

  if (boot.state === "language") {
    return <LanguageSelector onComplete={handleLanguageSelected} />;
  }

  if (boot.state === "starting") {
    return <SplashScreen />;
  }

  if (boot.state === "error") {
    return (
      <ErrorScreen
        message={boot.message}
        onRetry={() => window.location.reload()}
      />
    );
  }

  if (boot.state === "setup") {
    return <ModelSetup onReady={() => setBoot({ state: "ready" })} />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f8fafc] via-[#e6f4f9] to-[#f8fafc]">
      <MainDashboard />
    </div>
  );
}

// ============================================
// MAIN APP COMPONENT
// ============================================
export default function App() {
  return (
    <LanguageProvider>
      <AppContent />
    </LanguageProvider>
  );
}

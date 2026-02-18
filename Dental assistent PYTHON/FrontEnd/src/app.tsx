import React, { useEffect, useState } from "react";
import ModelSetup from "./components/ModelSetup";
import MainDashboard from "./components/MainDashboard";
import LanguageSelector from "./components/LanguageSelector";
import ProfileSetup from "./components/ProfileSetup";
import ErrorBoundary from "./components/ErrorBoundary";
import { LanguageProvider, useLanguage, ThemeProvider } from "./i18n";
import { ToothIcon, HeartPulseIcon, AlertCircleIcon, RefreshIcon } from "./components/ui/Icons";
import { Button, MedicalLoader } from "./components/ui";
import { DentistProfile } from "./hooks/useProfile";

type BootState =
  | { state: "language" }
  | { state: "profile" }
  | { state: "starting" }
  | { state: "setup" }
  | { state: "ready" }
  | { state: "error"; message: string };

async function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:9000";

async function waitForHealth(timeoutMs = 10_000): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${API_URL}/health`);
      if (res.ok) return;
    } catch {
      // ignore transient network errors during startup
    }
    await sleep(250);
  }
  throw new Error("[SYSTEM_001] Backend did not become ready. Is the server running on " + API_URL + "?");
}

// ============================================
// SPLASH SCREEN COMPONENT
// ============================================
const SplashScreen: React.FC = () => {
  const { t } = useLanguage();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#f8fafc] via-[#f0f7fc] to-[#effcfb] dark:from-[#0f172a] dark:via-[#1e293b] dark:to-[#0f172a] relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-[#2d96c6]/20 to-[#28b5ad]/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-tr from-[#28b5ad]/20 to-[#2d96c6]/20 rounded-full blur-3xl animate-pulse delay-1000" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-r from-[#2d96c6]/5 to-[#28b5ad]/5 rounded-full blur-3xl" />
      </div>

      {/* Main content */}
      <div className="relative z-10 flex flex-col items-center gap-8 p-8">
        {/* Logo container */}
        <div className="relative">
          {/* Glowing ring */}
          <div className="absolute inset-0 w-32 h-32 rounded-full bg-gradient-to-r from-[#2d96c6] to-[#28b5ad] blur-xl opacity-30 animate-pulse" />

          {/* Logo background */}
          <div className="relative w-32 h-32 rounded-3xl bg-gradient-to-br from-[#2d96c6] to-[#28b5ad] shadow-2xl shadow-[#2d96c6]/30 flex items-center justify-center transform hover:scale-105 transition-transform duration-300">
            <ToothIcon className="text-white" size={64} />
          </div>

          {/* Heartbeat indicator */}
          <div className="absolute -bottom-2 -right-2 w-10 h-10 rounded-full bg-white dark:bg-[#1e293b] shadow-lg flex items-center justify-center">
            <HeartPulseIcon className="text-[#28b5ad] animate-pulse" size={20} />
          </div>
        </div>

        {/* Title */}
        <div className="text-center">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-[#1e293b] via-[#334155] to-[#1e293b] dark:from-white dark:via-[#94a3b8] dark:to-white bg-clip-text text-transparent">
            {t("appName")}
          </h1>
          <p className="mt-2 text-[#64748b] dark:text-[#94a3b8] font-medium">
            {t("appTagline")}
          </p>
        </div>

        {/* Loading indicator */}
        <div className="flex flex-col items-center gap-4">
          <MedicalLoader text={String(t("initializing") || "Initializing...")} />
        </div>

        {/* Version badge */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2">
          <div className="px-4 py-2 rounded-full bg-white/80 dark:bg-[#1e293b]/80 backdrop-blur-sm border border-[#e2e8f0] dark:border-[#334155] shadow-sm">
            <span className="text-sm text-[#64748b] dark:text-[#94a3b8] font-medium">{t("version")}</span>
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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#fef2f2] via-[#fee2e2] to-[#fecaca] dark:from-[#1a0a0a] dark:via-[#1e1010] dark:to-[#1a0a0a] relative overflow-hidden">
      {/* Background pattern */}
      <div className="absolute inset-0">
        <div className="absolute top-20 right-20 w-64 h-64 bg-red-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-20 left-20 w-64 h-64 bg-red-400/10 rounded-full blur-3xl" />
      </div>

      {/* Main content */}
      <div className="relative z-10 max-w-md w-full mx-4">
        <div className="bg-white/90 dark:bg-[#1e293b]/90 backdrop-blur-xl rounded-3xl shadow-2xl shadow-red-500/10 border border-red-100 dark:border-red-900/50 p-8 text-center">
          {/* Error icon */}
          <div className="mx-auto w-20 h-20 rounded-2xl bg-gradient-to-br from-red-500 to-red-600 shadow-lg shadow-red-500/30 flex items-center justify-center mb-6">
            <AlertCircleIcon className="text-white" size={40} />
          </div>

          {/* Error title */}
          <h2 className="text-2xl font-bold text-[#1e293b] dark:text-white mb-3">
            {t("connectionFailed")}
          </h2>

          {/* Error message */}
          <p className="text-[#64748b] dark:text-[#94a3b8] mb-6 leading-relaxed">
            {message}
          </p>

          {/* Troubleshooting tips */}
          <div className="bg-red-50 dark:bg-red-950/50 rounded-xl p-4 mb-6 text-left">
            <p className="text-sm font-semibold text-red-800 dark:text-red-300 mb-2">{t("troubleshooting")}</p>
            <ul className="text-sm text-red-700 dark:text-red-400 space-y-1">
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
const LANGUAGE_SELECTED_KEY = "dental-assistant-language-selected";
const PROFILE_KEY = "dental-assistant-profile";

function AppContent() {
  const [boot, setBoot] = useState<BootState>(() => {
    // Check if language was already selected
    const languageSelected = localStorage.getItem(LANGUAGE_SELECTED_KEY);
    if (!languageSelected) {
      return { state: "language" };
    }
    // Check if profile was already set up
    const profileSet = localStorage.getItem(PROFILE_KEY);
    if (!profileSet) {
      return { state: "profile" };
    }
    return { state: "starting" };
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
    localStorage.setItem(LANGUAGE_SELECTED_KEY, "true");
    // After language, go to profile setup
    setBoot({ state: "profile" });
  };

  const handleProfileComplete = (profile: DentistProfile) => {
    localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
    setBoot({ state: "starting" });
  };

  if (boot.state === "language") {
    return <LanguageSelector onComplete={handleLanguageSelected} />;
  }

  if (boot.state === "profile") {
    return <ProfileSetup onComplete={handleProfileComplete} />;
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
    return (
      <ErrorBoundary>
        <ModelSetup onReady={() => setBoot({ state: "ready" })} />
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gradient-to-br from-[#f8fafc] via-[#f0f7fc] to-[#f8fafc] dark:from-[#0f172a] dark:via-[#1e293b] dark:to-[#0f172a]">
        <MainDashboard />
      </div>
    </ErrorBoundary>
  );
}

// ============================================
// MAIN APP COMPONENT
// ============================================
export default function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AppContent />
      </LanguageProvider>
    </ThemeProvider>
  );
}

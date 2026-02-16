import React, { useEffect, useRef, useState } from "react";
import {
  checkModelStatus,
  downloadModel,
  downloadWhisper,
  subscribeDownloadProgress,
  subscribeWhisperProgress,
  HardwareInfo,
} from "../api";
import { AppError, getErrorGuidance } from "../errors";
import { useLanguage } from "../i18n";
import {
  Button,
  Card,
  CardBody,
  ProgressBar,
  Alert,
  Badge,
  MedicalLoader,
} from "./ui";
import {
  ToothIcon,
  DownloadIcon,
  CpuIcon,
  CheckCircleIcon,
  AlertCircleIcon,
  RefreshIcon,
  SettingsIcon,
} from "./ui/Icons";

interface Props {
  onReady: () => void;
}

// ============================================
// STEP INDICATOR COMPONENT
// ============================================
interface StepIndicatorProps {
  currentStep: number;
  steps: string[];
}

const StepIndicator: React.FC<StepIndicatorProps> = ({ currentStep, steps }) => (
  <div className="flex items-center justify-center gap-2 mb-8">
    {steps.map((step, index) => (
      <React.Fragment key={step}>
        <div className="flex items-center gap-2">
          <div
            className={`
              w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold
              transition-all duration-300
              ${
                index < currentStep
                  ? "bg-gradient-to-br from-[#10b981] to-[#059669] text-white shadow-lg shadow-green-500/30"
                  : index === currentStep
                  ? "bg-gradient-to-br from-[#2d96c6] to-[#28b5ad] text-white shadow-lg shadow-[#2d96c6]/30"
                  : "bg-[#e2e8f0] dark:bg-[#334155] text-[#94a3b8]"
              }
            `}
          >
            {index < currentStep ? (
              <CheckCircleIcon size={16} />
            ) : (
              index + 1
            )}
          </div>
          <span
            className={`
              text-sm font-medium hidden sm:block
              ${
                index <= currentStep
                  ? "text-[#1e293b] dark:text-white"
                  : "text-[#94a3b8]"
              }
            `}
          >
            {step}
          </span>
        </div>
        {index < steps.length - 1 && (
          <div
            className={`
              w-8 h-0.5 rounded-full transition-all duration-300
              ${index < currentStep ? "bg-[#10b981]" : "bg-[#e2e8f0] dark:bg-[#334155]"}
            `}
          />
        )}
      </React.Fragment>
    ))}
  </div>
);

// ============================================
// HARDWARE INFO CARD COMPONENT
// ============================================
interface HardwareInfoCardProps {
  hardware: HardwareInfo;
}

const HardwareInfoCard: React.FC<HardwareInfoCardProps> = ({ hardware }) => {
  const { t } = useLanguage();

  const profileLabels: Record<string, { label: string; variant: "success" | "warning" | "primary" }> = {
    high_vram: { label: t("highVram") as string, variant: "success" },
    low_vram: { label: t("lowVram") as string, variant: "primary" },
    cpu_only: { label: t("cpuOnly") as string, variant: "warning" },
  };

  const profile = profileLabels[hardware.hardware_profile] || {
    label: hardware.hardware_profile,
    variant: "primary" as const,
  };

  return (
    <div className="bg-gradient-to-br from-[#f8fafc] to-[#f0f7fc] dark:from-[#0f172a] dark:to-[#1e293b] rounded-2xl p-5 border border-[#e2e8f0] dark:border-[#334155]">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#2d96c6] to-[#28b5ad] shadow-lg shadow-[#2d96c6]/20 flex items-center justify-center flex-shrink-0">
          <CpuIcon className="text-white" size={24} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-[#1e293b] dark:text-white">{t("hardwareProfile")}</h3>
            <Badge variant={profile.variant}>{profile.label}</Badge>
          </div>
          <p className="mt-2 text-sm text-[#64748b] dark:text-[#94a3b8]">
            {t("recommendedModel")}:{" "}
            <span className="font-medium text-[#334155] dark:text-[#e2e8f0]">
              {hardware.recommended_model}
            </span>
          </p>
          {hardware.download_url && (
            <p className="mt-1 text-xs text-[#94a3b8] dark:text-[#64748b] truncate">
              Source: {hardware.download_url}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================
// MAIN MODEL SETUP COMPONENT
// ============================================
export default function ModelSetup({ onReady }: Props) {
  const { t } = useLanguage();
  const [step, setStep] = useState<"checking" | "confirm" | "downloading" | "error">("checking");
  const [hardware, setHardware] = useState<HardwareInfo | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [errorCode, setErrorCode] = useState<string | undefined>();
  const [errorHint, setErrorHint] = useState<string | undefined>();
  const [progress, setProgress] = useState(0);
  const [downloadedMB, setDownloadedMB] = useState(0);
  const [totalMB, setTotalMB] = useState(0);
  // Track which model is currently downloading
  const [downloadPhase, setDownloadPhase] = useState<"whisper" | "llm">("whisper");

  // Ref to abort SSE stream on unmount
  const abortSSE = useRef<(() => void) | null>(null);
  // Fallback polling ref (only used if SSE fails)
  const fallbackTimer = useRef<number | null>(null);

  const lang = (t("lang") as string) || "fr";
  const steps = [t("stepHardware") as string, t("stepDownload") as string, t("stepReady") as string];
  const currentStepIndex = step === "checking" ? 0 : step === "confirm" ? 0 : step === "downloading" ? 1 : 0;

  /** Set structured error state from any caught value. */
  const showError = (e: unknown, fallbackMsg?: string) => {
    setStep("error");
    if (e instanceof AppError) {
      const guidance = getErrorGuidance(e.code, lang);
      setErrorCode(e.code);
      setErrorMsg(guidance.title);
      setErrorHint(guidance.hint);
    } else if (e instanceof Error) {
      setErrorCode(undefined);
      setErrorMsg(e.message);
      setErrorHint(undefined);
    } else {
      setErrorCode(undefined);
      setErrorMsg(fallbackMsg || String(e));
      setErrorHint(undefined);
    }
  };

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const status = await checkModelStatus();
        if (cancelled) return;

        setHardware(status);
        if (status.is_downloaded && status.whisper_downloaded) {
          onReady();
        } else {
          setStep("confirm");
        }
      } catch (e) {
        if (!cancelled) {
          showError(e, "Could not connect to the Local AI Engine. Is the backend running?");
        }
      }
    })();

    return () => {
      cancelled = true;
      if (abortSSE.current) abortSSE.current();
      if (fallbackTimer.current) window.clearInterval(fallbackTimer.current);
    };
  }, [onReady]);

  const refreshStatus = async () => {
    try {
      const status = await checkModelStatus();
      setHardware(status);
      if (status.is_downloaded && status.whisper_downloaded) {
        setProgress(100);
        setStep("confirm");
        setTimeout(onReady, 300);
      }
    } catch (e) {
      showError(e, "Could not connect to the backend.");
    }
  };

  /** Fallback: poll every 5 s if SSE connection fails */
  const startFallbackPolling = () => {
    fallbackTimer.current = window.setInterval(async () => {
      try {
        const status = await checkModelStatus();
        if (status.is_downloaded && status.whisper_downloaded) {
          if (fallbackTimer.current) window.clearInterval(fallbackTimer.current);
          setProgress(100);
          setTimeout(onReady, 500);
        }
      } catch {
        // ignore transient errors
      }
    }, 5000);
  };

  /** Start LLM download with SSE progress */
  const startLLMDownload = async () => {
    setDownloadPhase("llm");
    setProgress(0);
    setDownloadedMB(0);
    setTotalMB(0);

    try {
      const res = await downloadModel();
      if (res.status === "already_exists") {
        setProgress(100);
        setTimeout(onReady, 500);
        return;
      }
    } catch (e) {
      showError(e, "Failed to start LLM download.");
      return;
    }

    abortSSE.current = subscribeDownloadProgress(
      (p) => {
        setProgress(Math.round(p.progress));
        setDownloadedMB(Math.round(p.downloaded_bytes / (1024 * 1024)));
        setTotalMB(Math.round(p.total_bytes / (1024 * 1024)));
      },
      () => {
        setProgress(100);
        setTimeout(onReady, 500);
      },
      (errMsg, errCode) => {
        if (errCode) {
          const guidance = getErrorGuidance(errCode, lang);
          setErrorCode(errCode);
          setErrorMsg(guidance.title);
          setErrorHint(guidance.hint);
          setStep("error");
        } else {
          startFallbackPolling();
        }
      },
    );
  };

  const handleDownload = async () => {
    try {
      setStep("downloading");

      // Phase 1: Download Whisper if needed
      const needsWhisper = hardware && !hardware.whisper_downloaded;
      const needsLLM = hardware && !hardware.is_downloaded;

      if (needsWhisper) {
        setDownloadPhase("whisper");
        setProgress(0);
        setDownloadedMB(0);
        setTotalMB(0);

        const whisperRes = await downloadWhisper();
        if (whisperRes.status === "already_exists") {
          // Skip to LLM
          if (needsLLM) {
            await startLLMDownload();
          } else {
            setTimeout(onReady, 500);
          }
          return;
        }

        // Subscribe to Whisper progress, then chain to LLM when done
        abortSSE.current = subscribeWhisperProgress(
          (p) => {
            setProgress(Math.round(p.progress));
            setDownloadedMB(Math.round(p.downloaded_bytes / (1024 * 1024)));
            setTotalMB(Math.round(p.total_bytes / (1024 * 1024)));
          },
          () => {
            // Whisper done -> start LLM if needed
            if (needsLLM) {
              startLLMDownload();
            } else {
              setProgress(100);
              setTimeout(onReady, 500);
            }
          },
          (errMsg, errCode) => {
            if (errCode) {
              const guidance = getErrorGuidance(errCode, lang);
              setErrorCode(errCode);
              setErrorMsg(guidance.title);
              setErrorHint(guidance.hint);
              setStep("error");
            } else {
              startFallbackPolling();
            }
          },
        );
      } else if (needsLLM) {
        // Only LLM needed
        await startLLMDownload();
      } else {
        // Both already present
        setTimeout(onReady, 500);
      }
    } catch (e) {
      showError(e, "Failed to start download.");
    }
  };

  // ============================================
  // RENDER: CHECKING STATE
  // ============================================
  const renderChecking = () => (
    <Card glass className="text-center">
      <CardBody className="py-12">
        <MedicalLoader text={t("analyzingHardware") as string} />
        <p className="mt-6 text-sm text-[#94a3b8] dark:text-[#64748b]">
          {t("systemRequirements")}
        </p>
      </CardBody>
    </Card>
  );

  // ============================================
  // RENDER: ERROR STATE
  // ============================================
  const renderError = () => (
    <Card className="overflow-hidden">
      <div className="bg-gradient-to-r from-red-500 to-red-600 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center">
            <AlertCircleIcon className="text-white" size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-white">{t("processingError")}</h3>
            {errorCode && (
              <p className="text-sm text-red-200 font-mono">{errorCode}</p>
            )}
          </div>
        </div>
      </div>
      <CardBody>
        <Alert variant="error" icon={<AlertCircleIcon size={18} />}>
          <div>
            <p className="font-semibold">{errorMsg || t("errorOccurred")}</p>
            {errorHint && (
              <p className="mt-1 text-sm opacity-90">{errorHint}</p>
            )}
          </div>
        </Alert>
        <div className="mt-6 flex flex-col sm:flex-row gap-3">
          <Button
            variant="danger"
            onClick={refreshStatus}
            leftIcon={<RefreshIcon size={18} />}
            className="flex-1"
          >
            {t("tryAgain")}
          </Button>
          <Button
            variant="ghost"
            onClick={() => window.location.reload()}
            className="flex-1"
          >
            {t("tryAgain")}
          </Button>
        </div>
      </CardBody>
    </Card>
  );

  // ============================================
  // RENDER: DOWNLOADING STATE
  // ============================================
  const renderDownloading = () => (
    <Card className="overflow-hidden">
      <div className="bg-gradient-to-r from-[#2d96c6] to-[#28b5ad] px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center">
            <DownloadIcon className="text-white animate-bounce" size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-white">{t("downloadingModel")}</h3>
            <p className="text-sm text-white/80">{t("downloadProgress")}</p>
          </div>
        </div>
      </div>
      <CardBody className="space-y-6">
        {/* Phase indicator */}
        <div className="flex items-center gap-2">
          <span
            className={`text-xs font-semibold px-2 py-1 rounded-full ${
              downloadPhase === "whisper"
                ? "bg-[#f0f7fc] dark:bg-[#1e3a5f] text-[#2d96c6] dark:text-[#52b1db]"
                : "bg-[#f0fdf4] dark:bg-[#14332a] text-[#10b981] dark:text-[#6ee7b7]"
            }`}
          >
            {downloadPhase === "whisper" ? "1/2 — Whisper (speech)" : "2/2 — LLM (AI)"}
          </span>
        </div>

        {/* Progress section */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-[#334155] dark:text-[#e2e8f0]">
              {downloadPhase === "whisper" ? "Whisper model" : t("downloading")}
            </span>
            <span className="text-sm font-bold text-[#2d96c6]">{progress}%</span>
          </div>
          <ProgressBar value={progress} size="lg" />
        </div>

        {/* Hardware info */}
        {hardware && <HardwareInfoCard hardware={hardware} />}

        {/* Info message */}
        <Alert variant="info">
          <p className="text-sm">
            {t("downloadProgress")}
          </p>
        </Alert>

        {/* Download stats */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-[#f8fafc] dark:bg-[#0f172a] rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-[#2d96c6]">
              {totalMB > 0
                ? `${downloadedMB} / ${totalMB} MB`
                : downloadPhase === "whisper" ? "~464 MB" : "~4 GB"}
            </p>
            <p className="text-xs text-[#94a3b8] mt-1">{t("downloadSize")}</p>
          </div>
          <div className="bg-[#f8fafc] dark:bg-[#0f172a] rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-[#28b5ad]">{progress}%</p>
            <p className="text-xs text-[#94a3b8] mt-1">{t("optimal")}</p>
          </div>
        </div>
      </CardBody>
    </Card>
  );

  // ============================================
  // RENDER: CONFIRM STATE
  // ============================================
  const renderConfirm = () => (
    <Card className="overflow-hidden">
      <div className="bg-gradient-to-r from-[#2d96c6] to-[#28b5ad] px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center">
            <SettingsIcon className="text-white" size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-white">{t("setupTitle")}</h3>
            <p className="text-sm text-white/80">{t("setupSubtitle")}</p>
          </div>
        </div>
      </div>
      <CardBody className="space-y-6">
        {/* Hardware info */}
        {hardware && <HardwareInfoCard hardware={hardware} />}

        {/* Features */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-[#f0fdf4] dark:bg-[#14332a] rounded-xl p-4 text-center border border-[#bbf7d0] dark:border-[#276749]">
            <div className="w-10 h-10 mx-auto rounded-xl bg-gradient-to-br from-[#10b981] to-[#059669] flex items-center justify-center mb-3">
              <CheckCircleIcon className="text-white" size={20} />
            </div>
            <p className="text-sm font-semibold text-[#166534] dark:text-[#6ee7b7]">100% Private</p>
          </div>
          <div className="bg-[#f0f7fc] dark:bg-[#1e3a5f] rounded-xl p-4 text-center border border-[#bde0f3] dark:border-[#2d6a8e]">
            <div className="w-10 h-10 mx-auto rounded-xl bg-gradient-to-br from-[#2d96c6] to-[#1e7aa8] flex items-center justify-center mb-3">
              <CpuIcon className="text-white" size={20} />
            </div>
            <p className="text-sm font-semibold text-[#1a5271] dark:text-[#8acae9]">Offline Ready</p>
          </div>
          <div className="bg-[#effcfb] dark:bg-[#163332] rounded-xl p-4 text-center border border-[#b3f0ec] dark:border-[#1e7574]">
            <div className="w-10 h-10 mx-auto rounded-xl bg-gradient-to-br from-[#28b5ad] to-[#1f9290] flex items-center justify-center mb-3">
              <ToothIcon className="text-white" size={20} />
            </div>
            <p className="text-sm font-semibold text-[#1d4d4c] dark:text-[#43cec6]">Medical Grade</p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-col sm:flex-row gap-3 pt-2">
          <Button
            variant="primary"
            onClick={handleDownload}
            leftIcon={<DownloadIcon size={18} />}
            className="flex-1"
          >
            {t("downloadAndContinue")}
          </Button>
          <Button
            variant="ghost"
            onClick={refreshStatus}
            leftIcon={<RefreshIcon size={18} />}
          >
            {t("tryAgain")}
          </Button>
        </div>
      </CardBody>
    </Card>
  );

  // ============================================
  // MAIN RENDER
  // ============================================
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#f8fafc] via-[#f0f7fc] to-[#effcfb] dark:from-[#0f172a] dark:via-[#1e293b] dark:to-[#0f172a] p-4 relative overflow-hidden">
      {/* Background decorations */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-[#2d96c6]/10 to-[#28b5ad]/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-tr from-[#28b5ad]/10 to-[#2d96c6]/10 rounded-full blur-3xl" />
      </div>

      {/* Main content */}
      <div className="relative z-10 w-full max-w-xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-[#2d96c6] to-[#28b5ad] shadow-xl shadow-[#2d96c6]/30 mb-4">
            <ToothIcon className="text-white" size={32} />
          </div>
          <h1 className="text-3xl font-bold text-[#1e293b] dark:text-white">
            {t("appName")}
          </h1>
          <p className="mt-2 text-[#64748b] dark:text-[#94a3b8]">
            {t("setupSubtitle")}
          </p>
        </div>

        {/* Step indicator */}
        {step !== "error" && <StepIndicator currentStep={currentStepIndex} steps={steps} />}

        {/* Content */}
        {step === "checking" && renderChecking()}
        {step === "error" && renderError()}
        {step === "downloading" && renderDownloading()}
        {step === "confirm" && renderConfirm()}
      </div>
    </div>
  );
}

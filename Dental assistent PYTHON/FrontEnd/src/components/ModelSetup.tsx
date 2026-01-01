import React, { useEffect, useRef, useState } from "react";
import { checkModelStatus, downloadModel, HardwareInfo } from "../api";
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
                  ? "bg-gradient-to-br from-[#35a7d3] to-[#00bdb8] text-white shadow-lg shadow-[#35a7d3]/30"
                  : "bg-[#e2e8f0] text-[#94a3b8]"
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
                  ? "text-[#1e293b]"
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
              ${index < currentStep ? "bg-[#10b981]" : "bg-[#e2e8f0]"}
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
  const profileLabels: Record<string, { label: string; variant: "success" | "warning" | "primary" }> = {
    high_vram: { label: "High Performance GPU", variant: "success" },
    low_vram: { label: "Standard GPU", variant: "primary" },
    cpu_only: { label: "CPU Mode", variant: "warning" },
  };

  const profile = profileLabels[hardware.hardware_profile] || {
    label: hardware.hardware_profile,
    variant: "primary" as const,
  };

  return (
    <div className="bg-gradient-to-br from-[#f8fafc] to-[#e6f4f9] rounded-2xl p-5 border border-[#e2e8f0]">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#35a7d3] to-[#00bdb8] shadow-lg shadow-[#35a7d3]/20 flex items-center justify-center flex-shrink-0">
          <CpuIcon className="text-white" size={24} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-[#1e293b]">System Profile</h3>
            <Badge variant={profile.variant}>{profile.label}</Badge>
          </div>
          <p className="mt-2 text-sm text-[#64748b]">
            Recommended model:{" "}
            <span className="font-medium text-[#334155]">
              {hardware.recommended_model}
            </span>
          </p>
          {hardware.download_url && (
            <p className="mt-1 text-xs text-[#94a3b8] truncate">
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
  const [step, setStep] = useState<"checking" | "confirm" | "downloading" | "error">("checking");
  const [hardware, setHardware] = useState<HardwareInfo | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [progress, setProgress] = useState(0);

  const progressTimer = useRef<number | null>(null);
  const statusTimer = useRef<number | null>(null);

  const steps = ["Check System", "Download Models", "Complete"];
  const currentStepIndex = step === "checking" ? 0 : step === "confirm" ? 0 : step === "downloading" ? 1 : 0;

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

  // ============================================
  // RENDER: CHECKING STATE
  // ============================================
  const renderChecking = () => (
    <Card glass className="text-center">
      <CardBody className="py-12">
        <MedicalLoader text="Analyzing your system..." />
        <p className="mt-6 text-sm text-[#94a3b8]">
          Detecting hardware capabilities and model requirements
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
            <h3 className="font-semibold text-white">Setup Error</h3>
            <p className="text-sm text-red-100">Something went wrong</p>
          </div>
        </div>
      </div>
      <CardBody>
        <Alert variant="error" icon={<AlertCircleIcon size={18} />}>
          {errorMsg || "An unexpected error occurred"}
        </Alert>
        <div className="mt-6 flex flex-col sm:flex-row gap-3">
          <Button
            variant="danger"
            onClick={refreshStatus}
            leftIcon={<RefreshIcon size={18} />}
            className="flex-1"
          >
            Retry Connection
          </Button>
          <Button
            variant="ghost"
            onClick={() => window.location.reload()}
            className="flex-1"
          >
            Restart Application
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
      <div className="bg-gradient-to-r from-[#35a7d3] to-[#00bdb8] px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center">
            <DownloadIcon className="text-white animate-bounce" size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-white">Downloading Models</h3>
            <p className="text-sm text-white/80">Please wait while we set things up</p>
          </div>
        </div>
      </div>
      <CardBody className="space-y-6">
        {/* Progress section */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-[#334155]">
              Download Progress
            </span>
            <span className="text-sm font-bold text-[#35a7d3]">{progress}%</span>
          </div>
          <ProgressBar value={progress} size="lg" />
        </div>

        {/* Hardware info */}
        {hardware && <HardwareInfoCard hardware={hardware} />}

        {/* Info message */}
        <Alert variant="info">
          <p className="text-sm">
            <strong>Tip:</strong> You can keep this window open. The download will continue
            automatically and the app will start when ready.
          </p>
        </Alert>

        {/* Download stats */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-[#f8fafc] rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-[#35a7d3]">
              {hardware?.recommended_model?.includes("7B") ? "~4GB" : "~2GB"}
            </p>
            <p className="text-xs text-[#94a3b8] mt-1">Estimated Size</p>
          </div>
          <div className="bg-[#f8fafc] rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-[#00bdb8]">100%</p>
            <p className="text-xs text-[#94a3b8] mt-1">Local & Private</p>
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
      <div className="bg-gradient-to-r from-[#35a7d3] to-[#00bdb8] px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center">
            <SettingsIcon className="text-white" size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-white">Initial Setup Required</h3>
            <p className="text-sm text-white/80">Download AI models to get started</p>
          </div>
        </div>
      </div>
      <CardBody className="space-y-6">
        {/* Introduction */}
        <div>
          <p className="text-[#475569] leading-relaxed">
            To enable transcription and AI summarization, we need to download the
            language models to your device. This is a <strong>one-time setup</strong> that
            enables fully <strong>offline operation</strong>.
          </p>
        </div>

        {/* Hardware info */}
        {hardware && <HardwareInfoCard hardware={hardware} />}

        {/* Features */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-[#f0fdf4] rounded-xl p-4 text-center border border-[#bbf7d0]">
            <div className="w-10 h-10 mx-auto rounded-xl bg-gradient-to-br from-[#10b981] to-[#059669] flex items-center justify-center mb-3">
              <CheckCircleIcon className="text-white" size={20} />
            </div>
            <p className="text-sm font-semibold text-[#166534]">100% Private</p>
            <p className="text-xs text-[#22c55e] mt-1">Data stays on device</p>
          </div>
          <div className="bg-[#e6f4f9] rounded-xl p-4 text-center border border-[#c0e4f1]">
            <div className="w-10 h-10 mx-auto rounded-xl bg-gradient-to-br from-[#35a7d3] to-[#2584ae] flex items-center justify-center mb-3">
              <CpuIcon className="text-white" size={20} />
            </div>
            <p className="text-sm font-semibold text-[#0d5072]">Offline Ready</p>
            <p className="text-xs text-[#35a7d3] mt-1">No internet needed</p>
          </div>
          <div className="bg-[#e0f7f6] rounded-xl p-4 text-center border border-[#b3ebe8]">
            <div className="w-10 h-10 mx-auto rounded-xl bg-gradient-to-br from-[#00bdb8] to-[#009a94] flex items-center justify-center mb-3">
              <ToothIcon className="text-white" size={20} />
            </div>
            <p className="text-sm font-semibold text-[#006860]">Medical Grade</p>
            <p className="text-xs text-[#00bdb8] mt-1">Optimized for dental</p>
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
            Download and Continue
          </Button>
          <Button
            variant="ghost"
            onClick={refreshStatus}
            leftIcon={<RefreshIcon size={18} />}
          >
            Re-check Status
          </Button>
        </div>
      </CardBody>
    </Card>
  );

  // ============================================
  // MAIN RENDER
  // ============================================
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#f8fafc] via-[#e6f4f9] to-[#e0f7f6] p-4 relative overflow-hidden">
      {/* Background decorations */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-[#35a7d3]/10 to-[#00bdb8]/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-tr from-[#00bdb8]/10 to-[#35a7d3]/10 rounded-full blur-3xl" />
      </div>

      {/* Main content */}
      <div className="relative z-10 w-full max-w-xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-[#35a7d3] to-[#00bdb8] shadow-xl shadow-[#35a7d3]/30 mb-4">
            <ToothIcon className="text-white" size={32} />
          </div>
          <h1 className="text-3xl font-bold text-[#1e293b]">
            Dental Assistant
          </h1>
          <p className="mt-2 text-[#64748b]">
            One-time setup for offline AI capabilities
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

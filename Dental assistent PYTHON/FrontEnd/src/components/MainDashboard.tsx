import React, { useCallback, useRef, useState } from "react";
import { summarizeText, transcribeAudio } from "../api";
import {
  Button,
  Card,
  CardHeader,
  CardBody,
  Alert,
  Badge,
  MedicalLoader,
  Container,
} from "./ui";
import {
  ToothIcon,
  MicrophoneIcon,
  WaveformIcon,
  DocumentIcon,
  SparklesIcon,
  UploadCloudIcon,
  FileAudioIcon,
  XIcon,
  HeartPulseIcon,
} from "./ui/Icons";

const ALLOWED_EXTS = new Set(["wav", "mp3", "m4a", "ogg"]);

function getExt(name: string) {
  const parts = name.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
}

// ============================================
// HEADER COMPONENT
// ============================================
const Header: React.FC<{ onClear: () => void; hasContent: boolean }> = ({
  onClear,
  hasContent,
}) => (
  <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-[#e2e8f0] shadow-sm">
    <Container>
      <div className="flex items-center justify-between py-4">
        {/* Logo and title */}
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#35a7d3] to-[#00bdb8] shadow-lg shadow-[#35a7d3]/30 flex items-center justify-center">
              <ToothIcon className="text-white" size={24} />
            </div>
            <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-white shadow-md flex items-center justify-center">
              <HeartPulseIcon className="text-[#00bdb8]" size={12} />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#1e293b]">Dental Assistant</h1>
            <p className="text-sm text-[#64748b]">AI-Powered Documentation</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <Badge variant="success">
            <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse" />
            Online
          </Badge>
          {hasContent && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClear}
              leftIcon={<XIcon size={16} />}
            >
              Clear
            </Button>
          )}
        </div>
      </div>
    </Container>
  </header>
);

// ============================================
// UPLOAD ZONE COMPONENT
// ============================================
interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  fileName: string | null;
  isLoading: boolean;
  isDragActive: boolean;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  inputRef: React.RefObject<HTMLInputElement>;
}

const UploadZone: React.FC<UploadZoneProps> = ({
  onFileSelect,
  fileName,
  isLoading,
  isDragActive,
  onDragOver,
  onDragLeave,
  onDrop,
  inputRef,
}) => (
  <Card
    className={`
      relative overflow-hidden transition-all duration-300
      ${isDragActive ? "ring-4 ring-[#35a7d3]/30 border-[#35a7d3]" : ""}
      ${isLoading ? "opacity-50 pointer-events-none" : ""}
    `}
    hover={!isLoading}
  >
    {/* Gradient background pattern */}
    <div className="absolute inset-0 bg-gradient-to-br from-[#e6f4f9]/50 via-white to-[#e0f7f6]/50 pointer-events-none" />

    {/* Decorative circles */}
    <div className="absolute -top-20 -right-20 w-40 h-40 bg-gradient-to-br from-[#35a7d3]/10 to-transparent rounded-full blur-2xl pointer-events-none" />
    <div className="absolute -bottom-20 -left-20 w-40 h-40 bg-gradient-to-tr from-[#00bdb8]/10 to-transparent rounded-full blur-2xl pointer-events-none" />

    <CardBody className="relative">
      <div
        className="flex flex-col items-center justify-center py-12 cursor-pointer"
        onClick={() => inputRef.current?.click()}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
      >
        {/* Upload icon */}
        <div
          className={`
            w-20 h-20 rounded-2xl flex items-center justify-center mb-6
            transition-all duration-300
            ${
              isDragActive
                ? "bg-gradient-to-br from-[#35a7d3] to-[#00bdb8] scale-110"
                : "bg-gradient-to-br from-[#e6f4f9] to-[#e0f7f6]"
            }
          `}
        >
          <UploadCloudIcon
            className={isDragActive ? "text-white" : "text-[#35a7d3]"}
            size={40}
          />
        </div>

        {/* Title */}
        <h3 className="text-xl font-semibold text-[#1e293b] mb-2">
          {isDragActive ? "Drop your audio file here" : "Upload Audio Recording"}
        </h3>

        {/* Description */}
        <p className="text-[#64748b] mb-6 text-center max-w-md">
          Drag and drop your audio file here, or click to browse.
          We'll transcribe and summarize it automatically.
        </p>

        {/* File type badges */}
        <div className="flex flex-wrap justify-center gap-2 mb-6">
          {["WAV", "MP3", "M4A", "OGG"].map((ext) => (
            <Badge key={ext} variant="neutral">
              <FileAudioIcon size={12} />
              {ext}
            </Badge>
          ))}
        </div>

        {/* Upload button */}
        <Button
          variant="primary"
          leftIcon={<MicrophoneIcon size={18} />}
          disabled={isLoading}
        >
          Choose Audio File
        </Button>

        {/* Selected file info */}
        {fileName && (
          <div className="mt-4 flex items-center gap-2 px-4 py-2 bg-[#f0fdf4] rounded-lg border border-[#bbf7d0]">
            <FileAudioIcon className="text-[#10b981]" size={16} />
            <span className="text-sm font-medium text-[#166534]">{fileName}</span>
          </div>
        )}

        {/* Hidden input */}
        <input
          ref={inputRef}
          type="file"
          accept=".wav,.mp3,.m4a,.ogg"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              onFileSelect(file);
              e.target.value = "";
            }
          }}
        />
      </div>
    </CardBody>

    {/* Max size info */}
    <div className="px-6 py-3 bg-[#f8fafc] border-t border-[#e2e8f0] text-center">
      <p className="text-xs text-[#94a3b8]">
        Maximum file size: 10 MB
      </p>
    </div>
  </Card>
);

// ============================================
// PROCESSING INDICATOR COMPONENT
// ============================================
const ProcessingIndicator: React.FC = () => (
  <Card>
    <CardBody className="py-10">
      <div className="flex flex-col items-center">
        <MedicalLoader />
        <h3 className="mt-6 text-lg font-semibold text-[#1e293b]">
          Processing Audio
        </h3>
        <p className="mt-2 text-[#64748b] text-center max-w-md">
          Transcribing your audio and generating a medical summary.
          This may take a moment depending on the file length.
        </p>

        {/* Processing steps */}
        <div className="mt-8 flex items-center gap-8">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#35a7d3] to-[#2584ae] flex items-center justify-center">
              <WaveformIcon className="text-white" size={16} />
            </div>
            <span className="text-sm font-medium text-[#35a7d3]">Transcribing</span>
          </div>
          <div className="w-8 h-0.5 bg-[#e2e8f0] rounded" />
          <div className="flex items-center gap-2 opacity-50">
            <div className="w-8 h-8 rounded-lg bg-[#e2e8f0] flex items-center justify-center">
              <SparklesIcon className="text-[#94a3b8]" size={16} />
            </div>
            <span className="text-sm font-medium text-[#94a3b8]">Summarizing</span>
          </div>
        </div>
      </div>
    </CardBody>
  </Card>
);

// ============================================
// RESULT CARD COMPONENT
// ============================================
interface ResultCardProps {
  title: string;
  content: string | null;
  icon: React.ReactNode;
  gradientFrom: string;
  gradientTo: string;
  isPending: boolean;
}

const ResultCard: React.FC<ResultCardProps> = ({
  title,
  content,
  icon,
  gradientFrom,
  gradientTo,
  isPending,
}) => (
  <Card className="h-full flex flex-col" hover>
    <CardHeader icon={icon}>
      <div>
        <h2 className="font-semibold text-[#1e293b]">{title}</h2>
        <p className="text-xs text-[#64748b]">
          {isPending ? "Processing..." : "Generated by AI"}
        </p>
      </div>
    </CardHeader>
    <CardBody className="flex-1">
      {isPending ? (
        <div className="flex items-center justify-center py-8">
          <div className="flex flex-col items-center gap-3">
            <div
              className={`
                w-10 h-10 rounded-xl bg-gradient-to-br ${gradientFrom} ${gradientTo}
                flex items-center justify-center animate-pulse
              `}
            >
              {icon}
            </div>
            <p className="text-sm text-[#94a3b8]">Generating...</p>
          </div>
        </div>
      ) : (
        <div className="prose prose-sm max-w-none">
          <p className="text-[#475569] leading-relaxed whitespace-pre-wrap">
            {content}
          </p>
        </div>
      )}
    </CardBody>
  </Card>
);

// ============================================
// MAIN DASHBOARD COMPONENT
// ============================================
export default function MainDashboard() {
  const [fileName, setFileName] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [isDragActive, setIsDragActive] = useState(false);

  const inputRef = useRef<HTMLInputElement | null>(null);

  const processFile = async (file: File) => {
    const ext = getExt(file.name);
    if (!ALLOWED_EXTS.has(ext)) {
      setError("Please upload a valid audio file (WAV, MP3, M4A, OGG).");
      return;
    }

    setFileName(file.name);
    setIsLoading(true);
    setError(null);
    setTranscript(null);
    setSummary(null);

    try {
      const tr = await transcribeAudio(file);
      setTranscript(tr.text);

      const sum = await summarizeText(tr.text);
      setSummary(sum.summary);
    } catch (e) {
      console.error(e);
      setError(e instanceof Error ? e.message : "An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const onDrop = useCallback((evt: React.DragEvent<HTMLDivElement>) => {
    evt.preventDefault();
    setIsDragActive(false);
    const file = evt.dataTransfer.files?.[0];
    if (file) void processFile(file);
  }, []);

  const onDragOver = useCallback((evt: React.DragEvent<HTMLDivElement>) => {
    evt.preventDefault();
    setIsDragActive(true);
  }, []);

  const onDragLeave = useCallback((evt: React.DragEvent<HTMLDivElement>) => {
    evt.preventDefault();
    setIsDragActive(false);
  }, []);

  const clearAll = () => {
    setFileName(null);
    setError(null);
    setTranscript(null);
    setSummary(null);
  };

  const hasContent = !!(transcript || summary || error);

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f8fafc] via-[#e6f4f9] to-[#f8fafc]">
      {/* Header */}
      <Header onClear={clearAll} hasContent={hasContent} />

      {/* Main content */}
      <main className="py-8">
        <Container size="lg">
          <div className="space-y-8">
            {/* Upload section */}
            <section>
              <UploadZone
                onFileSelect={processFile}
                fileName={fileName}
                isLoading={isLoading}
                isDragActive={isDragActive}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
                inputRef={inputRef}
              />
            </section>

            {/* Error message */}
            {error && (
              <section className="animate-fade-in">
                <Alert
                  variant="error"
                  icon={<XIcon size={18} />}
                  className="shadow-lg"
                >
                  <div>
                    <p className="font-semibold">Processing Error</p>
                    <p className="mt-1 text-sm opacity-90">{error}</p>
                  </div>
                </Alert>
              </section>
            )}

            {/* Loading indicator */}
            {isLoading && (
              <section className="animate-fade-in">
                <ProcessingIndicator />
              </section>
            )}

            {/* Results section */}
            {(transcript || summary) && !isLoading && (
              <section className="animate-fade-in-up">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Transcript card */}
                  <ResultCard
                    title="Transcript"
                    content={transcript}
                    icon={<DocumentIcon className="text-white" size={20} />}
                    gradientFrom="from-[#35a7d3]"
                    gradientTo="to-[#2584ae]"
                    isPending={!transcript}
                  />

                  {/* Summary card */}
                  <ResultCard
                    title="Medical Summary"
                    content={summary}
                    icon={<SparklesIcon className="text-white" size={20} />}
                    gradientFrom="from-[#00bdb8]"
                    gradientTo="to-[#009a94]"
                    isPending={!summary}
                  />
                </div>

                {/* Quick actions */}
                <div className="mt-6 flex flex-wrap justify-center gap-4">
                  <Button
                    variant="secondary"
                    onClick={() => inputRef.current?.click()}
                    leftIcon={<MicrophoneIcon size={18} />}
                  >
                    Upload Another Recording
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => {
                      if (summary) {
                        navigator.clipboard.writeText(summary);
                      }
                    }}
                  >
                    Copy Summary
                  </Button>
                </div>
              </section>
            )}

            {/* Empty state hint */}
            {!hasContent && !isLoading && (
              <section className="text-center py-8">
                <div className="flex justify-center gap-4">
                  <div className="flex items-center gap-2 text-[#94a3b8]">
                    <div className="w-8 h-8 rounded-lg bg-[#f1f5f9] flex items-center justify-center">
                      <span className="text-sm font-bold">1</span>
                    </div>
                    <span className="text-sm">Upload audio</span>
                  </div>
                  <div className="w-8 h-0.5 bg-[#e2e8f0] self-center rounded" />
                  <div className="flex items-center gap-2 text-[#94a3b8]">
                    <div className="w-8 h-8 rounded-lg bg-[#f1f5f9] flex items-center justify-center">
                      <span className="text-sm font-bold">2</span>
                    </div>
                    <span className="text-sm">AI transcribes</span>
                  </div>
                  <div className="w-8 h-0.5 bg-[#e2e8f0] self-center rounded" />
                  <div className="flex items-center gap-2 text-[#94a3b8]">
                    <div className="w-8 h-8 rounded-lg bg-[#f1f5f9] flex items-center justify-center">
                      <span className="text-sm font-bold">3</span>
                    </div>
                    <span className="text-sm">Get summary</span>
                  </div>
                </div>
              </section>
            )}
          </div>
        </Container>
      </main>

      {/* Footer */}
      <footer className="py-6 border-t border-[#e2e8f0] bg-white/50 backdrop-blur-sm">
        <Container>
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-[#94a3b8]">
            <div className="flex items-center gap-2">
              <ToothIcon size={16} />
              <span>Dental Assistant v1.0</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse" />
                AI Engine Active
              </span>
              <span>100% Local Processing</span>
            </div>
          </div>
        </Container>
      </footer>
    </div>
  );
}

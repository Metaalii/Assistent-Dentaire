import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { summarizeTextStream, transcribeAudio } from "../api";
import { useProfile } from "../hooks/useProfile";
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
  StopIcon,
  DownloadIcon,
} from "./ui/Icons";

const ALLOWED_EXTS = new Set(["wav", "mp3", "m4a", "ogg", "webm", "mp4"]);

function getExt(name: string) {
  const parts = name.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
}

// ============================================
// HEADER COMPONENT (memoized)
// ============================================
const Header: React.FC<{ onClear: () => void; hasContent: boolean }> = React.memo(({
  onClear,
  hasContent,
}) => (
  <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-[#e2e8f0] shadow-sm">
    <Container>
      <div className="flex items-center justify-between py-4">
        {/* Logo and title */}
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#2d96c6] to-[#28b5ad] shadow-lg shadow-[#2d96c6]/30 flex items-center justify-center">
              <ToothIcon className="text-white" size={24} />
            </div>
            <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-white shadow-md flex items-center justify-center">
              <HeartPulseIcon className="text-[#28b5ad]" size={12} />
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
));

Header.displayName = 'Header';

// ============================================
// UPLOAD ZONE COMPONENT (memoized)
// ============================================
interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  fileName: string | null;
  isLoading: boolean;
  isDragActive: boolean;
  onDragOver: (e: React.DragEvent<HTMLDivElement>) => void;
  onDragLeave: (e: React.DragEvent<HTMLDivElement>) => void;
  onDrop: (e: React.DragEvent<HTMLDivElement>) => void;
  inputRef: React.RefObject<HTMLInputElement>;
}

const UploadZone: React.FC<UploadZoneProps> = React.memo(({
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
      ${isDragActive ? "ring-4 ring-[#2d96c6]/30 border-[#2d96c6]" : ""}
      ${isLoading ? "opacity-50 pointer-events-none" : ""}
    `}
    hover={!isLoading}
  >
    {/* Gradient background pattern */}
    <div className="absolute inset-0 bg-gradient-to-br from-[#f0f7fc]/50 via-white to-[#effcfb]/50 pointer-events-none" />

    {/* Decorative circles */}
    <div className="absolute -top-20 -right-20 w-40 h-40 bg-gradient-to-br from-[#2d96c6]/10 to-transparent rounded-full blur-2xl pointer-events-none" />
    <div className="absolute -bottom-20 -left-20 w-40 h-40 bg-gradient-to-tr from-[#28b5ad]/10 to-transparent rounded-full blur-2xl pointer-events-none" />

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
                ? "bg-gradient-to-br from-[#2d96c6] to-[#28b5ad] scale-110"
                : "bg-gradient-to-br from-[#f0f7fc] to-[#effcfb]"
            }
          `}
        >
          <UploadCloudIcon
            className={isDragActive ? "text-white" : "text-[#2d96c6]"}
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
          {["WAV", "MP3", "M4A", "OGG", "WEBM", "MP4"].map((ext) => (
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
          accept=".wav,.mp3,.m4a,.ogg,.webm,.mp4"
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
        Maximum file size: 100 MB
      </p>
    </div>
  </Card>
));

UploadZone.displayName = 'UploadZone';

// ============================================
// WAVEFORM VISUALIZER COMPONENT (memoized to prevent re-renders)
// ============================================
const WaveformVisualizer: React.FC = React.memo(() => {
  // Generate heights once and memoize them
  const barHeights = useMemo(
    () => Array.from({ length: 12 }, () => Math.random() * 24 + 8),
    []
  );

  return (
    <div className="flex items-center justify-center gap-1 mb-6 h-8">
      {barHeights.map((height, i) => (
        <div
          key={i}
          className="w-1 bg-[#2d96c6] rounded-full animate-pulse"
          style={{
            height: `${height}px`,
            animationDelay: `${i * 0.1}s`,
            animationDuration: '0.5s'
          }}
        />
      ))}
    </div>
  );
});

WaveformVisualizer.displayName = 'WaveformVisualizer';

// ============================================
// LIVE RECORDER COMPONENT
// ============================================
interface LiveRecorderProps {
  onRecordingComplete: (file: File) => void;
  isProcessing: boolean;
}

const LiveRecorder: React.FC<LiveRecorderProps> = ({ onRecordingComplete, isProcessing }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  // Keep ref in sync with state for cleanup
  useEffect(() => {
    audioUrlRef.current = audioUrl;
  }, [audioUrl]);

  // Cleanup on unmount only (empty deps)
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    };
  }, []);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const startRecording = async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
      });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const mimeType = mediaRecorder.mimeType;
        const blob = new Blob(chunksRef.current, { type: mimeType });
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);

        // Stop all tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
        }
      };

      mediaRecorder.start(1000); // Collect data every second
      setIsRecording(true);
      setIsPaused(false);
      setDuration(0);

      timerRef.current = window.setInterval(() => {
        setDuration(d => d + 1);
      }, 1000);

    } catch (err) {
      console.error('Error accessing microphone:', err);
      setError('Could not access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsPaused(false);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && isRecording && !isPaused) {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && isRecording && isPaused) {
      mediaRecorderRef.current.resume();
      setIsPaused(false);
      timerRef.current = window.setInterval(() => {
        setDuration(d => d + 1);
      }, 1000);
    }
  };

  const discardRecording = () => {
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    setDuration(0);
    chunksRef.current = [];
  };

  const sendRecording = () => {
    if (chunksRef.current.length > 0) {
      const mimeType = mediaRecorderRef.current?.mimeType || 'audio/webm';
      const ext = mimeType.includes('webm') ? 'webm' : 'mp4';
      const blob = new Blob(chunksRef.current, { type: mimeType });
      const file = new File([blob], `recording-${Date.now()}.${ext}`, { type: mimeType });
      onRecordingComplete(file);
      discardRecording();
    }
  };

  return (
    <Card
      className={`relative overflow-hidden transition-all duration-300 ${isProcessing ? "opacity-50 pointer-events-none" : ""}`}
      hover={!isProcessing}
    >
      {/* Gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#f0f7fc]/50 via-white to-[#effcfb]/50 pointer-events-none" />

      {/* Decorative circles */}
      <div className="absolute -top-20 -left-20 w-40 h-40 bg-gradient-to-br from-[#2d96c6]/10 to-transparent rounded-full blur-2xl pointer-events-none" />
      <div className="absolute -bottom-20 -right-20 w-40 h-40 bg-gradient-to-tr from-[#28b5ad]/10 to-transparent rounded-full blur-2xl pointer-events-none" />

      <CardBody className="relative">
        <div className="flex flex-col items-center justify-center py-8">
          {/* Recording indicator */}
          <div
            className={`
              w-20 h-20 rounded-full flex items-center justify-center mb-6
              transition-all duration-300
              ${isRecording
                ? isPaused
                  ? "bg-gradient-to-br from-[#f59e0b] to-[#d97706] animate-pulse"
                  : "bg-gradient-to-br from-[#ef4444] to-[#dc2626] animate-pulse"
                : audioUrl
                  ? "bg-gradient-to-br from-[#10b981] to-[#059669]"
                  : "bg-gradient-to-br from-[#2d96c6] to-[#28b5ad]"
              }
            `}
          >
            {isRecording ? (
              <WaveformIcon className="text-white" size={40} />
            ) : audioUrl ? (
              <FileAudioIcon className="text-white" size={40} />
            ) : (
              <MicrophoneIcon className="text-white" size={40} />
            )}
          </div>

          {/* Title */}
          <h3 className="text-xl font-semibold text-[#1e293b] mb-2">
            {isRecording
              ? isPaused ? "Recording Paused" : "Recording..."
              : audioUrl
                ? "Recording Ready"
                : "Live Recording"
            }
          </h3>

          {/* Duration display */}
          {(isRecording || audioUrl) && (
            <div className="text-3xl font-mono font-bold text-[#1e293b] mb-4">
              {formatDuration(duration)}
            </div>
          )}

          {/* Description */}
          {!isRecording && !audioUrl && (
            <p className="text-[#64748b] mb-6 text-center max-w-md">
              Record audio directly from your microphone. Click the button below to start recording your consultation.
            </p>
          )}

          {/* Waveform visualization when recording */}
          {isRecording && !isPaused && (
            <WaveformVisualizer />
          )}

          {/* Error message */}
          {error && (
            <Alert variant="error" className="mb-4 max-w-md">
              {error}
            </Alert>
          )}

          {/* Audio preview */}
          {audioUrl && (
            <div className="w-full max-w-md mb-6">
              <audio src={audioUrl} controls className="w-full" />
            </div>
          )}

          {/* Control buttons */}
          <div className="flex flex-wrap justify-center gap-3">
            {!isRecording && !audioUrl && (
              <Button
                variant="primary"
                onClick={startRecording}
                leftIcon={<MicrophoneIcon size={18} />}
              >
                Start Recording
              </Button>
            )}

            {isRecording && (
              <>
                {isPaused ? (
                  <Button
                    variant="primary"
                    onClick={resumeRecording}
                    leftIcon={<MicrophoneIcon size={18} />}
                    className="bg-gradient-to-r from-[#10b981] to-[#059669]"
                  >
                    Resume
                  </Button>
                ) : (
                  <Button
                    variant="secondary"
                    onClick={pauseRecording}
                    leftIcon={<WaveformIcon size={18} />}
                  >
                    Pause
                  </Button>
                )}
                <Button
                  variant="danger"
                  onClick={stopRecording}
                  leftIcon={<StopIcon size={18} />}
                >
                  Stop
                </Button>
              </>
            )}

            {audioUrl && (
              <>
                <Button
                  variant="primary"
                  onClick={sendRecording}
                  leftIcon={<SparklesIcon size={18} />}
                >
                  Process Recording
                </Button>
                <Button
                  variant="ghost"
                  onClick={discardRecording}
                  leftIcon={<XIcon size={18} />}
                >
                  Discard
                </Button>
                <Button
                  variant="secondary"
                  onClick={startRecording}
                  leftIcon={<MicrophoneIcon size={18} />}
                >
                  Record Again
                </Button>
              </>
            )}
          </div>
        </div>
      </CardBody>

      {/* Info footer */}
      <div className="px-6 py-3 bg-[#f8fafc] border-t border-[#e2e8f0] text-center">
        <p className="text-xs text-[#94a3b8]">
          Recording is processed locally on your device
        </p>
      </div>
    </Card>
  );
};

// ============================================
// PROCESSING INDICATOR COMPONENT (memoized)
// ============================================
const ProcessingIndicator: React.FC = React.memo(() => (
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
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#2d96c6] to-[#1e7aa8] flex items-center justify-center">
              <WaveformIcon className="text-white" size={16} />
            </div>
            <span className="text-sm font-medium text-[#2d96c6]">Transcribing</span>
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
));

ProcessingIndicator.displayName = 'ProcessingIndicator';

// ============================================
// RESULT CARD COMPONENT (memoized)
// ============================================
interface ResultCardProps {
  title: string;
  content: string | null;
  icon: React.ReactNode;
  gradientFrom: string;
  gradientTo: string;
  isPending: boolean;
}

const ResultCard: React.FC<ResultCardProps> = React.memo(({
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
));

ResultCard.displayName = 'ResultCard';

// ============================================
// MAIN DASHBOARD COMPONENT
// ============================================
export default function MainDashboard() {
  const [fileName, setFileName] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [document, setDocument] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState<string>("");
  const [isDragActive, setIsDragActive] = useState(false);

  const { getDocumentHeader, getDocumentFooter } = useProfile();
  const inputRef = useRef<HTMLInputElement | null>(null);

  const processFile = useCallback(async (file: File) => {
    const ext = getExt(file.name);
    if (!ALLOWED_EXTS.has(ext)) {
      setError("Please upload a valid audio file (WAV, MP3, M4A, OGG).");
      return;
    }

    setFileName(file.name);
    setIsLoading(true);
    setIsStreaming(false);
    setError(null);
    setTranscript(null);
    setDocument(null);
    setStreamingContent("");

    try {
      // Step 1: Transcribe audio
      const tr = await transcribeAudio(file);
      setTranscript(tr.text);

      // Step 2: Generate summary with streaming for real-time feedback
      setIsLoading(false);
      setIsStreaming(true);

      await summarizeTextStream(
        tr.text,
        // onChunk: called for each token
        (chunk) => {
          setStreamingContent((prev) => prev + chunk);
        },
        // onComplete: called when generation is finished
        (fullText) => {
          // Combine header + generated content + footer
          const fullDocument = `${getDocumentHeader()}

${fullText}

${getDocumentFooter()}`;
          setDocument(fullDocument);
          setIsStreaming(false);
          setStreamingContent("");
        },
        // onError: called on error
        (err) => {
          console.error(err);
          setError(err.message);
          setIsStreaming(false);
          setStreamingContent("");
        }
      );
    } catch (e) {
      console.error(e);
      setError(e instanceof Error ? e.message : "An error occurred. Please try again.");
      setIsLoading(false);
      setIsStreaming(false);
    }
  }, [getDocumentHeader, getDocumentFooter]);

  const handleExportPDF = useCallback(() => {
    if (!document) return;

    // Sanitize content to prevent XSS - escape HTML entities
    const escapeHtml = (text: string): string => {
      const htmlEntities: Record<string, string> = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
      };
      return text.replace(/[&<>"']/g, (char) => htmlEntities[char] || char);
    };

    const sanitizedContent = escapeHtml(document).replace(/\n/g, '<br>');

    // Create a printable window
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>Document Dentaire</title>
          <meta charset="UTF-8">
          <style>
            body {
              font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
              padding: 40px;
              max-width: 800px;
              margin: 0 auto;
              line-height: 1.6;
            }
            @media print {
              body { padding: 20px; }
            }
          </style>
        </head>
        <body>${sanitizedContent}</body>
        </html>
      `);
      printWindow.document.close();
      printWindow.print();
    }
  }, [document]);

  const onDrop = useCallback((evt: React.DragEvent<HTMLDivElement>) => {
    evt.preventDefault();
    setIsDragActive(false);
    const file = evt.dataTransfer.files?.[0];
    if (file) void processFile(file);
  }, [processFile]);

  const onDragOver = useCallback((evt: React.DragEvent<HTMLDivElement>) => {
    evt.preventDefault();
    setIsDragActive(true);
  }, []);

  const onDragLeave = useCallback((evt: React.DragEvent<HTMLDivElement>) => {
    evt.preventDefault();
    setIsDragActive(false);
  }, []);

  const clearAll = useCallback(() => {
    setFileName(null);
    setError(null);
    setTranscript(null);
    setDocument(null);
  }, []);

  const hasContent = !!(transcript || document || error || isStreaming);

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f8fafc] via-[#f0f7fc] to-[#f8fafc]">
      {/* Header */}
      <Header onClear={clearAll} hasContent={hasContent} />

      {/* Main content */}
      <main className="py-8">
        <Container size="lg">
          <div className="space-y-8">
            {/* Upload and Record section */}
            <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
              <LiveRecorder
                onRecordingComplete={processFile}
                isProcessing={isLoading}
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

            {/* Streaming indicator - shows content as it's generated */}
            {isStreaming && (
              <section className="animate-fade-in">
                <Card className="overflow-hidden">
                  <CardHeader icon={<SparklesIcon className="text-white" size={20} />}>
                    <div className="flex items-center gap-3">
                      <div>
                        <h2 className="font-semibold text-[#1e293b]">Generating SmartNote</h2>
                        <p className="text-xs text-[#64748b]">AI is writing...</p>
                      </div>
                      <div className="flex gap-1">
                        {[0, 1, 2].map((i) => (
                          <div
                            key={i}
                            className="w-2 h-2 bg-[#2d96c6] rounded-full animate-bounce"
                            style={{ animationDelay: `${i * 0.15}s` }}
                          />
                        ))}
                      </div>
                    </div>
                  </CardHeader>
                  <CardBody>
                    <div className="min-h-[200px] p-4 bg-[#f8fafc] rounded-xl border-2 border-[#e2e8f0]">
                      <pre className="whitespace-pre-wrap text-[#1e293b] font-mono text-sm leading-relaxed">
                        {streamingContent}
                        <span className="inline-block w-2 h-4 bg-[#2d96c6] animate-pulse ml-1" />
                      </pre>
                    </div>
                  </CardBody>
                </Card>
              </section>
            )}

            {/* Document section */}
            {document && !isLoading && !isStreaming && (
              <section className="animate-fade-in-up">
                <Card className="overflow-hidden">
                  <CardHeader icon={<DocumentIcon className="text-white" size={20} />}>
                    <div>
                      <h2 className="font-semibold text-[#1e293b]">Document Généré</h2>
                      <p className="text-xs text-[#64748b]">Modifiable avant export</p>
                    </div>
                  </CardHeader>
                  <CardBody>
                    <textarea
                      value={document}
                      onChange={(e) => setDocument(e.target.value)}
                      className="w-full h-96 p-4 border-2 border-[#e2e8f0] rounded-xl bg-white text-[#1e293b] font-mono text-sm leading-relaxed resize-y focus:border-[#2d96c6] focus:ring-2 focus:ring-[#2d96c6]/20 outline-none"
                      placeholder="Document généré..."
                    />
                  </CardBody>
                </Card>

                {/* Quick actions */}
                <div className="mt-6 flex flex-wrap justify-center gap-4">
                  <Button
                    variant="primary"
                    onClick={handleExportPDF}
                    leftIcon={<DownloadIcon size={18} />}
                  >
                    Exporter en PDF
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      if (document) {
                        navigator.clipboard.writeText(document);
                      }
                    }}
                  >
                    Copier le document
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => inputRef.current?.click()}
                    leftIcon={<MicrophoneIcon size={18} />}
                  >
                    Nouvel enregistrement
                  </Button>
                </div>
              </section>
            )}

            {/* Empty state hint */}
            {!hasContent && !isLoading && !isStreaming && (
              <section className="text-center py-8">
                <div className="flex justify-center gap-4">
                  <div className="flex items-center gap-2 text-[#94a3b8]">
                    <div className="w-8 h-8 rounded-lg bg-[#f1f5f9] flex items-center justify-center">
                      <span className="text-sm font-bold">1</span>
                    </div>
                    <span className="text-sm">Télécharger audio</span>
                  </div>
                  <div className="w-8 h-0.5 bg-[#e2e8f0] self-center rounded" />
                  <div className="flex items-center gap-2 text-[#94a3b8]">
                    <div className="w-8 h-8 rounded-lg bg-[#f1f5f9] flex items-center justify-center">
                      <span className="text-sm font-bold">2</span>
                    </div>
                    <span className="text-sm">Transcription IA</span>
                  </div>
                  <div className="w-8 h-0.5 bg-[#e2e8f0] self-center rounded" />
                  <div className="flex items-center gap-2 text-[#94a3b8]">
                    <div className="w-8 h-8 rounded-lg bg-[#f1f5f9] flex items-center justify-center">
                      <span className="text-sm font-bold">3</span>
                    </div>
                    <span className="text-sm">Document généré</span>
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

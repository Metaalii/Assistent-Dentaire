import React, { useEffect, useMemo, useRef, useState } from "react";
import { useLanguage } from "../../i18n";
import { Card, CardBody, Button, Alert, ConfirmDialog } from "../ui";
import {
  MicrophoneIcon,
  WaveformIcon,
  SparklesIcon,
  FileAudioIcon,
  XIcon,
  StopIcon,
} from "../ui/Icons";

// ============================================
// WAVEFORM VISUALIZER (memoized)
// ============================================
const WaveformVisualizer: React.FC = React.memo(() => {
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
// LIVE RECORDER
// ============================================
interface LiveRecorderProps {
  onRecordingComplete: (file: File) => void;
  isProcessing: boolean;
}

const LiveRecorder: React.FC<LiveRecorderProps> = ({ onRecordingComplete, isProcessing }) => {
  const { t } = useLanguage();
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showDiscardConfirm, setShowDiscardConfirm] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  useEffect(() => {
    audioUrlRef.current = audioUrl;
  }, [audioUrl]);

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

        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
        }
      };

      mediaRecorder.start(1000);
      setIsRecording(true);
      setIsPaused(false);
      setDuration(0);

      timerRef.current = window.setInterval(() => {
        setDuration(d => d + 1);
      }, 1000);

    } catch (err) {
      console.error('Error accessing microphone:', err);
      setError(String(t("microphoneError")));
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
      <div className="absolute inset-0 bg-gradient-to-br from-[#f0f7fc]/50 via-white to-[#effcfb]/50 dark:from-[#1e293b]/50 dark:via-[#1e293b] dark:to-[#1e293b]/50 pointer-events-none" />

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
          <h3 className="text-xl font-semibold text-[#1e293b] dark:text-white mb-2">
            {isRecording
              ? isPaused ? t("recordingPaused") : t("recordingInProgress")
              : audioUrl
                ? t("recordingReady")
                : t("liveRecording")
            }
          </h3>

          {/* Duration display */}
          {(isRecording || audioUrl) && (
            <div className="text-3xl font-mono font-bold text-[#1e293b] dark:text-white mb-4">
              {formatDuration(duration)}
            </div>
          )}

          {/* Description */}
          {!isRecording && !audioUrl && (
            <p className="text-[#64748b] dark:text-[#94a3b8] mb-6 text-center max-w-md">
              {t("recordFromMicrophone")}
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
                {t("startRecording")}
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
                    {t("resumeRecording")}
                  </Button>
                ) : (
                  <Button
                    variant="secondary"
                    onClick={pauseRecording}
                    leftIcon={<WaveformIcon size={18} />}
                  >
                    {t("pauseRecording")}
                  </Button>
                )}
                <Button
                  variant="danger"
                  onClick={stopRecording}
                  leftIcon={<StopIcon size={18} />}
                >
                  {t("stopRecording")}
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
                  {t("processRecording")}
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setShowDiscardConfirm(true)}
                  leftIcon={<XIcon size={18} />}
                >
                  {t("discardRecording")}
                </Button>
                <Button
                  variant="secondary"
                  onClick={startRecording}
                  leftIcon={<MicrophoneIcon size={18} />}
                >
                  {t("recordAgain")}
                </Button>
              </>
            )}
          </div>
        </div>
      </CardBody>

      {/* Info footer */}
      <div className="px-6 py-3 bg-[#f8fafc] dark:bg-[#0f172a] border-t border-[#e2e8f0] dark:border-[#334155] text-center">
        <p className="text-xs text-[#94a3b8]">
          {t("localProcessing")}
        </p>
      </div>

      {/* Discard confirmation dialog */}
      <ConfirmDialog
        open={showDiscardConfirm}
        title={String(t("confirmDiscardTitle"))}
        message={String(t("confirmDiscardMessage"))}
        confirmLabel={String(t("confirmDiscardAction"))}
        cancelLabel={String(t("cancel"))}
        onConfirm={() => {
          setShowDiscardConfirm(false);
          discardRecording();
        }}
        onCancel={() => setShowDiscardConfirm(false)}
      />
    </Card>
  );
};

export default LiveRecorder;

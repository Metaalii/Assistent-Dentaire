import React, { useCallback, useRef, useState } from "react";
import { useSmartNoteStream } from "../hooks/useSmartNoteStream";
import { useProfile } from "../hooks/useProfile";
import { useLanguage } from "../i18n";
import { exportPDF } from "../utils/exportPDF";
import {
  Alert,
  Container,
  ConfirmDialog,
} from "./ui";
import {
  ToothIcon,
  XIcon,
} from "./ui/Icons";
import {
  Header,
  UploadZone,
  LiveRecorder,
  ProcessingIndicator,
  SmartNoteEditor,
  StreamingPreview,
} from "./dashboard";

interface MainDashboardProps {
  onViewHistory?: () => void;
}

export default function MainDashboard({ onViewHistory }: MainDashboardProps) {
  const { t, language } = useLanguage();
  const { profile } = useProfile();

  const {
    fileName,
    isLoading,
    isStreaming,
    error,
    document,
    originalDocument,
    streamingContent,
    isRagEnhanced,
    isSaved,
    hasContent,
    setDocument,
    processFile,
    clearAll,
    restoreOriginal,
    validateFile,
  } = useSmartNoteStream();

  const [isDragActive, setIsDragActive] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [showOverwriteConfirm, setShowOverwriteConfirm] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const inputRef = useRef<HTMLInputElement | null>(null);

  // Gate file processing: confirm before overwriting existing document
  const handleFileIntent = useCallback((file: File) => {
    if (!validateFile(file)) return;

    if (document) {
      setPendingFile(file);
      setShowOverwriteConfirm(true);
    } else {
      processFile(file);
    }
  }, [document, processFile, validateFile]);

  const handleClearIntent = useCallback(() => {
    if (document) {
      setShowClearConfirm(true);
    } else {
      clearAll();
    }
  }, [document, clearAll]);

  const handleExportPDF = useCallback(() => {
    if (!document) return;
    exportPDF(document, profile, language, {
      pdfTitle: String(t("pdfTitle")),
      pdfDate: String(t("pdfDate")),
      pdfConsultationNotes: String(t("pdfConsultationNotes")),
      pdfDisclaimer: String(t("pdfDisclaimer")),
      pdfConfidential: String(t("pdfConfidential")),
      professionalTitlePlaceholder: String(t("professionalTitlePlaceholder")),
    });
  }, [document, profile, language, t]);

  const onDrop = useCallback((evt: React.DragEvent<HTMLDivElement>) => {
    evt.preventDefault();
    setIsDragActive(false);
    const file = evt.dataTransfer.files?.[0];
    if (file) void handleFileIntent(file);
  }, [handleFileIntent]);

  const onDragOver = useCallback((evt: React.DragEvent<HTMLDivElement>) => {
    evt.preventDefault();
    setIsDragActive(true);
  }, []);

  const onDragLeave = useCallback((evt: React.DragEvent<HTMLDivElement>) => {
    evt.preventDefault();
    setIsDragActive(false);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f8fafc] via-[#f0f7fc] to-[#f8fafc] dark:from-[#0f172a] dark:via-[#1e293b] dark:to-[#0f172a]">
      <Header onClear={handleClearIntent} hasContent={hasContent} onViewHistory={onViewHistory} />

      <main className="py-8">
        <Container size="lg">
          <div className="space-y-8">
            {/* Upload and Record section */}
            <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <UploadZone
                onFileSelect={handleFileIntent}
                fileName={fileName}
                isLoading={isLoading}
                isDragActive={isDragActive}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
                inputRef={inputRef}
              />
              <LiveRecorder
                onRecordingComplete={handleFileIntent}
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
                    <p className="font-semibold">{t("processingError")}</p>
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

            {/* Streaming indicator */}
            {isStreaming && (
              <StreamingPreview content={streamingContent} />
            )}

            {/* Document editor */}
            {document && !isLoading && !isStreaming && (
              <SmartNoteEditor
                document={document}
                originalDocument={originalDocument}
                isRagEnhanced={isRagEnhanced}
                isSaved={isSaved}
                onDocumentChange={setDocument}
                onExportPDF={handleExportPDF}
                onRestoreOriginal={restoreOriginal}
                onNewRecording={() => inputRef.current?.click()}
              />
            )}

            {/* Empty state hint */}
            {!hasContent && !isLoading && !isStreaming && (
              <section className="text-center py-8">
                <div className="flex justify-center gap-4">
                  <div className="flex items-center gap-2 text-[#94a3b8]">
                    <div className="w-8 h-8 rounded-lg bg-[#f1f5f9] dark:bg-[#334155] flex items-center justify-center">
                      <span className="text-sm font-bold">1</span>
                    </div>
                    <span className="text-sm">{t("step1Upload")}</span>
                  </div>
                  <div className="w-8 h-0.5 bg-[#e2e8f0] dark:bg-[#334155] self-center rounded" />
                  <div className="flex items-center gap-2 text-[#94a3b8]">
                    <div className="w-8 h-8 rounded-lg bg-[#f1f5f9] dark:bg-[#334155] flex items-center justify-center">
                      <span className="text-sm font-bold">2</span>
                    </div>
                    <span className="text-sm">{t("step2Transcription")}</span>
                  </div>
                  <div className="w-8 h-0.5 bg-[#e2e8f0] dark:bg-[#334155] self-center rounded" />
                  <div className="flex items-center gap-2 text-[#94a3b8]">
                    <div className="w-8 h-8 rounded-lg bg-[#f1f5f9] dark:bg-[#334155] flex items-center justify-center">
                      <span className="text-sm font-bold">3</span>
                    </div>
                    <span className="text-sm">{t("step3Document")}</span>
                  </div>
                </div>
              </section>
            )}
          </div>
        </Container>
      </main>

      {/* Footer */}
      <footer className="py-6 border-t border-[#e2e8f0] dark:border-[#334155] bg-white/50 dark:bg-[#1e293b]/50 backdrop-blur-sm">
        <Container>
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-[#94a3b8]">
            <div className="flex items-center gap-2">
              <ToothIcon size={16} />
              <span>{t("appName")} v1.0</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse" />
                {t("aiEngineActive")}
              </span>
              <span>{t("localProcessingFooter")}</span>
            </div>
          </div>
        </Container>
      </footer>

      {/* Clear all confirmation dialog */}
      <ConfirmDialog
        open={showClearConfirm}
        title={String(t("confirmClearTitle"))}
        message={String(t("confirmClearMessage"))}
        confirmLabel={String(t("confirmClearAction"))}
        cancelLabel={String(t("cancel"))}
        onConfirm={() => {
          setShowClearConfirm(false);
          clearAll();
        }}
        onCancel={() => setShowClearConfirm(false)}
      />

      {/* Overwrite confirmation dialog */}
      <ConfirmDialog
        open={showOverwriteConfirm}
        title={String(t("confirmOverwriteTitle"))}
        message={String(t("confirmOverwriteMessage"))}
        confirmLabel={String(t("confirmOverwriteAction"))}
        cancelLabel={String(t("cancel"))}
        variant="warning"
        onConfirm={() => {
          setShowOverwriteConfirm(false);
          if (pendingFile) {
            processFile(pendingFile);
            setPendingFile(null);
          }
        }}
        onCancel={() => {
          setShowOverwriteConfirm(false);
          setPendingFile(null);
        }}
      />
    </div>
  );
}

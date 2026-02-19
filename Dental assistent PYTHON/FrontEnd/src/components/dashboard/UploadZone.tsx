import React from "react";
import { useLanguage } from "../../i18n";
import { Card, CardBody, Button, Badge } from "../ui";
import {
  MicrophoneIcon,
  UploadCloudIcon,
  FileAudioIcon,
} from "../ui/Icons";

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
}) => {
  const { t } = useLanguage();

  return (
    <Card
      className={`
        relative overflow-hidden transition-all duration-300
        ${isDragActive ? "ring-4 ring-[#2d96c6]/30 border-[#2d96c6]" : ""}
        ${isLoading ? "opacity-50 pointer-events-none" : ""}
      `}
      hover={!isLoading}
    >
      {/* Gradient background pattern */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#f0f7fc]/50 via-white to-[#effcfb]/50 dark:from-[#1e293b]/50 dark:via-[#1e293b] dark:to-[#1e293b]/50 pointer-events-none" />

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
          <h3 className="text-xl font-semibold text-[#1e293b] dark:text-white mb-2">
            {isDragActive ? t("dropAudioHere") : t("uploadAudioRecording")}
          </h3>

          {/* Description */}
          <p className="text-[#64748b] dark:text-[#94a3b8] mb-6 text-center max-w-md">
            {t("dragAndDropAudio")}
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
            {t("chooseAudioFile")}
          </Button>

          {/* Selected file info */}
          {fileName && (
            <div className="mt-4 flex items-center gap-2 px-4 py-2 bg-[#f0fdf4] dark:bg-[#14332a] rounded-lg border border-[#bbf7d0] dark:border-[#276749]">
              <FileAudioIcon className="text-[#10b981]" size={16} />
              <span className="text-sm font-medium text-[#166534] dark:text-[#6ee7b7]">{fileName}</span>
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
      <div className="px-6 py-3 bg-[#f8fafc] dark:bg-[#0f172a] border-t border-[#e2e8f0] dark:border-[#334155] text-center">
        <p className="text-xs text-[#94a3b8]">
          {t("maxFileSize")}
        </p>
      </div>
    </Card>
  );
});

UploadZone.displayName = 'UploadZone';

export default UploadZone;

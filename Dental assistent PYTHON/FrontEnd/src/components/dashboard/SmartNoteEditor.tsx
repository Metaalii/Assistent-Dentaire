import React from "react";
import { useLanguage } from "../../i18n";
import { Card, CardHeader, CardBody, Button, Badge } from "../ui";
import {
  DocumentIcon,
  SparklesIcon,
  DownloadIcon,
  MicrophoneIcon,
} from "../ui/Icons";

interface SmartNoteEditorProps {
  document: string;
  originalDocument: string | null;
  isRagEnhanced: boolean;
  isSaved: boolean;
  onDocumentChange: (value: string) => void;
  onExportPDF: () => void;
  onRestoreOriginal: () => void;
  onNewRecording: () => void;
}

const SmartNoteEditor: React.FC<SmartNoteEditorProps> = ({
  document,
  originalDocument,
  isRagEnhanced,
  isSaved,
  onDocumentChange,
  onExportPDF,
  onRestoreOriginal,
  onNewRecording,
}) => {
  const { t } = useLanguage();

  return (
    <section className="animate-fade-in-up">
      <Card className="overflow-hidden">
        <CardHeader icon={<DocumentIcon className="text-white" size={20} />}>
          <div className="flex items-center gap-3">
            <div>
              <h2 className="font-semibold text-[#1e293b] dark:text-white">{t("generatedDocument")}</h2>
              <p className="text-xs text-[#64748b] dark:text-[#94a3b8]">{t("editableBeforeExport")}</p>
            </div>
            {isRagEnhanced && (
              <Badge variant="success">
                <SparklesIcon size={12} />
                {t("ragEnhanced")}
              </Badge>
            )}
            {isSaved && (
              <Badge variant="neutral">
                {t("consultationSaved")}
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardBody>
          <textarea
            value={document}
            onChange={(e) => onDocumentChange(e.target.value)}
            className="w-full h-96 p-4 border-2 border-[#e2e8f0] dark:border-[#334155] rounded-xl bg-white dark:bg-[#0f172a] text-[#1e293b] dark:text-[#e2e8f0] font-mono text-sm leading-relaxed resize-y focus:border-[#2d96c6] focus:ring-2 focus:ring-[#2d96c6]/20 outline-none"
            placeholder={String(t("documentPlaceholder"))}
          />
        </CardBody>
      </Card>

      {/* Quick actions */}
      <div className="mt-6 flex flex-wrap justify-center gap-4">
        <Button
          variant="primary"
          onClick={onExportPDF}
          leftIcon={<DownloadIcon size={18} />}
        >
          {t("exportPDF")}
        </Button>
        <Button
          variant="secondary"
          onClick={() => navigator.clipboard.writeText(document)}
        >
          {t("copyDocument")}
        </Button>
        {originalDocument && document !== originalDocument && (
          <Button
            variant="ghost"
            onClick={onRestoreOriginal}
          >
            {t("restoreOriginal")}
          </Button>
        )}
        <Button
          variant="ghost"
          onClick={onNewRecording}
          leftIcon={<MicrophoneIcon size={18} />}
        >
          {t("newRecording")}
        </Button>
      </div>
    </section>
  );
};

export default SmartNoteEditor;

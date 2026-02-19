import React from "react";
import { useLanguage } from "../../i18n";
import { Card, CardHeader, CardBody, Skeleton } from "../ui";
import {
  WaveformIcon,
  SparklesIcon,
  DocumentIcon,
} from "../ui/Icons";

const ProcessingIndicator: React.FC = React.memo(() => {
  const { t } = useLanguage();

  return (
    <div className="space-y-6">
      {/* Processing steps indicator */}
      <div className="flex items-center justify-center gap-8">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#2d96c6] to-[#1e7aa8] flex items-center justify-center">
            <WaveformIcon className="text-white" size={16} />
          </div>
          <span className="text-sm font-medium text-[#2d96c6]">{t("transcribingStep")}</span>
        </div>
        <div className="w-8 h-0.5 bg-[#e2e8f0] dark:bg-[#334155] rounded" />
        <div className="flex items-center gap-2 opacity-50">
          <div className="w-8 h-8 rounded-lg bg-[#e2e8f0] dark:bg-[#334155] flex items-center justify-center">
            <SparklesIcon className="text-[#94a3b8]" size={16} />
          </div>
          <span className="text-sm font-medium text-[#94a3b8]">{t("summarizingStep")}</span>
        </div>
      </div>

      {/* Skeleton preview of the document card */}
      <Card>
        <CardHeader icon={<DocumentIcon className="text-white" size={20} />}>
          <div>
            <Skeleton width="60%" height={16} />
            <Skeleton className="mt-2" width="40%" height={12} />
          </div>
        </CardHeader>
        <CardBody>
          <div className="space-y-3">
            <Skeleton width="100%" height={14} />
            <Skeleton width="95%" height={14} />
            <Skeleton width="88%" height={14} />
            <Skeleton width="92%" height={14} />
            <div className="pt-2" />
            <Skeleton width="100%" height={14} />
            <Skeleton width="80%" height={14} />
            <Skeleton width="96%" height={14} />
            <Skeleton width="70%" height={14} />
          </div>
        </CardBody>
      </Card>
    </div>
  );
});

ProcessingIndicator.displayName = 'ProcessingIndicator';

export default ProcessingIndicator;

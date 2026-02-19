import React from "react";
import { useLanguage } from "../../i18n";
import { Card, CardHeader, CardBody } from "../ui";
import { SparklesIcon } from "../ui/Icons";

interface StreamingPreviewProps {
  content: string;
}

const StreamingPreview: React.FC<StreamingPreviewProps> = ({ content }) => {
  const { t } = useLanguage();

  return (
    <section className="animate-fade-in">
      <Card className="overflow-hidden">
        <CardHeader icon={<SparklesIcon className="text-white" size={20} />}>
          <div className="flex items-center gap-3">
            <div>
              <h2 className="font-semibold text-[#1e293b] dark:text-white">{t("generatingSmartNote")}</h2>
              <p className="text-xs text-[#64748b] dark:text-[#94a3b8]">{t("aiWriting")}</p>
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
          <div className="min-h-[200px] p-4 bg-[#f8fafc] dark:bg-[#0f172a] rounded-xl border-2 border-[#e2e8f0] dark:border-[#334155]">
            <pre className="whitespace-pre-wrap text-[#1e293b] dark:text-[#e2e8f0] font-mono text-sm leading-relaxed">
              {content}
              <span className="inline-block w-2 h-4 bg-[#2d96c6] animate-pulse ml-1" />
            </pre>
          </div>
        </CardBody>
      </Card>
    </section>
  );
};

export default StreamingPreview;

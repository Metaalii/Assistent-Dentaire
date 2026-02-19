import React from "react";
import { useLanguage, useTheme } from "../../i18n";
import { Button, Badge, Container } from "../ui";
import {
  ToothIcon,
  HeartPulseIcon,
  DocumentIcon,
  XIcon,
  SunIcon,
  MoonIcon,
} from "../ui/Icons";

interface HeaderProps {
  onClear: () => void;
  hasContent: boolean;
  onViewHistory?: () => void;
}

const Header: React.FC<HeaderProps> = React.memo(({
  onClear,
  hasContent,
  onViewHistory,
}) => {
  const { t } = useLanguage();
  const { resolvedTheme, toggleTheme } = useTheme();

  return (
    <header className="sticky top-0 z-50 bg-white/80 dark:bg-[#1e293b]/80 backdrop-blur-xl border-b border-[#e2e8f0] dark:border-[#334155] shadow-sm">
      <Container>
        <div className="flex items-center justify-between py-4">
          {/* Logo and title */}
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#2d96c6] to-[#28b5ad] shadow-lg shadow-[#2d96c6]/30 flex items-center justify-center">
                <ToothIcon className="text-white" size={24} />
              </div>
              <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-white dark:bg-[#1e293b] shadow-md flex items-center justify-center">
                <HeartPulseIcon className="text-[#28b5ad]" size={12} />
              </div>
            </div>
            <div>
              <h1 className="text-xl font-bold text-[#1e293b] dark:text-white">{t("appName")}</h1>
              <p className="text-sm text-[#64748b] dark:text-[#94a3b8]">{t("aiPoweredDocumentation")}</p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3">
            <Badge variant="success">
              <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse" />
              {t("online")}
            </Badge>
            {onViewHistory && (
              <Button
                variant="secondary"
                size="sm"
                onClick={onViewHistory}
                leftIcon={<DocumentIcon size={16} />}
              >
                {t("viewHistory")}
              </Button>
            )}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg bg-[#f1f5f9] dark:bg-[#334155] text-[#64748b] dark:text-[#94a3b8] hover:bg-[#e2e8f0] dark:hover:bg-[#475569] transition-colors"
              title={resolvedTheme === "dark" ? String(t("lightMode")) : String(t("darkMode"))}
            >
              {resolvedTheme === "dark" ? <SunIcon size={18} /> : <MoonIcon size={18} />}
            </button>
            {hasContent && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClear}
                leftIcon={<XIcon size={16} />}
              >
                {t("clear")}
              </Button>
            )}
          </div>
        </div>
      </Container>
    </header>
  );
});

Header.displayName = 'Header';

export default Header;

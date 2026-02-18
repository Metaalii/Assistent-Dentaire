import React from "react";
import { useLanguage } from "../i18n";
import { Language } from "../i18n/translations";
import { ToothIcon, HeartPulseIcon } from "./ui/Icons";
import { Button } from "./ui";
import flagUkUrl from "../assets/flags/flag-uk.svg";
import flagFranceUrl from "../assets/flags/flag-france.svg";

interface LanguageSelectorProps {
  onComplete: () => void;
}

const LanguageSelector: React.FC<LanguageSelectorProps> = ({ onComplete }) => {
  const { language, setLanguage, t } = useLanguage();

  const handleSelect = (lang: Language) => {
    setLanguage(lang);
  };

  const handleContinue = () => {
    onComplete();
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#f8fafc] via-[#f0f7fc] to-[#effcfb] dark:from-[#0f172a] dark:via-[#1e293b] dark:to-[#0f172a] relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-[#2d96c6]/20 to-[#28b5ad]/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-tr from-[#28b5ad]/20 to-[#2d96c6]/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: "1s" }} />
      </div>

      {/* Main content */}
      <div className="relative z-10 flex flex-col items-center gap-8 p-8 max-w-lg w-full mx-4">
        {/* Logo */}
        <div className="relative">
          <div className="absolute inset-0 w-24 h-24 rounded-full bg-gradient-to-r from-[#2d96c6] to-[#28b5ad] blur-xl opacity-30 animate-pulse" />
          <div className="relative w-24 h-24 rounded-2xl bg-gradient-to-br from-[#2d96c6] to-[#28b5ad] shadow-2xl shadow-[#2d96c6]/30 flex items-center justify-center">
            <ToothIcon className="text-white" size={48} />
          </div>
          <div className="absolute -bottom-1 -right-1 w-8 h-8 rounded-full bg-white dark:bg-[#1e293b] shadow-lg flex items-center justify-center">
            <HeartPulseIcon className="text-[#28b5ad] animate-pulse" size={16} />
          </div>
        </div>

        {/* Title */}
        <div className="text-center">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-[#1e293b] via-[#334155] to-[#1e293b] dark:from-white dark:via-[#94a3b8] dark:to-white bg-clip-text text-transparent">
            {t("selectLanguage")}
          </h1>
          <p className="mt-2 text-[#64748b] dark:text-[#94a3b8]">
            {t("languageSubtitle")}
          </p>
        </div>

        {/* Language options */}
        <div className="w-full space-y-3">
          {/* English */}
          <button
            onClick={() => handleSelect("en")}
            className={`w-full flex items-center gap-4 p-4 rounded-xl border-2 transition-all duration-300 ${
              language === "en"
                ? "border-[#2d96c6] bg-[#2d96c6]/5 dark:bg-[#2d96c6]/10 shadow-lg shadow-[#2d96c6]/10"
                : "border-[#e2e8f0] dark:border-[#334155] bg-white/80 dark:bg-[#1e293b]/80 hover:border-[#2d96c6]/50 hover:bg-white dark:hover:bg-[#1e293b]"
            }`}
          >
            <div className="w-12 h-8 rounded overflow-hidden shadow-sm flex items-center justify-center bg-gray-100 dark:bg-[#334155]">
              <img src={flagUkUrl} alt="UK flag" width="32" height="16" />
            </div>
            <div className="flex-1 text-left">
              <p className={`font-semibold ${language === "en" ? "text-[#2d96c6]" : "text-[#1e293b] dark:text-[#e2e8f0]"}`}>
                English
              </p>
              <p className="text-sm text-[#64748b] dark:text-[#94a3b8]">United Kingdom</p>
            </div>
            {language === "en" && (
              <div className="w-6 h-6 rounded-full bg-[#2d96c6] flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            )}
          </button>

          {/* French */}
          <button
            onClick={() => handleSelect("fr")}
            className={`w-full flex items-center gap-4 p-4 rounded-xl border-2 transition-all duration-300 ${
              language === "fr"
                ? "border-[#2d96c6] bg-[#2d96c6]/5 dark:bg-[#2d96c6]/10 shadow-lg shadow-[#2d96c6]/10"
                : "border-[#e2e8f0] dark:border-[#334155] bg-white/80 dark:bg-[#1e293b]/80 hover:border-[#2d96c6]/50 hover:bg-white dark:hover:bg-[#1e293b]"
            }`}
          >
            <div className="w-12 h-8 rounded overflow-hidden shadow-sm flex items-center justify-center bg-gray-100 dark:bg-[#334155]">
              <img src={flagFranceUrl} alt="France flag" width="32" height="21" />
            </div>
            <div className="flex-1 text-left">
              <p className={`font-semibold ${language === "fr" ? "text-[#2d96c6]" : "text-[#1e293b] dark:text-[#e2e8f0]"}`}>
                Français
              </p>
              <p className="text-sm text-[#64748b] dark:text-[#94a3b8]">France</p>
            </div>
            {language === "fr" && (
              <div className="w-6 h-6 rounded-full bg-[#2d96c6] flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            )}
          </button>
        </div>

        {/* Continue button */}
        <Button
          variant="primary"
          onClick={handleContinue}
          className="w-full mt-4"
        >
          {t("continue")}
        </Button>

        {/* Version badge */}
        <div className="mt-4">
          <div className="px-4 py-2 rounded-full bg-white/80 dark:bg-[#1e293b]/80 backdrop-blur-sm border border-[#e2e8f0] dark:border-[#334155] shadow-sm">
            <span className="text-sm text-[#64748b] dark:text-[#94a3b8] font-medium">{t("version")}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LanguageSelector;

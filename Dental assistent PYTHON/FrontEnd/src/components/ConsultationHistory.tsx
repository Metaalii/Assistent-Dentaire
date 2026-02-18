import React, { useCallback, useEffect, useState } from "react";
import { searchConsultations, getRAGStatus, type ConsultationResult, type RAGStatus } from "../api";
import { useLanguage, useTheme } from "../i18n";
import {
  Button,
  Card,
  CardBody,
  Alert,
  Badge,
  Skeleton,
  Container,
} from "./ui";
import {
  ToothIcon,
  DocumentIcon,
  SparklesIcon,
  XIcon,
  HeartPulseIcon,
  SunIcon,
  MoonIcon,
} from "./ui/Icons";

// Search icon (magnifying glass)
const SearchIcon: React.FC<{ className?: string; size?: number }> = ({
  className = "",
  size = 24,
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    className={className}
    xmlns="http://www.w3.org/2000/svg"
  >
    <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2" />
    <path d="M21 21L16.65 16.65" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

// Clock icon for date display
const ClockIcon: React.FC<{ className?: string; size?: number }> = ({
  className = "",
  size = 24,
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    className={className}
    xmlns="http://www.w3.org/2000/svg"
  >
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
    <path d="M12 6V12L16 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

// Arrow left icon for back button
const ArrowLeftIcon: React.FC<{ className?: string; size?: number }> = ({
  className = "",
  size = 24,
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    className={className}
    xmlns="http://www.w3.org/2000/svg"
  >
    <path d="M19 12H5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    <path d="M12 19L5 12L12 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

// Database icon for RAG stats
const DatabaseIcon: React.FC<{ className?: string; size?: number }> = ({
  className = "",
  size = 24,
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    className={className}
    xmlns="http://www.w3.org/2000/svg"
  >
    <ellipse cx="12" cy="5" rx="9" ry="3" stroke="currentColor" strokeWidth="2" />
    <path d="M21 12C21 13.66 16.97 15 12 15C7.03 15 3 13.66 3 12" stroke="currentColor" strokeWidth="2" />
    <path d="M3 5V19C3 20.66 7.03 22 12 22C16.97 22 21 20.66 21 19V5" stroke="currentColor" strokeWidth="2" />
  </svg>
);

interface ConsultationHistoryProps {
  onBack: () => void;
}

export default function ConsultationHistory({ onBack }: ConsultationHistoryProps) {
  const { t } = useLanguage();
  const { resolvedTheme, toggleTheme } = useTheme();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ConsultationResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ragStatus, setRagStatus] = useState<RAGStatus | null>(null);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  // Load RAG status and recent consultations on mount
  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const status = await getRAGStatus();
        if (!cancelled) setRagStatus(status);

        // Load recent consultations (empty query returns most recent)
        if (status.available && status.consultations_count > 0) {
          const recent = await searchConsultations("consultation dentaire", 20);
          if (!cancelled) setResults(recent.results);
        }
      } catch (err) {
        console.error("Failed to load RAG status:", err);
      }
    })();

    return () => { cancelled = true; };
  }, []);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    setError(null);
    setHasSearched(true);
    setExpandedIndex(null);

    try {
      const response = await searchConsultations(query.trim(), 20);
      setResults(response.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [query]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") handleSearch();
    },
    [handleSearch]
  );

  const formatScore = (score: number): string => {
    return `${Math.round(score * 100)}%`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f8fafc] via-[#f0f7fc] to-[#f8fafc] dark:from-[#0f172a] dark:via-[#1e293b] dark:to-[#0f172a]">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 dark:bg-[#1e293b]/80 backdrop-blur-xl border-b border-[#e2e8f0] dark:border-[#334155] shadow-sm">
        <Container>
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={onBack}
                leftIcon={<ArrowLeftIcon size={16} />}
              >
                {t("backToDashboard")}
              </Button>
              <div className="h-6 w-px bg-[#e2e8f0] dark:bg-[#334155]" />
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#8b5cf6] to-[#6d28d9] shadow-lg shadow-[#8b5cf6]/30 flex items-center justify-center">
                  <ClockIcon className="text-white" size={20} />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-[#1e293b] dark:text-white">
                    {t("consultationHistory")}
                  </h1>
                  <p className="text-xs text-[#64748b] dark:text-[#94a3b8]">
                    {t("consultationHistoryDesc")}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {/* RAG stats badges */}
              {ragStatus?.available && (
                <>
                  <Badge variant="neutral">
                    <DatabaseIcon size={12} />
                    {ragStatus.consultations_count} {t("consultationCount")}
                  </Badge>
                  <Badge variant="success">
                    <SparklesIcon size={12} />
                    {ragStatus.knowledge_count} {t("knowledgeCount")}
                  </Badge>
                </>
              )}
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg bg-[#f1f5f9] dark:bg-[#334155] text-[#64748b] dark:text-[#94a3b8] hover:bg-[#e2e8f0] dark:hover:bg-[#475569] transition-colors"
                title={resolvedTheme === "dark" ? String(t("lightMode")) : String(t("darkMode"))}
              >
                {resolvedTheme === "dark" ? <SunIcon size={18} /> : <MoonIcon size={18} />}
              </button>
            </div>
          </div>
        </Container>
      </header>

      <main className="py-8">
        <Container size="lg">
          <div className="space-y-6">
            {/* Search bar */}
            <Card>
              <CardBody>
                <div className="flex gap-3">
                  <div className="flex-1 relative">
                    <SearchIcon
                      className="absolute left-4 top-1/2 -translate-y-1/2 text-[#94a3b8]"
                      size={20}
                    />
                    <input
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder={String(t("searchPlaceholder"))}
                      className="w-full pl-12 pr-4 py-3 border-2 border-[#e2e8f0] dark:border-[#334155] rounded-xl bg-white dark:bg-[#0f172a] text-[#1e293b] dark:text-[#e2e8f0] placeholder-[#94a3b8] focus:border-[#8b5cf6] focus:ring-2 focus:ring-[#8b5cf6]/20 outline-none transition-colors"
                    />
                  </div>
                  <Button
                    variant="primary"
                    onClick={handleSearch}
                    disabled={isSearching || !query.trim()}
                    leftIcon={<SearchIcon size={18} />}
                    className="bg-gradient-to-r from-[#8b5cf6] to-[#6d28d9] hover:from-[#7c3aed] hover:to-[#5b21b6]"
                  >
                    {t("search")}
                  </Button>
                </div>
              </CardBody>
            </Card>

            {/* Error */}
            {error && (
              <Alert variant="error" icon={<XIcon size={18} />}>
                {error}
              </Alert>
            )}

            {/* Loading */}
            {isSearching && (
              <div className="space-y-4">
                {[0, 1, 2].map((i) => (
                  <Card key={i}>
                    <CardBody>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 space-y-3">
                          <div className="flex items-center gap-3">
                            <Skeleton width={120} height={14} />
                            <Skeleton width={80} height={22} variant="rectangular" />
                          </div>
                          <Skeleton width="100%" height={14} />
                          <Skeleton width="95%" height={14} />
                          <Skeleton width="75%" height={14} />
                        </div>
                        <Skeleton width={90} height={32} variant="rectangular" />
                      </div>
                    </CardBody>
                  </Card>
                ))}
              </div>
            )}

            {/* No results message */}
            {!isSearching && hasSearched && results.length === 0 && (
              <Card>
                <CardBody className="py-16">
                  <div className="flex flex-col items-center text-center">
                    <div className="w-16 h-16 rounded-2xl bg-[#f1f5f9] dark:bg-[#334155] flex items-center justify-center mb-4">
                      <SearchIcon className="text-[#94a3b8]" size={32} />
                    </div>
                    <h3 className="text-lg font-semibold text-[#1e293b] dark:text-white mb-2">
                      {t("noResults")}
                    </h3>
                    <p className="text-[#64748b] dark:text-[#94a3b8] max-w-md">
                      {t("noResultsDesc")}
                    </p>
                  </div>
                </CardBody>
              </Card>
            )}

            {/* Empty state (no search yet and no consultations) */}
            {!isSearching && !hasSearched && results.length === 0 && (
              <Card>
                <CardBody className="py-16">
                  <div className="flex flex-col items-center text-center">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#8b5cf6]/20 to-[#6d28d9]/20 flex items-center justify-center mb-4">
                      <DocumentIcon className="text-[#8b5cf6]" size={32} />
                    </div>
                    <h3 className="text-lg font-semibold text-[#1e293b] dark:text-white mb-2">
                      {t("noHistory")}
                    </h3>
                    <p className="text-[#64748b] dark:text-[#94a3b8] max-w-md">
                      {t("noHistoryDesc")}
                    </p>
                  </div>
                </CardBody>
              </Card>
            )}

            {/* Results list */}
            {!isSearching && results.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-[#1e293b] dark:text-white">
                    {hasSearched ? t("searchResults") : t("recentConsultations")}
                  </h2>
                  <Badge variant="neutral">
                    {results.length} {t("consultationCount")}
                  </Badge>
                </div>

                {results.map((result, index) => (
                  <Card
                    key={`${result.date}-${index}`}
                    hover
                    className="transition-all duration-200"
                  >
                    <CardBody>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          {/* Date and score */}
                          <div className="flex items-center gap-3 mb-2">
                            <div className="flex items-center gap-1.5 text-sm text-[#64748b] dark:text-[#94a3b8]">
                              <ClockIcon size={14} />
                              <span>{result.date_display || result.date}</span>
                            </div>
                            {hasSearched && result.score > 0 && (
                              <Badge
                                variant={result.score > 0.7 ? "success" : result.score > 0.4 ? "warning" : "neutral"}
                              >
                                {t("relevanceScore")}: {formatScore(result.score)}
                              </Badge>
                            )}
                            {result.dentist_name && (
                              <Badge variant="neutral">
                                <ToothIcon size={12} />
                                {result.dentist_name}
                              </Badge>
                            )}
                          </div>

                          {/* SmartNote preview */}
                          <div
                            className={`text-sm text-[#475569] dark:text-[#cbd5e1] leading-relaxed ${
                              expandedIndex === index ? "" : "line-clamp-3"
                            }`}
                          >
                            <pre className="whitespace-pre-wrap font-sans">
                              {result.smartnote}
                            </pre>
                          </div>
                        </div>

                        {/* Expand/collapse button */}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            setExpandedIndex(expandedIndex === index ? null : index)
                          }
                        >
                          {expandedIndex === index ? t("closeNote") : t("viewFullNote")}
                        </Button>
                      </div>

                      {/* Expanded: show transcription if available */}
                      {expandedIndex === index && result.transcription && (
                        <div className="mt-4 pt-4 border-t border-[#e2e8f0] dark:border-[#334155]">
                          <h4 className="text-sm font-semibold text-[#64748b] dark:text-[#94a3b8] mb-2">
                            Transcription
                          </h4>
                          <p className="text-sm text-[#94a3b8] dark:text-[#64748b] leading-relaxed whitespace-pre-wrap">
                            {result.transcription}
                          </p>
                        </div>
                      )}
                    </CardBody>
                  </Card>
                ))}
              </div>
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
    </div>
  );
}

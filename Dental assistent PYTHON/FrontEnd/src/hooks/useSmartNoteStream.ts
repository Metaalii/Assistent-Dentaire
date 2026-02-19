import { useCallback, useState } from "react";
import { summarizeTextStreamRAG, transcribeAudio, saveConsultation } from "../api";
import { useProfile } from "./useProfile";
import { useLanguage } from "../i18n";

const ALLOWED_EXTS = new Set(["wav", "mp3", "m4a", "ogg", "webm", "mp4"]);

function getExt(name: string) {
  const parts = name.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
}

export interface SmartNoteStreamState {
  fileName: string | null;
  isLoading: boolean;
  isStreaming: boolean;
  error: string | null;
  transcript: string | null;
  document: string | null;
  originalDocument: string | null;
  streamingContent: string;
  isRagEnhanced: boolean;
  isSaved: boolean;
  hasContent: boolean;
  setDocument: (doc: string) => void;
  processFile: (file: File) => void;
  clearAll: () => void;
  restoreOriginal: () => void;
  validateFile: (file: File) => boolean;
}

export function useSmartNoteStream(): SmartNoteStreamState {
  const { language } = useLanguage();
  const { profile, getDocumentHeader, getDocumentFooter } = useProfile();

  const [fileName, setFileName] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [document, setDocument] = useState<string | null>(null);
  const [originalDocument, setOriginalDocument] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState<string>("");
  const [isRagEnhanced, setIsRagEnhanced] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  const validateFile = useCallback((file: File): boolean => {
    return ALLOWED_EXTS.has(getExt(file.name));
  }, []);

  const processFile = useCallback(async (file: File) => {
    if (!validateFile(file)) {
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
    setIsRagEnhanced(false);
    setIsSaved(false);

    try {
      const tr = await transcribeAudio(file, language);
      setTranscript(tr.text);

      setIsLoading(false);
      setIsStreaming(true);

      const transcriptionText = tr.text;

      await summarizeTextStreamRAG(
        transcriptionText,
        (chunk) => {
          setStreamingContent((prev) => prev + chunk);
        },
        (fullText) => {
          const fullDocument = `${getDocumentHeader(language)}

${fullText}

${getDocumentFooter(language)}`;
          setDocument(fullDocument);
          setOriginalDocument(fullDocument);
          setIsStreaming(false);
          setStreamingContent("");

          saveConsultation({
            smartnote: fullText,
            transcription: transcriptionText,
            dentist_name: profile?.name || "",
          }).then(() => {
            setIsSaved(true);
          }).catch((err) => {
            console.warn("Failed to save consultation to history:", err);
          });
        },
        (ragEnhanced) => {
          setIsRagEnhanced(ragEnhanced);
        },
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
  }, [getDocumentHeader, getDocumentFooter, profile, language, validateFile]);

  const clearAll = useCallback(() => {
    setFileName(null);
    setError(null);
    setTranscript(null);
    setDocument(null);
    setOriginalDocument(null);
  }, []);

  const restoreOriginal = useCallback(() => {
    if (originalDocument) {
      setDocument(originalDocument);
    }
  }, [originalDocument]);

  const hasContent = !!(transcript || document || error || isStreaming);

  return {
    fileName,
    isLoading,
    isStreaming,
    error,
    transcript,
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
  };
}

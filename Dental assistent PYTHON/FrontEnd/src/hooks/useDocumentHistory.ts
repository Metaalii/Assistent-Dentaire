import { useState, useCallback, useEffect } from 'react';

/**
 * Document history entry interface
 */
export interface DocumentEntry {
  id: string;
  timestamp: number;
  fileName: string;
  transcript: string;
  document: string;
  patientName?: string;
}

const STORAGE_KEY = 'dental-assistant-document-history';
const MAX_HISTORY_ITEMS = 50;

/**
 * Hook for managing local document history
 * Stores documents in localStorage with automatic cleanup
 */
export function useDocumentHistory() {
  const [history, setHistory] = useState<DocumentEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load history from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Validate and filter corrupted entries
        const validEntries = parsed.filter(
          (entry: unknown): entry is DocumentEntry =>
            typeof entry === 'object' &&
            entry !== null &&
            'id' in entry &&
            'timestamp' in entry &&
            'document' in entry
        );
        setHistory(validEntries);
      }
    } catch (error) {
      console.error('Failed to load document history:', error);
      // Reset corrupted storage
      localStorage.removeItem(STORAGE_KEY);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Save history to localStorage whenever it changes
  const saveHistory = useCallback((newHistory: DocumentEntry[]) => {
    try {
      // Limit history size to prevent localStorage overflow
      const trimmedHistory = newHistory.slice(0, MAX_HISTORY_ITEMS);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmedHistory));
      setHistory(trimmedHistory);
    } catch (error) {
      console.error('Failed to save document history:', error);
      // If storage is full, remove oldest entries and retry
      if (error instanceof DOMException && error.name === 'QuotaExceededError') {
        const reducedHistory = newHistory.slice(0, Math.floor(MAX_HISTORY_ITEMS / 2));
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(reducedHistory));
          setHistory(reducedHistory);
        } catch {
          // Storage still full, clear all
          localStorage.removeItem(STORAGE_KEY);
          setHistory([]);
        }
      }
    }
  }, []);

  /**
   * Add a new document to history
   */
  const addDocument = useCallback((
    fileName: string,
    transcript: string,
    document: string,
    patientName?: string
  ): DocumentEntry => {
    const entry: DocumentEntry = {
      id: `doc-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      fileName,
      transcript,
      document,
      patientName,
    };

    const newHistory = [entry, ...history];
    saveHistory(newHistory);
    return entry;
  }, [history, saveHistory]);

  /**
   * Update an existing document
   */
  const updateDocument = useCallback((id: string, updates: Partial<Omit<DocumentEntry, 'id' | 'timestamp'>>) => {
    const newHistory = history.map(entry =>
      entry.id === id ? { ...entry, ...updates } : entry
    );
    saveHistory(newHistory);
  }, [history, saveHistory]);

  /**
   * Delete a document from history
   */
  const deleteDocument = useCallback((id: string) => {
    const newHistory = history.filter(entry => entry.id !== id);
    saveHistory(newHistory);
  }, [history, saveHistory]);

  /**
   * Clear all document history
   */
  const clearHistory = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setHistory([]);
  }, []);

  /**
   * Get a specific document by ID
   */
  const getDocument = useCallback((id: string): DocumentEntry | undefined => {
    return history.find(entry => entry.id === id);
  }, [history]);

  /**
   * Search documents by text content
   */
  const searchDocuments = useCallback((query: string): DocumentEntry[] => {
    if (!query.trim()) return history;

    const lowerQuery = query.toLowerCase();
    return history.filter(entry =>
      entry.document.toLowerCase().includes(lowerQuery) ||
      entry.transcript.toLowerCase().includes(lowerQuery) ||
      entry.fileName.toLowerCase().includes(lowerQuery) ||
      entry.patientName?.toLowerCase().includes(lowerQuery)
    );
  }, [history]);

  /**
   * Get documents from the last N days
   */
  const getRecentDocuments = useCallback((days: number = 7): DocumentEntry[] => {
    const cutoff = Date.now() - (days * 24 * 60 * 60 * 1000);
    return history.filter(entry => entry.timestamp >= cutoff);
  }, [history]);

  /**
   * Export history as JSON for backup
   */
  const exportHistory = useCallback((): string => {
    return JSON.stringify(history, null, 2);
  }, [history]);

  /**
   * Import history from JSON backup
   */
  const importHistory = useCallback((jsonString: string): boolean => {
    try {
      const imported = JSON.parse(jsonString);
      if (!Array.isArray(imported)) {
        throw new Error('Invalid format: expected array');
      }

      // Merge with existing history, avoiding duplicates by ID
      const existingIds = new Set(history.map(e => e.id));
      const newEntries = imported.filter(
        (entry: DocumentEntry) => !existingIds.has(entry.id)
      );

      const merged = [...newEntries, ...history].sort(
        (a, b) => b.timestamp - a.timestamp
      );
      saveHistory(merged);
      return true;
    } catch (error) {
      console.error('Failed to import history:', error);
      return false;
    }
  }, [history, saveHistory]);

  return {
    history,
    isLoading,
    addDocument,
    updateDocument,
    deleteDocument,
    clearHistory,
    getDocument,
    searchDocuments,
    getRecentDocuments,
    exportHistory,
    importHistory,
    totalCount: history.length,
  };
}

export default useDocumentHistory;

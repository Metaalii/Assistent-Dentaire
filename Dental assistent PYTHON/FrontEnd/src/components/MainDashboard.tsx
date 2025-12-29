import React, { useState, useCallback } from "react";
import { summarizeText, transcribeAudio } from "../api";

const ALLOWED_EXTS = new Set(["wav", "mp3", "m4a", "ogg"]);

function getExt(name: string) {
  const parts = name.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
}

export default function MainDashboard() {
  // keep your states...

  const processFile = async (file: File) => {
    const ext = getExt(file.name);
    if (!ALLOWED_EXTS.has(ext)) {
      setError("Please upload a valid audio file (WAV, MP3, M4A, OGG).");
      return;
    }

    setFileName(file.name);
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const tr = await transcribeAudio(file);
      // If you want SOAP:
      const sum = await summarizeText(tr.text);
      setResult(sum.summary);
      // Or if you want raw transcript:
      // setResult(tr.text);
    } catch (e) {
      console.error(e);
      setError(e instanceof Error ? e.message : "An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  // rest of your component unchanged
}

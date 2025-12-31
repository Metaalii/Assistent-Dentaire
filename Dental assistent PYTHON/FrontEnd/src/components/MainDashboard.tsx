import React, { useCallback, useRef, useState } from "react";
import { summarizeText, transcribeAudio } from "../api";

const ALLOWED_EXTS = new Set(["wav", "mp3", "m4a", "ogg"]);

function getExt(name: string) {
  const parts = name.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
}

export default function MainDashboard() {
  const [fileName, setFileName] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement | null>(null);

  const processFile = async (file: File) => {
    const ext = getExt(file.name);
    if (!ALLOWED_EXTS.has(ext)) {
      setError("Please upload a valid audio file (WAV, MP3, M4A, OGG).");
      return;
    }

    setFileName(file.name);
    setIsLoading(true);
    setError(null);
    setTranscript(null);
    setSummary(null);

    try {
      const tr = await transcribeAudio(file);
      setTranscript(tr.text);

      const sum = await summarizeText(tr.text);
      setSummary(sum.summary);
    } catch (e) {
      console.error(e);
      setError(e instanceof Error ? e.message : "An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const onFileChange = (evt: React.ChangeEvent<HTMLInputElement>) => {
    const file = evt.target.files?.[0];
    if (file) {
      void processFile(file);
      evt.target.value = ""; // reset for next upload
    }
  };

  const onDrop = useCallback(
    (evt: React.DragEvent<HTMLDivElement>) => {
      evt.preventDefault();
      const file = evt.dataTransfer.files?.[0];
      if (file) void processFile(file);
    },
    []
  );

  const onDragOver = useCallback((evt: React.DragEvent<HTMLDivElement>) => {
    evt.preventDefault();
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Dental Assistant</h1>
            <p className="text-sm text-slate-600">Upload an audio note to transcribe and summarize.</p>
          </div>
          <button
            className="rounded border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-white"
            onClick={() => {
              setFileName(null);
              setError(null);
              setTranscript(null);
              setSummary(null);
            }}
          >
            Clear
          </button>
        </header>

        <div
          className="flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-slate-300 bg-white p-8 text-center shadow-sm hover:border-blue-400"
          onDrop={onDrop}
          onDragOver={onDragOver}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
          }}
        >
          <div className="text-lg font-semibold text-slate-900">Drop an audio file or click to browse</div>
          <div className="text-sm text-slate-600">Allowed: WAV, MP3, M4A, OGG. Max 10 MB.</div>
          <button className="mt-2 rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700">Choose file</button>
          {fileName && <div className="text-sm text-slate-700">Selected: {fileName}</div>}
          <input
            ref={inputRef}
            type="file"
            accept=".wav,.mp3,.m4a,.ogg"
            className="hidden"
            onChange={onFileChange}
          />
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
        )}

        {isLoading && (
          <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="h-3 w-3 animate-ping rounded-full bg-blue-500" aria-hidden />
            <div className="text-slate-800 font-medium">Processing audio… this may take a moment.</div>
          </div>
        )}

        {(transcript || summary) && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Transcript</h2>
              <p className="mt-2 whitespace-pre-wrap text-slate-800 text-sm">
                {transcript || "Pending…"}
              </p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Summary</h2>
              <p className="mt-2 whitespace-pre-wrap text-slate-800 text-sm">
                {summary || "Generating summary…"}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

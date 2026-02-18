/**
 * Centralized error handling for the Dental Assistant frontend.
 *
 * Maps backend error codes to user-facing messages and provides
 * structured error types for consistent handling across components.
 *
 * Error codes follow the pattern: DOMAIN_NNN
 * - AUTH_*        : Authentication errors
 * - INPUT_*       : Input validation errors
 * - MODEL_*       : Model availability errors
 * - INFERENCE_*   : LLM / Whisper inference errors
 * - DOWNLOAD_*    : Model download errors
 * - SYSTEM_*      : Server-level errors
 */

// ---------------------------------------------------------------------------
// Structured error response from the backend
// ---------------------------------------------------------------------------

export interface BackendErrorBody {
  error_code: string;
  message: string;
  detail?: string | null;
  request_id?: string;
}

// ---------------------------------------------------------------------------
// Application error class
// ---------------------------------------------------------------------------

export class AppError extends Error {
  /** Machine-readable error code (e.g. "MODEL_001") */
  readonly code: string;
  /** Human-readable description from the backend */
  readonly backendMessage: string;
  /** Optional extra context (file path, allowed values, etc.) */
  readonly detail: string | null;
  /** Correlation ID for debugging */
  readonly requestId: string | null;
  /** HTTP status code */
  readonly status: number;

  constructor(status: number, body: BackendErrorBody) {
    super(body.message);
    this.name = "AppError";
    this.code = body.error_code;
    this.backendMessage = body.message;
    this.detail = body.detail ?? null;
    this.requestId = body.request_id ?? null;
    this.status = status;
  }

  /** True if this is a "model not downloaded" error (MODEL_001..MODEL_005). */
  get isModelError(): boolean {
    return this.code.startsWith("MODEL_");
  }

  /** True if this is an authentication error (AUTH_001..AUTH_003). */
  get isAuthError(): boolean {
    return this.code.startsWith("AUTH_");
  }

  /** True if the server is busy / overloaded (INFERENCE_001). */
  get isBusy(): boolean {
    return this.code === "INFERENCE_001";
  }

  /** True if this is a download failure (DOWNLOAD_002). */
  get isDownloadError(): boolean {
    return this.code.startsWith("DOWNLOAD_");
  }

  /** Formatted string for developer debugging. */
  toDebugString(): string {
    const parts = [`[${this.code}] ${this.backendMessage}`];
    if (this.detail) parts.push(`Detail: ${this.detail}`);
    if (this.requestId) parts.push(`Request ID: ${this.requestId}`);
    parts.push(`HTTP ${this.status}`);
    return parts.join(" | ");
  }
}

// ---------------------------------------------------------------------------
// Error code -> user-friendly description map
// Keyed by language so the UI can display localised guidance.
// ---------------------------------------------------------------------------

type ErrorGuidance = { title: string; hint: string };

const ERROR_GUIDANCE_FR: Record<string, ErrorGuidance> = {
  AUTH_001: { title: "Cle API manquante", hint: "Verifiez la configuration de l'en-tete X-API-Key." },
  AUTH_002: { title: "Cle API invalide", hint: "La cle envoyee ne correspond pas a celle du serveur." },
  AUTH_003: { title: "Configuration de securite", hint: "Definissez APP_API_KEY en mode production." },
  INPUT_001: { title: "Texte vide", hint: "Le texte fourni est vide ou invalide apres nettoyage." },
  INPUT_002: { title: "Nom de fichier manquant", hint: "Le fichier televerse n'a pas de nom." },
  INPUT_003: { title: "Extension non supportee", hint: "Formats acceptes : WAV, MP3, M4A, OGG, WEBM, MP4." },
  INPUT_004: { title: "Fichier trop volumineux", hint: "La taille maximale autorisee est de 100 Mo." },
  INPUT_005: { title: "En-tete malformee", hint: "L'en-tete Content-Length est invalide." },
  MODEL_001: { title: "Modele LLM non telecharge", hint: "Lancez la page de configuration pour telecharger le modele." },
  MODEL_002: { title: "Modele Whisper non telecharge", hint: "Lancez la page de configuration pour telecharger Whisper." },
  MODEL_003: { title: "Dossier Whisper vide", hint: "Les fichiers du modele Whisper sont absents. Re-telechargez." },
  MODEL_004: { title: "Dependance LLM manquante", hint: "Installez llama-cpp-python pour activer les resumes." },
  MODEL_005: { title: "Dependance Whisper manquante", hint: "Installez faster-whisper pour activer la transcription." },
  INFERENCE_001: { title: "Serveur occupe", hint: "Une autre requete est en cours. Reessayez dans quelques instants." },
  INFERENCE_002: { title: "Reponse LLM inattendue", hint: "Le modele a retourne un format imprevu. Verifiez les logs." },
  INFERENCE_003: { title: "Erreur de streaming", hint: "La generation en temps reel a echoue." },
  INFERENCE_004: { title: "Transcription echouee", hint: "La transcription audio a echoue. Verifiez le fichier audio." },
  DOWNLOAD_001: { title: "Telechargement en cours", hint: "Un telechargement est deja actif. Patientez." },
  DOWNLOAD_002: { title: "Echec du telechargement", hint: "Verifiez votre connexion internet et reessayez." },
  SYSTEM_001: { title: "Backend non pret", hint: "Le moteur IA local n'est pas encore demarre." },
  SYSTEM_002: { title: "Connexion interrompue", hint: "Le client s'est deconnecte avant la fin du traitement." },
  SYSTEM_003: { title: "Trop de requetes", hint: "Vous avez depasse la limite de requetes. Patientez." },
  SYSTEM_004: { title: "Erreur interne", hint: "Une erreur inattendue s'est produite cote serveur." },
};

const ERROR_GUIDANCE_EN: Record<string, ErrorGuidance> = {
  AUTH_001: { title: "Missing API key", hint: "Check the X-API-Key header configuration." },
  AUTH_002: { title: "Invalid API key", hint: "The key sent does not match the server key." },
  AUTH_003: { title: "Security configuration", hint: "Set APP_API_KEY in production mode." },
  INPUT_001: { title: "Empty text", hint: "The text provided is empty or invalid after cleaning." },
  INPUT_002: { title: "Missing filename", hint: "The uploaded file has no filename." },
  INPUT_003: { title: "Unsupported extension", hint: "Accepted formats: WAV, MP3, M4A, OGG, WEBM, MP4." },
  INPUT_004: { title: "File too large", hint: "Maximum allowed size is 100 MB." },
  INPUT_005: { title: "Malformed header", hint: "The Content-Length header is invalid." },
  MODEL_001: { title: "LLM model not downloaded", hint: "Run the setup page to download the model." },
  MODEL_002: { title: "Whisper model not downloaded", hint: "Run the setup page to download Whisper." },
  MODEL_003: { title: "Whisper folder empty", hint: "Whisper model files are missing. Re-download." },
  MODEL_004: { title: "LLM dependency missing", hint: "Install llama-cpp-python to enable summaries." },
  MODEL_005: { title: "Whisper dependency missing", hint: "Install faster-whisper to enable transcription." },
  INFERENCE_001: { title: "Server busy", hint: "Another request is being processed. Try again shortly." },
  INFERENCE_002: { title: "Unexpected LLM response", hint: "The model returned an unexpected format. Check logs." },
  INFERENCE_003: { title: "Streaming error", hint: "Real-time generation failed." },
  INFERENCE_004: { title: "Transcription failed", hint: "Audio transcription failed. Check the audio file." },
  DOWNLOAD_001: { title: "Download in progress", hint: "A download is already active. Please wait." },
  DOWNLOAD_002: { title: "Download failed", hint: "Check your internet connection and try again." },
  SYSTEM_001: { title: "Backend not ready", hint: "The local AI engine has not started yet." },
  SYSTEM_002: { title: "Connection interrupted", hint: "The client disconnected before processing finished." },
  SYSTEM_003: { title: "Too many requests", hint: "You've exceeded the request limit. Please wait." },
  SYSTEM_004: { title: "Internal error", hint: "An unexpected server error occurred." },
};

const GUIDANCE_MAP: Record<string, Record<string, ErrorGuidance>> = {
  fr: ERROR_GUIDANCE_FR,
  en: ERROR_GUIDANCE_EN,
};

/**
 * Get user-friendly error guidance for a given error code and language.
 */
export function getErrorGuidance(
  code: string,
  lang: string = "fr",
): ErrorGuidance {
  const map = GUIDANCE_MAP[lang] ?? GUIDANCE_MAP["fr"];
  return (
    map[code] ?? {
      title: lang === "fr" ? "Erreur inconnue" : "Unknown error",
      hint:
        lang === "fr"
          ? `Code: ${code}. Consultez les logs du serveur.`
          : `Code: ${code}. Check the server logs.`,
    }
  );
}

// ---------------------------------------------------------------------------
// Helper: parse backend error response into AppError
// ---------------------------------------------------------------------------

/**
 * Parse a non-OK fetch Response into an AppError.
 * Falls back gracefully if the body isn't structured JSON.
 */
export async function parseApiError(res: Response): Promise<AppError> {
  try {
    const body: BackendErrorBody = await res.json();
    if (body?.error_code) {
      return new AppError(res.status, body);
    }
    // Legacy format: { detail: "..." }
    const detail = typeof body === "object" && body !== null
      ? (body as Record<string, unknown>).detail
      : undefined;
    return new AppError(res.status, {
      error_code: "SYSTEM_004",
      message: typeof detail === "string" ? detail : res.statusText,
      detail: null,
    });
  } catch {
    return new AppError(res.status, {
      error_code: "SYSTEM_004",
      message: res.statusText || "Unknown error",
      detail: null,
    });
  }
}

// ---------------------------------------------------------------------------
// Helper: parse SSE error event into AppError
// ---------------------------------------------------------------------------

export interface SSEErrorData {
  error_code?: string;
  message?: string;
  error?: string;
  detail?: string;
}

/**
 * Parse an SSE error event payload into an AppError.
 */
export function parseSSEError(data: SSEErrorData): AppError {
  const code = data.error_code ?? "SYSTEM_004";
  const message = data.message ?? data.error ?? "Streaming error";
  return new AppError(0, {
    error_code: code,
    message,
    detail: data.detail ?? data.error ?? null,
  });
}

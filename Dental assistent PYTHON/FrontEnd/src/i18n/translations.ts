export type Language = "en" | "fr";

export const translations = {
  en: {
    // App
    appName: "Dental Assistant",
    appTagline: "Professional AI-Powered Care",
    version: "Version 1.0",

    // Language selector
    selectLanguage: "Select Language",
    languageSubtitle: "Choose your preferred language",
    continue: "Continue",
    english: "English",
    french: "Français",

    // Splash screen
    initializing: "Initializing system...",

    // Error screen
    connectionFailed: "Connection Failed",
    troubleshooting: "Troubleshooting:",
    troubleshootingTips: [
      "Check if the backend service is running",
      "Verify network connectivity",
      "Restart the application",
    ],
    tryAgain: "Try Again",

    // Model Setup
    setupTitle: "System Setup",
    setupSubtitle: "Let's configure your AI assistant",
    stepHardware: "Hardware Detection",
    stepDownload: "Model Download",
    stepReady: "Ready",

    // Hardware detection
    analyzingHardware: "Analyzing your system...",
    systemRequirements: "System Requirements",
    hardwareProfile: "Hardware Profile",
    cpuOnly: "CPU Only",
    lowVram: "Low VRAM GPU",
    highVram: "High VRAM GPU",
    recommendedModel: "Recommended Model",
    modelSize: "Model Size",
    estimatedRam: "Estimated RAM",
    downloadSize: "Download Size",
    optimal: "Optimal",

    // Download
    downloadAndContinue: "Download & Continue",
    downloading: "Downloading...",
    downloadingModel: "Downloading AI Model",
    downloadProgress: "This may take several minutes depending on your connection",
    skipDownload: "Skip for now",
    modelReady: "Model Ready",
    modelReadyDesc: "The AI model is already installed and ready to use.",
    continueToApp: "Continue to App",

    // Main Dashboard
    dashboard: "Dashboard",
    uploadAudio: "Upload Audio",
    uploadAudioDesc: "Drag and drop an audio file or click to browse",
    supportedFormats: "Supported formats: WAV, MP3, M4A, OGG (max 10MB)",
    processing: "Processing",
    processingAudio: "Processing your audio...",
    transcribing: "Transcribing audio content",
    transcription: "Transcription",
    transcriptionResult: "Transcription Result",
    analysis: "Analysis",
    analysisResult: "AI Analysis",
    analyzing: "Analyzing content...",
    copyToClipboard: "Copy to clipboard",
    copied: "Copied!",
    newRecording: "New Recording",

    // Errors
    processingError: "Processing Error",
    errorOccurred: "An error occurred",

    // Settings
    settings: "Settings",
    language: "Language",
  },

  fr: {
    // App
    appName: "Assistant Dentaire",
    appTagline: "Soins Professionnels Propulsés par l'IA",
    version: "Version 1.0",

    // Language selector
    selectLanguage: "Choisir la Langue",
    languageSubtitle: "Sélectionnez votre langue préférée",
    continue: "Continuer",
    english: "English",
    french: "Français",

    // Splash screen
    initializing: "Initialisation du système...",

    // Error screen
    connectionFailed: "Échec de Connexion",
    troubleshooting: "Dépannage :",
    troubleshootingTips: [
      "Vérifiez si le service backend est en cours d'exécution",
      "Vérifiez la connectivité réseau",
      "Redémarrez l'application",
    ],
    tryAgain: "Réessayer",

    // Model Setup
    setupTitle: "Configuration du Système",
    setupSubtitle: "Configurons votre assistant IA",
    stepHardware: "Détection Matérielle",
    stepDownload: "Téléchargement du Modèle",
    stepReady: "Prêt",

    // Hardware detection
    analyzingHardware: "Analyse de votre système...",
    systemRequirements: "Configuration Requise",
    hardwareProfile: "Profil Matériel",
    cpuOnly: "CPU Uniquement",
    lowVram: "GPU VRAM Faible",
    highVram: "GPU VRAM Élevée",
    recommendedModel: "Modèle Recommandé",
    modelSize: "Taille du Modèle",
    estimatedRam: "RAM Estimée",
    downloadSize: "Taille du Téléchargement",
    optimal: "Optimal",

    // Download
    downloadAndContinue: "Télécharger et Continuer",
    downloading: "Téléchargement...",
    downloadingModel: "Téléchargement du Modèle IA",
    downloadProgress: "Cela peut prendre plusieurs minutes selon votre connexion",
    skipDownload: "Passer pour l'instant",
    modelReady: "Modèle Prêt",
    modelReadyDesc: "Le modèle IA est déjà installé et prêt à l'emploi.",
    continueToApp: "Continuer vers l'Application",

    // Main Dashboard
    dashboard: "Tableau de Bord",
    uploadAudio: "Télécharger Audio",
    uploadAudioDesc: "Glissez-déposez un fichier audio ou cliquez pour parcourir",
    supportedFormats: "Formats supportés : WAV, MP3, M4A, OGG (max 10Mo)",
    processing: "Traitement",
    processingAudio: "Traitement de votre audio...",
    transcribing: "Transcription du contenu audio",
    transcription: "Transcription",
    transcriptionResult: "Résultat de la Transcription",
    analysis: "Analyse",
    analysisResult: "Analyse IA",
    analyzing: "Analyse en cours...",
    copyToClipboard: "Copier dans le presse-papiers",
    copied: "Copié !",
    newRecording: "Nouvel Enregistrement",

    // Errors
    processingError: "Erreur de Traitement",
    errorOccurred: "Une erreur s'est produite",

    // Settings
    settings: "Paramètres",
    language: "Langue",
  },
} as const;

export type TranslationKey = keyof typeof translations.en;

"""
Configuration centralisee pour l'optimisation LLM.

Ce fichier contient tous les parametres de performance pour:
- llama-cpp-python (LLM)
- faster-whisper (transcription)

Prompt format: Llama-3 Instruct chat template.
"""

import os


# ============================================
# LLAMA-3 INSTRUCT CHAT TEMPLATE
# ============================================
# <|begin_of_text|> is added automatically by llama.cpp as BOS token.
# Do NOT include it in prompt strings to avoid duplication.

def _llama3_prompt(system: str, user: str) -> str:
    """
    Build a Llama-3 Instruct chat-formatted prompt.

    The model expects this exact token structure to follow instructions
    properly. Without it, output quality degrades significantly.
    """
    return (
        f"<|start_header_id|>system<|end_header_id|>\n\n{system}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n{user}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
    )


# ============================================
# CONFIGURATION CONTEXTE LLM
# ============================================

# Contexte adapte aux SmartNotes dentaires
# Une consultation typique = 2000-3000 tokens
# SmartNote output = 300-500 tokens
# Marge de securite incluse
CONTEXT_LENGTH = 4096

# Longueur maximale de generation pour SmartNotes
MAX_GENERATION_TOKENS = 800

# Seuil pour activer le chunking (en tokens estimes)
CHUNKING_THRESHOLD = 3000

# Taille des chunks pour les longues transcriptions
CHUNK_SIZE_TOKENS = 2000


# ============================================
# CONFIGURATION THREADING
# ============================================

def get_optimal_threads() -> int:
    """
    Calcule le nombre optimal de threads CPU.

    Strategie: utiliser la moitie des cores pour laisser
    de la marge au systeme et a Whisper.
    """
    cpu_count = os.cpu_count() or 4
    # Minimum 4 threads, maximum moitie des cores
    return max(4, cpu_count // 2)


CPU_THREADS = get_optimal_threads()


# ============================================
# CONFIGURATION PAR PROFIL HARDWARE
# ============================================

# Batch sizes optimises par profil
BATCH_SIZES = {
    "high_vram": 512,   # GPU puissant: batch max
    "low_vram": 256,    # GPU limite: batch reduit
    "cpu_only": 128,    # CPU: batch minimal pour eviter saturation
}

# GPU layers pour Llama-3-8B (32 layers total + embeddings)
GPU_LAYERS = {
    "high_vram": 33,    # Toutes les couches sur GPU
    "low_vram": 24,     # ~75% sur GPU
    "cpu_only": 0,      # Tout sur CPU
}

# Layers specifiques pour Apple Silicon (memoire unifiee)
GPU_LAYERS_APPLE_SILICON = 33  # Offload total, memoire partagee


# ============================================
# PARAMETRES DE GENERATION
# ============================================

GENERATION_PARAMS = {
    "temperature": 0.3,      # Bas pour documents medicaux (deterministe)
    "top_p": 0.9,            # Nucleus sampling
    "top_k": 40,             # Limite vocabulaire considere
    "repeat_penalty": 1.1,   # Evite repetitions
}

# Stop tokens pour Llama-3 Instruct
STOP_TOKENS = ["<|eot_id|>", "<|end_of_text|>"]


# ============================================
# CONFIGURATION WHISPER
# ============================================

# Default language for transcription (can be overridden per-request)
WHISPER_DEFAULT_LANGUAGE = "fr"

WHISPER_CONFIG = {
    "vad_filter": True,                  # Filtrer silences (20-30% faster)
    "vad_parameters": {
        "min_silence_duration_ms": 500,  # Silences > 500ms ignores
        "speech_pad_ms": 200,            # Padding autour de la parole
    },
    "condition_on_previous_text": False, # Plus rapide, moins de contexte
    "compression_ratio_threshold": 2.4,  # Seuil qualite
    "log_prob_threshold": -1.0,          # Seuil probabilite
    "no_speech_threshold": 0.6,          # Seuil detection silence
}

# Workers Whisper par profil
WHISPER_WORKERS = {
    "high_vram": 4,
    "low_vram": 2,
    "cpu_only": 1,
}


# ============================================
# CONFIGURATION MEMOIRE
# ============================================

MEMORY_CONFIG = {
    "use_mlock": True,   # Verrouille modele en RAM (evite swap)
    "use_mmap": True,    # Memory-mapped loading (chargement efficace)
}


# ============================================
# PROMPTS OPTIMISES (Llama-3 Instruct format)
# ============================================

SMARTNOTE_PROMPT_OPTIMIZED = _llama3_prompt(
    system=(
        "Tu es un assistant de documentation dentaire. "
        "Tu generes des SmartNotes concises et structurees en francais "
        "a partir de transcriptions de consultations. "
        "Reponds uniquement avec la SmartNote au format demande, sans commentaires ni explications."
    ),
    user=(
        "Genere une SmartNote (5-10 lignes) pour cette consultation.\n\n"
        "Format:\n"
        "- Motif : [raison consultation]\n"
        "- Antecedents : [historique pertinent]\n"
        "- Examen : [observations cliniques]\n"
        "- Plan : [traitements proposes]\n"
        "- Risques : [risques identifies]\n"
        "- Recommandations : [conseils patient]\n"
        "- Prochain RDV : [prochaine etape]\n"
        "- Admin : [devis/paiement si mentionne]\n\n"
        "Transcription:\n{text}"
    ),
)

CHUNK_SUMMARY_PROMPT = _llama3_prompt(
    system=(
        "Tu es un assistant dentaire. "
        "Resume les transcriptions de consultations de maniere concise en francais."
    ),
    user="Resume cette partie ({part}/{total}) de la consultation:\n\n{text}",
)

COMBINE_SUMMARIES_PROMPT = _llama3_prompt(
    system=(
        "Tu es un assistant de documentation dentaire. "
        "Tu combines des resumes partiels en une SmartNote finale structuree en francais."
    ),
    user=(
        "Combine ces resumes en une SmartNote finale (5-10 lignes):\n\n"
        "{summaries}\n\n"
        "Format:\n"
        "- Motif : ...\n"
        "- Antecedents : ...\n"
        "- Examen : ...\n"
        "- Plan : ...\n"
        "- Risques : ...\n"
        "- Recommandations : ...\n"
        "- Prochain RDV : ...\n"
        "- Admin : ..."
    ),
)


# ============================================
# RAG-AUGMENTED PROMPT (Llama-3 Instruct format)
# ============================================
# Used when dental knowledge context is available from the RAG pipeline.
# The context provides guidelines, drug interactions, and protocols
# that ground the SmartNote in verified medical references.

def build_rag_smartnote_prompt(transcription: str, rag_context: str) -> str:
    """
    Build a RAG-augmented SmartNote prompt with retrieved dental knowledge.

    If rag_context is empty, falls back to the standard prompt.
    """
    if not rag_context:
        return SMARTNOTE_PROMPT_OPTIMIZED.format(text=transcription)

    return _llama3_prompt(
        system=(
            "Tu es un assistant de documentation dentaire expert. "
            "Tu generes des SmartNotes concises et structurees en francais "
            "a partir de transcriptions de consultations. "
            "Tu disposes de references medicales pertinentes pour enrichir "
            "et verifier tes recommandations. "
            "Utilise les references pour verifier les protocoles mentionnes, "
            "signaler les risques medicamenteux et enrichir les recommandations. "
            "Reponds uniquement avec la SmartNote au format demande."
        ),
        user=(
            "Genere une SmartNote (5-10 lignes) pour cette consultation.\n\n"
            "References medicales pertinentes:\n"
            f"{rag_context}\n\n"
            "Format:\n"
            "- Motif : [raison consultation]\n"
            "- Antecedents : [historique pertinent]\n"
            "- Examen : [observations cliniques]\n"
            "- Plan : [traitements proposes]\n"
            "- Risques : [risques identifies, interactions medicamenteuses]\n"
            "- Recommandations : [conseils patient, appuyes par les references]\n"
            "- Prochain RDV : [prochaine etape]\n"
            "- Admin : [devis/paiement si mentionne]\n\n"
            f"Transcription:\n{transcription}"
        ),
    )

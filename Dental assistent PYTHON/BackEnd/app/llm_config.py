"""
Configuration centralisée pour l'optimisation LLM.

Ce fichier contient tous les paramètres de performance pour:
- llama-cpp-python (LLM)
- faster-whisper (transcription)
"""

import os

# ============================================
# CONFIGURATION CONTEXTE LLM
# ============================================

# Contexte adapté aux SmartNotes dentaires
# Une consultation typique = 2000-3000 tokens
# SmartNote output = 300-500 tokens
# Marge de sécurité incluse
CONTEXT_LENGTH = 4096

# Longueur maximale de génération pour SmartNotes
MAX_GENERATION_TOKENS = 800

# Seuil pour activer le chunking (en tokens estimés)
CHUNKING_THRESHOLD = 3000

# Taille des chunks pour les longues transcriptions
CHUNK_SIZE_TOKENS = 2000


# ============================================
# CONFIGURATION THREADING
# ============================================

def get_optimal_threads() -> int:
    """
    Calcule le nombre optimal de threads CPU.

    Stratégie: utiliser la moitié des cores pour laisser
    de la marge au système et à Whisper.
    """
    cpu_count = os.cpu_count() or 4
    # Minimum 4 threads, maximum moitié des cores
    return max(4, cpu_count // 2)


CPU_THREADS = get_optimal_threads()


# ============================================
# CONFIGURATION PAR PROFIL HARDWARE
# ============================================

# Batch sizes optimisés par profil
# Plus petit = moins de mémoire, légèrement plus lent
# Plus grand = plus de mémoire, plus rapide (jusqu'à un certain point)
BATCH_SIZES = {
    "high_vram": 512,   # GPU puissant: batch max
    "low_vram": 256,    # GPU limité: batch réduit
    "cpu_only": 128,    # CPU: batch minimal pour éviter saturation
}

# GPU layers pour Llama-3-8B (32 layers total + embeddings)
# Offloader plus de layers = plus rapide si VRAM suffisante
GPU_LAYERS = {
    "high_vram": 33,    # Toutes les couches sur GPU
    "low_vram": 24,     # ~75% sur GPU
    "cpu_only": 0,      # Tout sur CPU
}

# Layers spécifiques pour Apple Silicon (mémoire unifiée)
GPU_LAYERS_APPLE_SILICON = 33  # Offload total, mémoire partagée


# ============================================
# PARAMETRES DE GENERATION
# ============================================

GENERATION_PARAMS = {
    "temperature": 0.3,      # Bas pour documents médicaux (déterministe)
    "top_p": 0.9,            # Nucleus sampling
    "top_k": 40,             # Limite vocabulaire considéré
    "repeat_penalty": 1.1,   # Évite répétitions
}

# Stop tokens pour Llama-3
STOP_TOKENS = ["<|eot_id|>", "<|end_of_text|>"]


# ============================================
# CONFIGURATION WHISPER
# ============================================

WHISPER_CONFIG = {
    "language": "fr",                    # Forcer français (évite détection)
    "vad_filter": True,                  # Filtrer silences
    "vad_parameters": {
        "min_silence_duration_ms": 500,  # Silences > 500ms ignorés
        "speech_pad_ms": 200,            # Padding autour de la parole
    },
    "condition_on_previous_text": False, # Plus rapide, moins de contexte
    "compression_ratio_threshold": 2.4,  # Seuil qualité
    "log_prob_threshold": -1.0,          # Seuil probabilité
    "no_speech_threshold": 0.6,          # Seuil détection silence
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
    "use_mlock": True,   # Verrouille modèle en RAM (évite swap)
    "use_mmap": True,    # Memory-mapped loading (chargement efficace)
}


# ============================================
# PROMPTS OPTIMISES
# ============================================

# Prompt SmartNote optimisé (réduit de ~500 à ~300 tokens)
SMARTNOTE_PROMPT_OPTIMIZED = """Assistant dentaire. Génère une SmartNote concise (5-10 lignes) en français.

Format requis:
• Motif : [raison consultation]
• Antécédents : [historique pertinent]
• Examen : [observations cliniques]
• Plan : [traitements proposés]
• Risques : [risques identifiés]
• Recommandations : [conseils patient]
• Prochain RDV : [prochaine étape]
• Admin : [devis/paiement si mentionné]

Consultation:
{text}

SmartNote:"""

# Prompt pour résumer les chunks
CHUNK_SUMMARY_PROMPT = """Résume cette partie d'une consultation dentaire en français (partie {part}/{total}):

{text}

Résumé concis:"""

# Prompt pour combiner les résumés
COMBINE_SUMMARIES_PROMPT = """Combine ces résumés en une SmartNote dentaire finale (5-10 lignes):

{summaries}

Format:
• Motif : ...
• Antécédents : ...
• Examen : ...
• Plan : ...
• Risques : ...
• Recommandations : ...
• Prochain RDV : ...
• Admin : ...

SmartNote finale:"""

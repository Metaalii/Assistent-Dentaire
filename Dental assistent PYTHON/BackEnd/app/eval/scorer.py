"""
Deterministic SmartNote quality scorer.

All metrics are computable offline (no LLM needed) and suitable for CI.
Each scorer returns a dict with a 0-1 score plus diagnostic details.
"""

from __future__ import annotations

import re
from typing import Any

# The 8 expected SmartNote fields, matching the prompt template exactly.
EXPECTED_FIELDS = [
    "Motif",
    "Antecedents",
    "Examen",
    "Plan",
    "Risques",
    "Recommandations",
    "Prochain RDV",
    "Admin",
]

# Placeholder patterns that indicate an empty / template field.
_PLACEHOLDER_RE = re.compile(
    r"^\s*\[.*\]\s*$"       # [raison consultation]
    r"|^\s*\.{2,}\s*$"      # ...
    r"|^\s*-?\s*$"           # blank or lone dash
    r"|^\s*N/?A\s*$"         # N/A
    r"|^\s*non\s*(renseigne|mentionne|precise|detaille|specifie)\s*$"  # non renseigne
    r"|^\s*aucun[e]?\s*(identifie|signale|mentionne|probleme)?\s*$"   # aucun identifie
    r"|^\s*non\s*$",         # bare "Non"
    re.IGNORECASE,
)


# ------------------------------------------------------------------
# Individual scorers
# ------------------------------------------------------------------

def score_format(smartnote: str) -> dict[str, Any]:
    """Check that all 8 expected fields are present with correct labels."""
    found: list[str] = []
    missing: list[str] = []
    for field in EXPECTED_FIELDS:
        # Match "- Motif :" at start-of-line, tolerating whitespace variance.
        pattern = rf"^[ \t]*-\s*{re.escape(field)}\s*:"
        if re.search(pattern, smartnote, re.MULTILINE | re.IGNORECASE):
            found.append(field)
        else:
            missing.append(field)
    return {
        "score": len(found) / len(EXPECTED_FIELDS),
        "found": found,
        "missing": missing,
    }


def score_field_fill(smartnote: str) -> dict[str, Any]:
    """Check that present fields have substantive content (not placeholders)."""
    filled: list[str] = []
    empty: list[str] = []
    for field in EXPECTED_FIELDS:
        pattern = rf"^[ \t]*-\s*{re.escape(field)}\s*:\s*(.+)$"
        match = re.search(pattern, smartnote, re.MULTILINE | re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value and not _PLACEHOLDER_RE.match(value):
                filled.append(field)
            else:
                empty.append(field)
        else:
            empty.append(field)
    total = len(EXPECTED_FIELDS)
    return {
        "score": len(filled) / total,
        "filled": filled,
        "empty": empty,
    }


def score_length(smartnote: str) -> dict[str, Any]:
    """Check that the SmartNote is 5-10 non-blank lines (the prompt target)."""
    lines = [ln for ln in smartnote.strip().splitlines() if ln.strip()]
    n = len(lines)
    if 5 <= n <= 10:
        score = 1.0
    elif n < 5:
        score = max(0.0, n / 5)
    else:
        # Gentle penalty: lose 0.1 per extra line beyond 10, floor at 0.3
        score = max(0.3, 1.0 - 0.1 * (n - 10))
    return {"score": score, "line_count": n}


def score_language(smartnote: str) -> dict[str, Any]:
    """
    Basic French-language heuristic.

    Checks for common French dental/medical terms that should appear
    in any well-formed SmartNote. Not a full language detector—just
    enough to catch an LLM accidentally switching to English.
    """
    fr_markers = [
        r"\bconsultation\b", r"\bpatient[e]?\b", r"\btraitement\b",
        r"\bdentaire\b", r"\bdouleur\b", r"\bcarie\b", r"\bcontrole\b",
        r"\bparodont", r"\bdetartrage\b", r"\bextraction\b",
        r"\bprothese\b", r"\bradiograph", r"\banesthesi",
        r"\bmolaire\b", r"\bincisive\b", r"\bpremolaire\b",
        r"\bgencive\b", r"\bocclusion\b", r"\bpulp",
        r"\bdevis\b", r"\bprise en charge\b", r"\bseance\b",
        r"\bjours?\b", r"\bsemaines?\b", r"\bmois\b",
        r"\brisques?\b", r"\brecommandation", r"\bantecedent",
    ]
    en_markers = [
        r"\btreatment\b", r"\bpatient\b", r"\bfollow[\s-]?up\b",
        r"\bexamination\b", r"\bappointment\b", r"\brisk\b",
        r"\brecommendation\b", r"\bbilling\b",
    ]
    text_lower = smartnote.lower()
    fr_hits = sum(1 for p in fr_markers if re.search(p, text_lower))
    en_hits = sum(1 for p in en_markers if re.search(p, text_lower))

    if fr_hits >= 3 and en_hits <= 1:
        score = 1.0
    elif fr_hits >= 1 and fr_hits > en_hits:
        score = 0.7
    elif en_hits > fr_hits:
        score = 0.2
    else:
        score = 0.5
    return {"score": score, "fr_hits": fr_hits, "en_hits": en_hits}


def score_faithfulness(
    smartnote: str,
    transcription: str,
    key_terms: list[str] | None = None,
) -> dict[str, Any]:
    """
    Extraction recall: check that key clinical terms from the transcription
    (or an explicit key_terms list) appear in the SmartNote.

    This catches two failure modes:
    - **Omission**: the LLM dropped important clinical facts.
    - **Hallucination proxy**: if key terms are absent but random terms
      appear, the note may be fabricated.
    """
    if key_terms is None:
        key_terms = _extract_key_terms(transcription)

    if not key_terms:
        return {"score": 1.0, "matched": [], "missed": [], "total": 0}

    note_lower = smartnote.lower()
    matched = []
    missed = []
    for t in key_terms:
        tl = t.lower()
        # Prefix match: "radiograph" matches "radio", "radiographie", etc.
        # Use word-boundary prefix so "36" doesn't match "136".
        if tl in note_lower or re.search(rf"\b{re.escape(tl)}", note_lower):
            matched.append(t)
        else:
            missed.append(t)
    return {
        "score": len(matched) / len(key_terms),
        "matched": matched,
        "missed": missed,
        "total": len(key_terms),
    }


# ------------------------------------------------------------------
# Key-term extraction heuristic
# ------------------------------------------------------------------

# Dental / clinical terms to look for in transcriptions.
_CLINICAL_TERM_PATTERNS = [
    # Tooth references (ISO numbering: 11-48, or French names)
    r"\b[1-4][1-8]\b",
    r"\bmolaire\b", r"\bpremolaire\b", r"\bincisive\b", r"\bcanine\b",
    # Common conditions
    r"\bcarie\b", r"\bpulpite\b", r"\babces\b", r"\bparodontite\b",
    r"\bgingivite\b", r"\bfracture\b", r"\bfistule\b",
    # Common procedures
    r"\bdetartrage\b", r"\bextraction\b", r"\bcomposite\b",
    r"\bcouronne\b", r"\bimplant\b", r"\bdevitalisation\b",
    r"\bendodont", r"\bradiograph", r"\bpanoramique\b",
    # Medications / substances
    r"\bantibiotique\b", r"\bamoxicilline\b", r"\bibuprofene\b",
    r"\banticoagulant\b", r"\bbisphosphonate\b", r"\banesthesi",
    # Symptoms
    r"\bdouleur\b", r"\bgonflement\b", r"\bsaignement\b",
    r"\bsensibilite\b", r"\bmobilite\b",
]


def _extract_key_terms(transcription: str) -> list[str]:
    """Extract clinically-relevant terms from a transcription."""
    terms: list[str] = []
    text_lower = transcription.lower()
    for pattern in _CLINICAL_TERM_PATTERNS:
        for match in re.finditer(pattern, text_lower):
            term = match.group(0)
            if term not in terms:
                terms.append(term)
    return terms


# ------------------------------------------------------------------
# Aggregate scorer
# ------------------------------------------------------------------

def score_smartnote(
    smartnote: str,
    transcription: str = "",
    key_terms: list[str] | None = None,
) -> dict[str, Any]:
    """
    Run all scorers and return an aggregate report.

    Returns:
        {
            "overall": float,          # weighted 0-1 score
            "format": {...},
            "field_fill": {...},
            "length": {...},
            "language": {...},
            "faithfulness": {...},      # only if transcription provided
        }
    """
    fmt = score_format(smartnote)
    fill = score_field_fill(smartnote)
    length = score_length(smartnote)
    lang = score_language(smartnote)

    result: dict[str, Any] = {
        "format": fmt,
        "field_fill": fill,
        "length": length,
        "language": lang,
    }

    # Weights: format compliance is most critical for a structured note.
    weights = {
        "format": 0.30,
        "field_fill": 0.25,
        "length": 0.10,
        "language": 0.10,
    }
    weighted_sum = (
        fmt["score"] * weights["format"]
        + fill["score"] * weights["field_fill"]
        + length["score"] * weights["length"]
        + lang["score"] * weights["language"]
    )
    total_weight = sum(weights.values())

    if transcription or key_terms:
        faith = score_faithfulness(smartnote, transcription, key_terms)
        result["faithfulness"] = faith
        faith_weight = 0.25
        weighted_sum += faith["score"] * faith_weight
        total_weight += faith_weight

    result["overall"] = round(weighted_sum / total_weight, 4)
    return result

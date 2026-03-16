"""
Shared input-sanitization helper.

Used by summarize and RAG routers to clean user text before LLM processing.

Defence layers (applied in order):
1. NFKC Unicode normalization — collapses homoglyphs and full-width chars
   so that pattern matching below works reliably (e.g. Cyrillic 'е' → 'e').
2. Control-character stripping — removes null bytes and other non-printable
   chars that could confuse tokenizers or bypass regex filters.
3. Prompt-injection pattern removal — regex-based removal of common
   jailbreak phrases.  Not a complete defence on its own; the structural
   isolation in llm_config.py (XML delimiters around the transcript) is
   the primary guard.
4. Whitespace normalization — collapse runs of spaces/tabs and limit
   consecutive newlines.
5. Length cap — hard truncation to prevent OOM / context overflow.
"""

import re
import unicodedata


def sanitize_input(text: str, max_length: int = 50000) -> str:
    """
    Sanitize user input before LLM processing.

    Returns an empty string for empty/blank input so callers can
    raise a 400 without exposing implementation details.
    """
    if not text or not text.strip():
        return ""

    # ------------------------------------------------------------------
    # 1. NFKC normalization — defeats homoglyph injection:
    #    "Ѕystem:" (Cyrillic Ѕ)   → "System:" (caught below)
    #    "ｉgnore" (full-width i)  → "ignore"  (caught below)
    #    Zero-width joiners and similar invisible chars are also collapsed.
    # ------------------------------------------------------------------
    text = unicodedata.normalize("NFKC", text)

    # ------------------------------------------------------------------
    # 2. Strip control characters (except \n and \t which are structural).
    #    Includes NUL (0x00), BEL, BS, VT, FF, DEL, and the C1 block.
    # ------------------------------------------------------------------
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f]", "", text)

    # ------------------------------------------------------------------
    # 3. Prompt-injection pattern removal.
    #    Coverage: direct commands, indirect phrasing, role-switch attempts,
    #    separator tricks, and common jailbreak openers.
    #    Note: NFKC above has already normalised Unicode variants, so plain
    #    ASCII regex is sufficient here.
    # ------------------------------------------------------------------
    _INJECTION_PATTERNS = [
        # Direct overrides
        r"(?i)ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|rules?|context)",
        r"(?i)disregard\s+(all\s+)?(previous|above|prior|earlier)",
        r"(?i)forget\s+(everything|all(\s+previous)?|prior\s+instructions?)",
        r"(?i)override\s+(previous|prior|all)\s+(instructions?|rules?)",
        # Role / persona switches
        r"(?i)you\s+are\s+now\s+(a|an)\s+",
        r"(?i)act\s+as\s+(a|an|if)\s+",
        r"(?i)pretend\s+(you\s+are|to\s+be)\s+",
        r"(?i)roleplay\s+as\s+",
        r"(?i)simulate\s+(being|a|an)\s+",
        # New-instruction injectors
        r"(?i)new\s+instructions?\s*:",
        r"(?i)updated?\s+instructions?\s*:",
        r"(?i)additional\s+instructions?\s*:",
        # Separator / delimiter tricks (trying to inject a fake system turn)
        r"(?i)(^|\n)\s*system\s*:\s*",
        r"(?i)(^|\n)\s*assistant\s*:\s*",
        r"(?i)(^|\n)\s*<\|?(system|user|assistant)\|?>\s*",
        # Prompt-leak / exfiltration
        r"(?i)reveal\s+(your|the)\s+(system\s+)?prompt",
        r"(?i)print\s+(your|the)\s+(system\s+)?prompt",
        r"(?i)what\s+(are|were)\s+your\s+(original\s+)?instructions?",
        r"(?i)repeat\s+(everything|all)\s+(above|before|prior)",
    ]

    for pattern in _INJECTION_PATTERNS:
        text = re.sub(pattern, "[FILTERED]", text)

    # ------------------------------------------------------------------
    # 4. Whitespace normalization (keep structure; don't flatten paragraphs).
    # ------------------------------------------------------------------
    text = re.sub(r"[ \t]+", " ", text)        # collapse horizontal whitespace
    text = re.sub(r"\n{4,}", "\n\n\n", text)   # cap consecutive blank lines

    # ------------------------------------------------------------------
    # 5. Hard length cap.  Log if truncation occurs so it can be monitored.
    # ------------------------------------------------------------------
    text = text.strip()
    if len(text) > max_length:
        import logging
        logging.getLogger("dental_assistant.sanitize").warning(
            "Input truncated from %d to %d characters", len(text), max_length
        )
        text = text[:max_length]

    return text

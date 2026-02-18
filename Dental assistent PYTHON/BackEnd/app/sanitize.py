"""
Shared input-sanitization helper.

Used by summarize and RAG routers to clean user text before LLM processing.
"""

import re


def sanitize_input(text: str, max_length: int = 50000) -> str:
    """
    Sanitize user input before LLM processing.

    - Removes potential prompt injection patterns
    - Limits text length to prevent memory issues
    - Removes control characters except newlines
    - Normalizes whitespace
    """
    if not text:
        return ""

    # Truncate to max length
    text = text[:max_length]

    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Remove potential prompt injection patterns (basic protection)
    injection_patterns = [
        r'(?i)ignore\s+(all\s+)?(previous|above)\s+instructions?',
        r'(?i)disregard\s+(all\s+)?(previous|above)',
        r'(?i)forget\s+(everything|all)',
        r'(?i)you\s+are\s+now\s+a',
        r'(?i)new\s+instructions?:',
        r'(?i)system\s*:\s*',
    ]

    for pattern in injection_patterns:
        text = re.sub(pattern, '[FILTERED]', text)

    # Normalize excessive whitespace (but keep structure)
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space
    text = re.sub(r'\n{4,}', '\n\n\n', text)  # Max 3 consecutive newlines

    return text.strip()

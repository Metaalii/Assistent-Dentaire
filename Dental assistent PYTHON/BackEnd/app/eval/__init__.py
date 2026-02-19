"""
SmartNote evaluation framework.

Deterministic quality metrics for dental SmartNotes:
- Structural compliance (8-field format)
- Field fill rate (substantive content vs placeholders)
- Length compliance (5-10 lines target)
- Faithfulness (key term extraction recall)
"""

from app.eval.scorer import score_smartnote  # noqa: F401

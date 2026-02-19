"""
Golden-set tests for SmartNote output quality.

These tests validate that the evaluation scorer itself is correct
and that all gold-standard reference notes meet the quality bar.
They also verify that known-bad outputs are properly caught.

Run:  pytest tests/test_smartnote_eval.py -v
"""

from __future__ import annotations

import pytest

from app.eval.scorer import (
    EXPECTED_FIELDS,
    score_faithfulness,
    score_field_fill,
    score_format,
    score_language,
    score_length,
    score_smartnote,
)
from app.eval.samples import SAMPLES


# ======================================================================
# 1. Gold-standard reference notes must all pass
# ======================================================================

class TestGoldenSetBaseline:
    """Every reference note should score above the quality threshold."""

    @pytest.mark.parametrize(
        "sample",
        SAMPLES,
        ids=[s.scenario for s in SAMPLES],
    )
    def test_reference_note_passes_overall(self, sample):
        report = score_smartnote(
            smartnote=sample.reference_note,
            transcription=sample.transcription,
            key_terms=sample.key_terms,
        )
        assert report["overall"] >= 0.80, (
            f"{sample.scenario}: overall {report['overall']:.2%} < 80%"
        )

    @pytest.mark.parametrize(
        "sample",
        SAMPLES,
        ids=[s.scenario for s in SAMPLES],
    )
    def test_reference_note_format_perfect(self, sample):
        """Every reference note must have all 8 fields."""
        report = score_format(sample.reference_note)
        assert report["score"] == 1.0, (
            f"{sample.scenario}: missing fields {report['missing']}"
        )

    @pytest.mark.parametrize(
        "sample",
        SAMPLES,
        ids=[s.scenario for s in SAMPLES],
    )
    def test_reference_note_language_french(self, sample):
        report = score_language(sample.reference_note)
        assert report["score"] >= 0.7, (
            f"{sample.scenario}: language score {report['score']:.2%} "
            f"(fr={report['fr_hits']}, en={report['en_hits']})"
        )


# ======================================================================
# 2. Format scorer catches structural regressions
# ======================================================================

class TestFormatScorer:
    def test_perfect_format(self):
        note = "\n".join(f"- {f} : some content" for f in EXPECTED_FIELDS)
        result = score_format(note)
        assert result["score"] == 1.0
        assert result["missing"] == []

    def test_missing_single_field(self):
        fields = EXPECTED_FIELDS.copy()
        fields.remove("Risques")
        note = "\n".join(f"- {f} : some content" for f in fields)
        result = score_format(note)
        assert result["score"] == 7 / 8
        assert "Risques" in result["missing"]

    def test_completely_wrong_format(self):
        note = "This is just a paragraph of text with no fields at all."
        result = score_format(note)
        assert result["score"] == 0.0
        assert len(result["missing"]) == 8

    def test_case_insensitive(self):
        note = "\n".join(f"- {f.upper()} : content" for f in EXPECTED_FIELDS)
        result = score_format(note)
        assert result["score"] == 1.0

    def test_tolerates_whitespace_variance(self):
        note = "  -  Motif  :  content\n  - Antecedents:content"
        result = score_format(note)
        assert "Motif" in result["found"]
        assert "Antecedents" in result["found"]

    def test_empty_input(self):
        result = score_format("")
        assert result["score"] == 0.0


# ======================================================================
# 3. Field fill scorer detects placeholders
# ======================================================================

class TestFieldFillScorer:
    def test_all_filled(self):
        note = "\n".join(
            f"- {f} : real clinical content here" for f in EXPECTED_FIELDS
        )
        result = score_field_fill(note)
        assert result["score"] == 1.0

    def test_placeholder_brackets(self):
        note = "- Motif : [raison consultation]\n- Examen : real content"
        result = score_field_fill(note)
        assert "Motif" in result["empty"]
        assert "Examen" in result["filled"]

    def test_placeholder_non_mentionne(self):
        note = "- Admin : Non mentionne"
        result = score_field_fill(note)
        assert "Admin" in result["empty"]

    def test_placeholder_na(self):
        note = "- Antecedents : N/A"
        result = score_field_fill(note)
        assert "Antecedents" in result["empty"]

    def test_placeholder_aucun(self):
        note = "- Risques : Aucun identifie"
        result = score_field_fill(note)
        assert "Risques" in result["empty"]

    def test_placeholder_dots(self):
        note = "- Plan : ..."
        result = score_field_fill(note)
        assert "Plan" in result["empty"]

    def test_placeholder_non_detaille(self):
        note = "- Examen : Non detaille"
        result = score_field_fill(note)
        assert "Examen" in result["empty"]


# ======================================================================
# 4. Length scorer enforces 5-10 line target
# ======================================================================

class TestLengthScorer:
    def test_optimal_length(self):
        note = "\n".join(f"- Field{i} : content" for i in range(8))
        result = score_length(note)
        assert result["score"] == 1.0
        assert result["line_count"] == 8

    def test_too_short(self):
        note = "- Motif : something\n- Plan : something"
        result = score_length(note)
        assert result["score"] < 1.0
        assert result["line_count"] == 2

    def test_one_line(self):
        result = score_length("single line")
        assert result["score"] == pytest.approx(0.2, abs=0.01)

    def test_too_long(self):
        note = "\n".join(f"line {i}" for i in range(15))
        result = score_length(note)
        assert result["score"] < 1.0

    def test_empty(self):
        result = score_length("")
        assert result["score"] == 0.0

    def test_blank_lines_excluded(self):
        """Blank lines shouldn't count toward the total."""
        note = "- Motif : x\n\n\n- Plan : y\n\n\n- Examen : z"
        result = score_length(note)
        assert result["line_count"] == 3


# ======================================================================
# 5. Language scorer catches English drift
# ======================================================================

class TestLanguageScorer:
    def test_clearly_french(self):
        note = (
            "- Motif : Douleur molaire depuis 3 jours\n"
            "- Examen : Carie profonde, detartrage necessaire\n"
            "- Plan : Traitement endodontique, couronne"
        )
        result = score_language(note)
        assert result["score"] == 1.0

    def test_clearly_english(self):
        note = (
            "- Reason : Tooth pain for 3 days\n"
            "- Examination : Deep cavity, treatment needed\n"
            "- Follow-up appointment next week, billing sent"
        )
        result = score_language(note)
        assert result["score"] <= 0.5

    def test_mixed_language(self):
        note = (
            "- Motif : Patient consultation for carie\n"
            "- Treatment : Follow-up appointment"
        )
        result = score_language(note)
        # Should score somewhere in between
        assert 0.1 <= result["score"] <= 0.9


# ======================================================================
# 6. Faithfulness scorer catches omissions
# ======================================================================

class TestFaithfulnessScorer:
    def test_all_terms_present(self):
        transcription = "Le patient a une carie sur la 36 avec douleur"
        note = "- Motif : Douleur carie 36"
        result = score_faithfulness(
            note, transcription, key_terms=["carie", "36", "douleur"]
        )
        assert result["score"] == 1.0
        assert result["missed"] == []

    def test_missing_terms(self):
        note = "- Motif : Controle annuel"
        result = score_faithfulness(
            note,
            "Le patient a une carie profonde sur la 36",
            key_terms=["carie", "36", "profonde"],
        )
        assert result["score"] < 1.0
        assert "36" in result["missed"]

    def test_no_key_terms(self):
        """If no key terms are extractable, score should be 1.0 (no expectations)."""
        result = score_faithfulness("any note", "bonjour au revoir", key_terms=[])
        assert result["score"] == 1.0

    def test_auto_extraction(self):
        """When no explicit key_terms, the scorer auto-extracts from transcription."""
        transcription = "Carie sur molaire 36 avec douleur, detartrage prevu"
        note = "- Motif : Douleur carie 36, detartrage"
        result = score_faithfulness(note, transcription)
        assert result["score"] > 0.0
        assert len(result["matched"]) > 0

    def test_prefix_matching(self):
        """Stem 'radio' should match 'radiographie' in the note."""
        note = "- Examen : Radiographie panoramique realisee"
        result = score_faithfulness(
            note, "", key_terms=["radio"]
        )
        assert "radio" in result["matched"]


# ======================================================================
# 7. Aggregate scorer
# ======================================================================

class TestAggregateScorer:
    def test_perfect_note(self):
        note = (
            "- Motif : Douleur molaire 36\n"
            "- Antecedents : Patient diabetique\n"
            "- Examen : Carie profonde sur 36, test froid positif\n"
            "- Plan : Detartrage et obturation composite\n"
            "- Risques : Pulpite irreversible, extraction possible\n"
            "- Recommandations : Brossage doux, consultation controle\n"
            "- Prochain RDV : 2 semaines\n"
            "- Admin : Devis 120 euros"
        )
        transcription = "Douleur molaire 36 carie detartrage composite"
        report = score_smartnote(note, transcription)
        assert report["overall"] >= 0.85

    def test_empty_note_scores_zero(self):
        report = score_smartnote("")
        assert report["overall"] < 0.2

    def test_has_all_sections(self):
        note = "\n".join(f"- {f} : content" for f in EXPECTED_FIELDS)
        report = score_smartnote(note)
        assert "format" in report
        assert "field_fill" in report
        assert "length" in report
        assert "language" in report

    def test_faithfulness_included_when_transcription_provided(self):
        note = "- Motif : Douleur"
        report = score_smartnote(note, transcription="douleur molaire")
        assert "faithfulness" in report

    def test_faithfulness_excluded_without_transcription(self):
        note = "- Motif : Douleur"
        report = score_smartnote(note)
        assert "faithfulness" not in report


# ======================================================================
# 8. Regression guards — known-bad outputs must fail
# ======================================================================

class TestKnownBadOutputs:
    def test_english_output_fails(self):
        """An LLM that switched to English should score poorly."""
        note = (
            "- Reason : Tooth pain\n"
            "- History : No prior issues\n"
            "- Examination : Deep cavity on tooth 36\n"
            "- Treatment : Root canal treatment\n"
            "- Risks : Infection spread\n"
            "- Recommendations : Avoid hard foods\n"
            "- Next Appointment : 2 weeks\n"
            "- Billing : 200 euros"
        )
        report = score_smartnote(note, "douleur molaire 36 carie")
        # Format should fail (wrong field labels)
        assert report["format"]["score"] == 0.0
        assert report["overall"] < 0.50

    def test_truncated_output_fails(self):
        """Only 2 fields generated — should fail format and length."""
        note = "- Motif : Douleur\n- Plan : Traitement"
        report = score_smartnote(note)
        assert report["format"]["score"] < 0.5
        assert report["overall"] < 0.50

    def test_hallucinated_output_fails_faithfulness(self):
        """Note mentions terms not in the transcription."""
        transcription = "Simple detartrage, pas de probleme"
        note = (
            "- Motif : Extraction urgente molaire 48\n"
            "- Antecedents : Patient sous anticoagulant\n"
            "- Examen : Fracture radiculaire, abces periapical\n"
            "- Plan : Extraction chirurgicale sous anesthesie generale\n"
            "- Risques : Hemorragie massive\n"
            "- Recommandations : Hospitalisation\n"
            "- Prochain RDV : Demain matin urgence\n"
            "- Admin : Devis chirurgical 2000 euros"
        )
        report = score_smartnote(
            note, transcription, key_terms=["detartrage"]
        )
        # The key term from the transcription is "detartrage"
        # which doesn't appear in the hallucinated note
        assert report["faithfulness"]["score"] < 1.0

    def test_template_only_output_fails(self):
        """LLM just echoed the template placeholders."""
        note = (
            "- Motif : [raison consultation]\n"
            "- Antecedents : [historique pertinent]\n"
            "- Examen : [observations cliniques]\n"
            "- Plan : [traitements proposes]\n"
            "- Risques : [risques identifies]\n"
            "- Recommandations : [conseils patient]\n"
            "- Prochain RDV : [prochaine etape]\n"
            "- Admin : [devis/paiement si mentionne]"
        )
        report = score_smartnote(note, "douleur carie 36")
        # Format passes but field_fill should fail completely
        assert report["format"]["score"] == 1.0
        assert report["field_fill"]["score"] == 0.0
        assert report["overall"] < 0.60

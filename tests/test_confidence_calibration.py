"""
Tests for the Confidence Calibration and Uncertainty Handling Framework.

Covers:
  1. Confidence type taxonomy and band classification with asymmetric thresholds.
  2. Temperature scaling (fitting, calibration, diagnostics).
  3. Calibration evaluation metrics (ECE, MCE, reliability diagrams).
  4. Confidence distribution and high/low-confidence case analysis.
  5. Per-model confidence metadata registry.
  6. End-to-end: every model inference has confidence_metadata and confidence_band.
  7. Production labels are "High confidence" / "Moderate confidence" / "Insufficient evidence".
  8. Mastery model explicitly reports theta as NOT a confidence.
  9. Documentation (CONFIDENCE_GLOSSARY.md) exists.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml.calibration.confidence_types import (
    ConfidenceBand,
    ConfidenceMetadata,
    ConfidenceType,
    classify_confidence_band,
)
from ml.calibration.temperature_scaling import TemperatureScaler, apply_temperature_to_probs
from ml.calibration.calibration_metrics import (
    CalibrationReport,
    confidence_distribution_data,
    expected_calibration_error,
    generate_calibration_report,
    high_confidence_errors,
    low_confidence_correct,
    maximum_calibration_error,
    reliability_diagram_data,
)
from ml.calibration.model_confidence_registry import (
    MODEL_CONFIDENCE_REGISTRY,
    get_confidence_metadata,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Confidence Type Taxonomy & Band Classification
# ═══════════════════════════════════════════════════════════════════════════

class TestConfidenceTypes:
    """Test the four confidence types and three production bands."""

    def test_confidence_type_enum_values(self):
        assert ConfidenceType.CALIBRATED_PROBABILITY.value == "calibrated_probability"
        assert ConfidenceType.MODEL_SCORE.value == "model_score"
        assert ConfidenceType.HEURISTIC_CONFIDENCE.value == "heuristic_confidence"
        assert ConfidenceType.UNAVAILABLE.value == "unavailable"

    def test_confidence_band_labels(self):
        """Production must use these exact labels, not numeric precision."""
        assert ConfidenceBand.HIGH.value == "High confidence"
        assert ConfidenceBand.MODERATE.value == "Moderate confidence"
        assert ConfidenceBand.INSUFFICIENT.value == "Insufficient evidence"

    def test_unavailable_always_insufficient(self):
        """UNAVAILABLE type always maps to 'Insufficient evidence'."""
        for score in [0.0, 0.5, 0.99, 1.0]:
            band = classify_confidence_band(score, ConfidenceType.UNAVAILABLE)
            assert band == ConfidenceBand.INSUFFICIENT

    def test_calibrated_probability_thresholds(self):
        """Calibrated probabilities have the most lenient thresholds."""
        assert classify_confidence_band(0.80, ConfidenceType.CALIBRATED_PROBABILITY) == ConfidenceBand.HIGH
        assert classify_confidence_band(0.75, ConfidenceType.CALIBRATED_PROBABILITY) == ConfidenceBand.HIGH
        assert classify_confidence_band(0.60, ConfidenceType.CALIBRATED_PROBABILITY) == ConfidenceBand.MODERATE
        assert classify_confidence_band(0.45, ConfidenceType.CALIBRATED_PROBABILITY) == ConfidenceBand.MODERATE
        assert classify_confidence_band(0.30, ConfidenceType.CALIBRATED_PROBABILITY) == ConfidenceBand.INSUFFICIENT

    def test_model_score_asymmetric_higher_thresholds(self):
        """
        Uncalibrated model scores MUST clear a higher bar than calibrated probs.
        A model score of 0.80 is NOT high confidence — NNs are overconfident.
        """
        # 0.80 is HIGH for calibrated but only MODERATE for model score
        assert classify_confidence_band(0.80, ConfidenceType.CALIBRATED_PROBABILITY) == ConfidenceBand.HIGH
        assert classify_confidence_band(0.80, ConfidenceType.MODEL_SCORE) == ConfidenceBand.MODERATE
        # Only >= 0.85 is HIGH for model score
        assert classify_confidence_band(0.85, ConfidenceType.MODEL_SCORE) == ConfidenceBand.HIGH
        assert classify_confidence_band(0.60, ConfidenceType.MODEL_SCORE) == ConfidenceBand.INSUFFICIENT

    def test_heuristic_confidence_conservative(self):
        """Heuristic confidence is binned conservatively."""
        assert classify_confidence_band(0.85, ConfidenceType.HEURISTIC_CONFIDENCE) == ConfidenceBand.HIGH
        assert classify_confidence_band(0.70, ConfidenceType.HEURISTIC_CONFIDENCE) == ConfidenceBand.MODERATE
        assert classify_confidence_band(0.50, ConfidenceType.HEURISTIC_CONFIDENCE) == ConfidenceBand.INSUFFICIENT

    def test_confidence_metadata_to_dict(self):
        """ConfidenceMetadata must serialize cleanly."""
        meta = ConfidenceMetadata(
            raw_score=0.87,
            confidence_type=ConfidenceType.MODEL_SCORE,
            confidence_band=ConfidenceBand.HIGH,
            calibration_method=None,
            interpretation_note="Test note",
        )
        d = meta.to_dict()
        assert d["raw_score"] == 0.87
        assert d["confidence_type"] == "model_score"
        assert d["confidence_band"] == "High confidence"
        assert d["interpretation_note"] == "Test note"


# ═══════════════════════════════════════════════════════════════════════════
# 2. Temperature Scaling
# ═══════════════════════════════════════════════════════════════════════════

class TestTemperatureScaling:
    """Test temperature scaling for post-hoc calibration."""

    @pytest.fixture
    def overconfident_data(self):
        """Simulate an overconfident 3-class classifier."""
        rng = np.random.RandomState(42)
        n = 200
        # Generate logits where model is overconfident
        true_labels = rng.randint(0, 3, size=n)
        logits = rng.randn(n, 3).astype(np.float64)
        # Make the model predict the correct class most of the time, but with extreme logits
        for i in range(n):
            if rng.rand() < 0.7:
                logits[i, true_labels[i]] += 3.0
            else:
                wrong = (true_labels[i] + 1) % 3
                logits[i, wrong] += 3.0
        return logits, true_labels

    def test_temperature_scaling_learns_T_greater_than_1_for_overconfident(self, overconfident_data):
        """For an overconfident model, temperature should be > 1 to soften."""
        logits, labels = overconfident_data
        scaler = TemperatureScaler(lr=0.01, max_iter=200)
        scaler.fit(logits, labels)
        assert scaler.is_fitted
        # Overconfident models need T > 1 to soften
        assert scaler.temperature > 1.0

    def test_temperature_scaling_reduces_ece(self, overconfident_data):
        """After fitting, ECE should decrease (or at worst stay the same)."""
        logits, labels = overconfident_data
        scaler = TemperatureScaler(lr=0.01, max_iter=200)
        scaler.fit(logits, labels)
        diag = scaler.get_diagnostics()
        # ECE after should be <= ECE before
        assert diag["ece_after"] <= diag["ece_before"] + 0.01  # small tolerance

    def test_calibrate_preserves_argmax(self, overconfident_data):
        """Temperature scaling preserves predictions (only changes confidence)."""
        logits, labels = overconfident_data
        scaler = TemperatureScaler()
        scaler.fit(logits, labels)
        original_preds = np.argmax(logits, axis=-1)
        calibrated = scaler.calibrate(logits)
        calibrated_preds = np.argmax(calibrated, axis=-1)
        np.testing.assert_array_equal(original_preds, calibrated_preds)

    def test_calibrate_output_is_valid_probability(self, overconfident_data):
        """Calibrated output must sum to 1 and be in [0, 1]."""
        logits, labels = overconfident_data
        scaler = TemperatureScaler()
        scaler.fit(logits, labels)
        calibrated = scaler.calibrate(logits)
        assert np.all(calibrated >= 0.0)
        assert np.all(calibrated <= 1.0)
        np.testing.assert_allclose(np.sum(calibrated, axis=-1), 1.0, atol=1e-6)

    def test_calibrate_probs_roundtrip(self):
        """apply_temperature_to_probs re-normalizes correctly."""
        probs = [0.8, 0.15, 0.05]
        result = apply_temperature_to_probs(probs, temperature=2.0)
        assert len(result) == 3
        assert abs(sum(result) - 1.0) < 1e-5
        # Temperature > 1 should soften: max prob decreases
        assert result[0] < 0.8

    def test_scaler_diagnostics(self, overconfident_data):
        """Diagnostics should include all expected fields."""
        logits, labels = overconfident_data
        scaler = TemperatureScaler()
        scaler.fit(logits, labels)
        diag = scaler.get_diagnostics()
        assert "temperature" in diag
        assert "fitted" in diag
        assert diag["fitted"] is True
        assert "n_calibration_samples" in diag
        assert "ece_before" in diag
        assert "ece_after" in diag
        assert "nll_before" in diag
        assert "nll_after" in diag

    def test_insufficient_data_skips_fitting(self):
        """With fewer than 10 samples, fitting should be skipped."""
        logits = np.random.randn(5, 3)
        labels = np.array([0, 1, 2, 0, 1])
        scaler = TemperatureScaler()
        scaler.fit(logits, labels)
        assert not scaler.is_fitted
        assert scaler.temperature == 1.0


# ═══════════════════════════════════════════════════════════════════════════
# 3. Calibration Evaluation Metrics
# ═══════════════════════════════════════════════════════════════════════════

class TestCalibrationMetrics:
    """Test ECE, MCE, reliability diagram, and diagnostic outputs."""

    def test_perfect_calibration_zero_ece(self):
        """A perfectly calibrated model should have ECE ≈ 0."""
        # If confidence = accuracy in each bin, ECE should be 0
        confidences = [0.1, 0.3, 0.5, 0.7, 0.9] * 20
        # Make accuracy match confidence (1 with prob = conf)
        rng = np.random.RandomState(42)
        accuracies = [int(rng.rand() < c) for c in confidences]
        ece = expected_calibration_error(confidences, accuracies, num_bins=5)
        # Won't be exactly 0 due to randomness, but should be small
        assert ece < 0.20

    def test_overconfident_model_has_high_ece(self):
        """A model that always says 0.99 but is only right 50% has high ECE."""
        confidences = [0.99] * 100
        accuracies = [1] * 50 + [0] * 50
        ece = expected_calibration_error(confidences, accuracies, num_bins=10)
        assert ece > 0.40  # Very miscalibrated

    def test_reliability_diagram_structure(self):
        """Reliability diagram data should have the expected structure."""
        confs = np.random.rand(100).tolist()
        accs = [int(c > 0.5) for c in confs]
        data = reliability_diagram_data(confs, accs, num_bins=10)
        assert "bins" in data
        assert "ece" in data
        assert "mce" in data
        assert "num_samples" in data
        assert len(data["bins"]) == 10
        assert data["perfectly_calibrated_line"] == [[0.0, 0.0], [1.0, 1.0]]
        for b in data["bins"]:
            assert "bin_lower" in b
            assert "bin_upper" in b
            assert "mean_confidence" in b
            assert "count" in b

    def test_confidence_distribution_structure(self):
        """Confidence distribution should have histogram and statistics."""
        confs = np.random.rand(200).tolist()
        data = confidence_distribution_data(confs, num_bins=20)
        assert "histogram" in data
        assert len(data["histogram"]) == 20
        assert "mean_confidence" in data
        assert "median_confidence" in data
        assert "std_confidence" in data
        assert data["num_samples"] == 200

    def test_high_confidence_errors_detection(self):
        """Should find cases where model was confident but wrong."""
        confs = [0.95, 0.90, 0.30, 0.85, 0.50]
        preds = ["A", "B", "A", "C", "A"]
        actuals = ["A", "A", "A", "A", "A"]
        errors = high_confidence_errors(confs, preds, actuals, threshold=0.80)
        # Indices 1, 3 are high-confidence errors (confident but wrong)
        assert len(errors) == 2
        assert errors[0]["confidence"] == 0.90  # Sorted by descending confidence
        assert errors[0]["predicted"] == "B"
        assert errors[0]["actual"] == "A"

    def test_low_confidence_correct_detection(self):
        """Should find cases where model was uncertain but correct."""
        confs = [0.30, 0.90, 0.40, 0.20, 0.95]
        preds = ["A", "B", "A", "A", "A"]
        actuals = ["A", "A", "A", "A", "A"]
        correct = low_confidence_correct(confs, preds, actuals, threshold=0.50)
        # Indices 0, 2, 3 are low-confidence correct
        assert len(correct) == 3
        assert correct[0]["confidence"] == 0.20  # Sorted by ascending confidence

    def test_calibration_report_generation(self):
        """generate_calibration_report should produce all four outputs."""
        rng = np.random.RandomState(42)
        n = 100
        confs = rng.rand(n).tolist()
        labels = ["A", "B", "C"]
        preds = [labels[rng.randint(0, 3)] for _ in range(n)]
        actuals = [labels[rng.randint(0, 3)] for _ in range(n)]

        report = generate_calibration_report(
            model_name="test-model",
            confidence_type="model_score",
            confidences=confs,
            predictions=preds,
            actuals=actuals,
        )
        assert isinstance(report, CalibrationReport)
        assert report.model_name == "test-model"
        assert report.num_samples == 100
        assert len(report.reliability_diagram["bins"]) > 0
        assert len(report.confidence_distribution["histogram"]) > 0
        assert isinstance(report.high_confidence_errors, list)
        assert isinstance(report.low_confidence_correct, list)
        assert report.summary  # Non-empty summary


# ═══════════════════════════════════════════════════════════════════════════
# 4. Model Confidence Registry
# ═══════════════════════════════════════════════════════════════════════════

class TestModelConfidenceRegistry:
    """Test per-model confidence type classification."""

    CANONICAL_MODELS = [
        "question-difficulty-v1",
        "question-skill-v1",
        "answer-nli-v1",
        "code-risk-v1",
        "mastery-v1",
    ]

    def test_all_five_models_registered(self):
        """Every canonical model must be in the confidence registry."""
        for model in self.CANONICAL_MODELS:
            assert model in MODEL_CONFIDENCE_REGISTRY, f"{model} missing from confidence registry"

    def test_each_model_has_required_fields(self):
        """Each registry entry must have confidence_type, interpretation, calibration_status."""
        for model in self.CANONICAL_MODELS:
            entry = MODEL_CONFIDENCE_REGISTRY[model]
            assert "confidence_type" in entry
            assert "interpretation" in entry
            assert "calibration_status" in entry
            assert "calibration_feasibility" in entry
            assert "tiers" in entry

    def test_mastery_confidence_is_unavailable(self):
        """mastery-v1 must be typed as UNAVAILABLE (theta is not confidence)."""
        entry = MODEL_CONFIDENCE_REGISTRY["mastery-v1"]
        assert entry["confidence_type"] == ConfidenceType.UNAVAILABLE

    def test_classifiers_are_model_score(self):
        """Uncalibrated classifiers must be typed as MODEL_SCORE."""
        for model in ["question-difficulty-v1", "answer-nli-v1", "code-risk-v1"]:
            entry = MODEL_CONFIDENCE_REGISTRY[model]
            assert entry["confidence_type"] == ConfidenceType.MODEL_SCORE

    def test_get_confidence_metadata_returns_correct_types(self):
        """get_confidence_metadata should return proper ConfidenceMetadata."""
        meta = get_confidence_metadata("question-difficulty-v1", 0.85, source_tier="ml")
        assert isinstance(meta, ConfidenceMetadata)
        assert meta.confidence_type == ConfidenceType.MODEL_SCORE
        assert meta.confidence_band == ConfidenceBand.HIGH  # 0.85 >= threshold for model_score
        assert meta.raw_score == 0.85

    def test_get_confidence_metadata_with_calibration_override(self):
        """Providing calibration_method should upgrade type to CALIBRATED_PROBABILITY."""
        meta = get_confidence_metadata(
            "question-difficulty-v1", 0.70,
            source_tier="ml",
            calibration_method="temperature_scaling",
        )
        assert meta.confidence_type == ConfidenceType.CALIBRATED_PROBABILITY
        # 0.70 is MODERATE for calibrated probability
        assert meta.confidence_band == ConfidenceBand.MODERATE

    def test_deterministic_tier_uses_heuristic_type(self):
        """Deterministic tier should use HEURISTIC_CONFIDENCE."""
        meta = get_confidence_metadata("question-difficulty-v1", 0.65, source_tier="deterministic")
        assert meta.confidence_type == ConfidenceType.HEURISTIC_CONFIDENCE


# ═══════════════════════════════════════════════════════════════════════════
# 5. End-to-End: Model Inferences Include Confidence Metadata
# ═══════════════════════════════════════════════════════════════════════════

class TestModelInferenceConfidenceMetadata:
    """Test that every model's inference output includes confidence_metadata."""

    def test_difficulty_prediction_has_confidence_metadata(self):
        """question-difficulty-v1 inference must include confidence_metadata."""
        from ml.models.difficulty_predictor import QuestionDifficultyPredictor
        predictor = QuestionDifficultyPredictor()
        result = predictor.predict("Implement a binary search tree", allow_llm=False)
        assert "confidence_metadata" in result
        assert "confidence_band" in result
        meta = result["confidence_metadata"]
        assert meta["confidence_type"] in [t.value for t in ConfidenceType]
        assert result["confidence_band"] in [b.value for b in ConfidenceBand]

    def test_skill_classification_has_confidence_metadata(self):
        """question-skill-v1 inference must include confidence_metadata."""
        from ml.models.skill_classifier import QuestionSkillClassifier
        classifier = QuestionSkillClassifier()
        result = classifier.predict("Implement merge sort for a linked list")
        assert "confidence_metadata" in result
        assert "confidence_band" in result
        meta = result["confidence_metadata"]
        assert meta["confidence_type"] in [t.value for t in ConfidenceType]

    def test_concept_coverage_has_confidence_metadata(self):
        """answer-nli-v1 inference must include confidence_metadata."""
        from ml.models.concept_coverage import ConceptCoverageAnalyzer
        analyzer = ConceptCoverageAnalyzer()
        result = analyzer.evaluate_concepts(
            "A hash table uses a hash function to map keys to buckets",
            ["hash function", "collision handling", "time complexity"],
            allow_llm=False,
        )
        assert "confidence_metadata" in result
        assert "confidence_band" in result
        meta = result["confidence_metadata"]
        assert meta["confidence_type"] in [t.value for t in ConfidenceType]

    def test_defect_detection_has_confidence_metadata(self):
        """code-risk-v1 inference must include confidence_metadata."""
        from ml.models.defect_detector import CodeDefectDetector
        detector = CodeDefectDetector()
        result = detector.analyze_code("def add(a, b): return a + b", allow_llm=False)
        assert "confidence_metadata" in result
        assert "confidence_band" in result
        meta = result["confidence_metadata"]
        assert meta["confidence_type"] in [t.value for t in ConfidenceType]

    def test_mastery_model_has_confidence_metadata_unavailable(self):
        """mastery-v1 inference must include confidence_metadata typed as unavailable."""
        from ml.models.skill_mastery import ItemResponseTheoryMasteryModel
        irt = ItemResponseTheoryMasteryModel()
        result = irt.update_ability(current_theta=0.0, score=75, difficulty_level="intermediate")
        assert "confidence_metadata" in result
        assert "confidence_band" in result
        # Mastery model is typed as UNAVAILABLE
        assert result["confidence_metadata"]["confidence_type"] == ConfidenceType.UNAVAILABLE.value
        assert result["confidence_band"] == ConfidenceBand.INSUFFICIENT.value

    def test_mastery_model_has_uncertainty_note(self):
        """mastery-v1 must document that theta is NOT a confidence."""
        from ml.models.skill_mastery import ItemResponseTheoryMasteryModel
        irt = ItemResponseTheoryMasteryModel()
        result = irt.update_ability(current_theta=0.0, score=75, difficulty_level="intermediate")
        assert "uncertainty_note" in result
        assert "NOT a confidence" in result["uncertainty_note"]


# ═══════════════════════════════════════════════════════════════════════════
# 6. Production Labels
# ═══════════════════════════════════════════════════════════════════════════

class TestProductionLabels:
    """Verify production-grade labels are used, not false precision."""

    ALLOWED_BANDS = {"High confidence", "Moderate confidence", "Insufficient evidence"}

    def test_difficulty_uses_production_labels(self):
        """Difficulty predictor must use one of the three production labels."""
        from ml.models.difficulty_predictor import QuestionDifficultyPredictor
        predictor = QuestionDifficultyPredictor()
        result = predictor.predict("What is a variable?", allow_llm=False)
        assert result["confidence_band"] in self.ALLOWED_BANDS

    def test_defect_uses_production_labels(self):
        """Defect detector must use one of the three production labels."""
        from ml.models.defect_detector import CodeDefectDetector
        detector = CodeDefectDetector()
        result = detector.analyze_code("print('hello')", allow_llm=False)
        assert result["confidence_band"] in self.ALLOWED_BANDS

    def test_raw_confidence_not_presented_as_calibrated(self):
        """
        For uncalibrated models, confidence_type must NOT be 'calibrated_probability'
        unless explicit calibration has been performed.
        """
        from ml.models.difficulty_predictor import QuestionDifficultyPredictor
        predictor = QuestionDifficultyPredictor()
        result = predictor.predict("Explain polymorphism", allow_llm=False)
        meta = result["confidence_metadata"]
        # Without post-hoc calibration, it should NOT claim to be calibrated
        assert meta["confidence_type"] != "calibrated_probability"


# ═══════════════════════════════════════════════════════════════════════════
# 7. Documentation
# ═══════════════════════════════════════════════════════════════════════════

class TestDocumentation:
    """Verify that required documentation exists."""

    def test_confidence_glossary_exists(self):
        """docs/CONFIDENCE_GLOSSARY.md must exist."""
        glossary_path = PROJECT_ROOT / "docs" / "CONFIDENCE_GLOSSARY.md"
        assert glossary_path.exists(), f"CONFIDENCE_GLOSSARY.md not found at {glossary_path}"

    def test_glossary_covers_key_concepts(self):
        """Glossary must document all three key concepts."""
        glossary_path = PROJECT_ROOT / "docs" / "CONFIDENCE_GLOSSARY.md"
        content = glossary_path.read_text(encoding="utf-8")
        assert "Prediction Probability" in content
        assert "Confidence" in content
        assert "Candidate Skill Estimate" in content
        assert "theta" in content.lower() or "Theta" in content

    def test_glossary_documents_distinction(self):
        """Glossary must explain why softmax != calibrated confidence."""
        glossary_path = PROJECT_ROOT / "docs" / "CONFIDENCE_GLOSSARY.md"
        content = glossary_path.read_text(encoding="utf-8")
        assert "overconfident" in content.lower()
        assert "calibrat" in content.lower()  # calibration, calibrated, etc.

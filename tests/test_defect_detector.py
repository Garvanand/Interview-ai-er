"""
Comprehensive test suite for the CodeBERT Defect Detection ML component.

Tests the CodeDefectDetector inference module and integration points.
Exercises the fallback chain (fine-tuned → base model → AST heuristic)
and validates the output schema, risk band classification, and model versioning.
"""
from __future__ import annotations

import pytest
from typing import Dict, Any

from ml.models.defect_detector import (
    CodeDefectDetector,
    _classify_risk_band,
    LOW_RISK_THRESHOLD,
    HIGH_RISK_THRESHOLD,
    MODEL_VERSION,
)
from ml.features.code_features import extract_code_lexical_features


# ────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────

@pytest.fixture
def detector():
    """A fresh CodeDefectDetector instance (will use fallback if no model available)."""
    return CodeDefectDetector(device="cpu")


@pytest.fixture
def clean_python_code():
    return '''
def binary_search(arr, target):
    """Binary search for target in sorted array."""
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
'''


@pytest.fixture
def buggy_python_code():
    return '''
def broken_sort(lst):
    # Off-by-one error and missing return
    for i in range(len(lst)):
        for j in range(len(lst)):
            if lst[i] > lst[j]:
                lst[i], lst[j] = lst[j], lst[i]
    # Missing return statement
'''


@pytest.fixture
def syntax_error_code():
    return '''
def incomplete_function(x:
    return x + 1
    if x > 0
    print("done"
'''


@pytest.fixture
def recursive_code():
    return '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
'''


@pytest.fixture
def complex_code():
    """Large code with many lines and nested loops without error handling."""
    lines = [
        "def process_data(data):",
        "    results = []",
    ]
    for i in range(40):
        lines.append(f"    for item_{i} in data:")
        lines.append(f"        results.append(item_{i} * {i})")
    lines.append("    return results")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────────────
# Test 1: Output Schema Validation
# ────────────────────────────────────────────────────────────────────

class TestOutputSchema:
    """Verify the output format matches the specified contract."""

    def test_output_has_required_fields(self, detector, clean_python_code):
        """Output must contain all required fields from the spec."""
        result = detector.analyze_code(clean_python_code, language="python")

        assert "defect_probability" in result
        assert "risk_band" in result
        assert "model_version" in result
        assert "confidence" in result
        assert "inference_time_ms" in result
        assert "risk_indicators" in result
        assert "method" in result

    def test_defect_probability_range(self, detector, clean_python_code):
        """defect_probability must be between 0.0 and 1.0."""
        result = detector.analyze_code(clean_python_code)
        assert 0.0 <= result["defect_probability"] <= 1.0

    def test_risk_band_values(self, detector, clean_python_code):
        """risk_band must be one of low, medium, high."""
        result = detector.analyze_code(clean_python_code)
        assert result["risk_band"] in ("low", "medium", "high")

    def test_confidence_range(self, detector, clean_python_code):
        """confidence must be between 0.0 and 1.0."""
        result = detector.analyze_code(clean_python_code)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_inference_time_positive(self, detector, clean_python_code):
        """inference_time_ms must be non-negative."""
        result = detector.analyze_code(clean_python_code)
        assert result["inference_time_ms"] >= 0.0

    def test_model_version_present(self, detector, clean_python_code):
        """model_version must be a non-empty string."""
        result = detector.analyze_code(clean_python_code)
        assert isinstance(result["model_version"], str)
        assert len(result["model_version"]) > 0

    def test_signal_disclaimer_present(self, detector, clean_python_code):
        """Output must include a signal disclaimer."""
        result = detector.analyze_code(clean_python_code)
        assert "signal_disclaimer" in result
        assert "not proof" in result["signal_disclaimer"].lower()


# ────────────────────────────────────────────────────────────────────
# Test 2: Risk Band Classification
# ────────────────────────────────────────────────────────────────────

class TestRiskBandClassification:
    """Verify deterministic risk band thresholds."""

    def test_low_risk_band(self):
        assert _classify_risk_band(0.0) == "low"
        assert _classify_risk_band(0.10) == "low"
        assert _classify_risk_band(0.29) == "low"

    def test_medium_risk_band(self):
        assert _classify_risk_band(0.30) == "medium"
        assert _classify_risk_band(0.50) == "medium"
        assert _classify_risk_band(0.64) == "medium"

    def test_high_risk_band(self):
        assert _classify_risk_band(0.65) == "high"
        assert _classify_risk_band(0.80) == "high"
        assert _classify_risk_band(0.99) == "high"

    def test_boundary_values(self):
        assert _classify_risk_band(LOW_RISK_THRESHOLD - 0.001) == "low"
        assert _classify_risk_band(LOW_RISK_THRESHOLD) == "medium"
        assert _classify_risk_band(HIGH_RISK_THRESHOLD - 0.001) == "medium"
        assert _classify_risk_band(HIGH_RISK_THRESHOLD) == "high"


# ────────────────────────────────────────────────────────────────────
# Test 3: Clean Code Analysis
# ────────────────────────────────────────────────────────────────────

class TestCleanCode:
    """Clean, well-written code should generally produce low-to-medium risk."""

    def test_clean_code_risk_level(self, detector, clean_python_code):
        """Well-written binary search should not flag as high risk."""
        result = detector.analyze_code(clean_python_code, language="python")
        # In heuristic mode, clean valid Python should score low
        if result["method"] == "deterministic_ast_heuristic":
            assert result["defect_probability"] < HIGH_RISK_THRESHOLD

    def test_clean_code_no_syntax_indicators(self, detector, clean_python_code):
        """Clean code should not have syntax error indicators."""
        result = detector.analyze_code(clean_python_code, language="python")
        for indicator in result.get("risk_indicators", []):
            assert "syntax error" not in indicator.lower()


# ────────────────────────────────────────────────────────────────────
# Test 4: Syntax Error Detection
# ────────────────────────────────────────────────────────────────────

class TestSyntaxErrors:
    """Code with syntax errors should produce higher risk scores."""

    def test_syntax_error_detected(self, detector, syntax_error_code):
        """Code with Python syntax errors should flag risk."""
        result = detector.analyze_code(syntax_error_code, language="python")
        assert result["defect_probability"] > 0.3
        # Should have a syntax error indicator
        has_syntax_indicator = any(
            "syntax" in ind.lower() for ind in result.get("risk_indicators", [])
        )
        assert has_syntax_indicator

    def test_syntax_error_high_risk_band(self, detector, syntax_error_code):
        """Syntax-broken code should generally be medium or high risk."""
        result = detector.analyze_code(syntax_error_code, language="python")
        assert result["risk_band"] in ("medium", "high")


# ────────────────────────────────────────────────────────────────────
# Test 5: Recursive Code Detection
# ────────────────────────────────────────────────────────────────────

class TestRecursiveCode:
    """Recursive code should produce appropriate risk indicators."""

    def test_recursion_detected_in_indicators(self, detector, recursive_code):
        """Recursive functions should be noted in risk indicators."""
        result = detector.analyze_code(recursive_code, language="python")
        has_recursion_indicator = any(
            "recursive" in ind.lower() or "recursion" in ind.lower()
            for ind in result.get("risk_indicators", [])
        )
        assert has_recursion_indicator


# ────────────────────────────────────────────────────────────────────
# Test 6: Complex Code Analysis
# ────────────────────────────────────────────────────────────────────

class TestComplexCode:
    """Large, complex code should produce elevated risk."""

    def test_complex_code_elevated_risk(self, detector, complex_code):
        """Code with many lines and loops should have non-trivial risk."""
        result = detector.analyze_code(complex_code, language="python")
        assert result["defect_probability"] > 0.0
        assert len(result.get("risk_indicators", [])) >= 1


# ────────────────────────────────────────────────────────────────────
# Test 7: Confidence Computation
# ────────────────────────────────────────────────────────────────────

class TestConfidenceComputation:
    """Confidence should reflect distance from the decision boundary."""

    def test_extreme_defect_prob_high_confidence(self, detector):
        """Predictions near 0 or 1 should have high confidence."""
        conf = detector._compute_confidence(0.95)
        assert conf > 0.8

    def test_boundary_defect_prob_low_confidence(self, detector):
        """Predictions near 0.5 should have low confidence."""
        conf = detector._compute_confidence(0.50)
        assert conf < 0.1

    def test_zero_defect_prob_max_confidence(self, detector):
        """Prediction of 0.0 should have maximum confidence."""
        conf = detector._compute_confidence(0.0)
        assert abs(conf - 1.0) < 0.01

    def test_perfect_defect_prob_max_confidence(self, detector):
        """Prediction of 1.0 should have maximum confidence."""
        conf = detector._compute_confidence(1.0)
        assert abs(conf - 1.0) < 0.01


# ────────────────────────────────────────────────────────────────────
# Test 8: Lexical Features
# ────────────────────────────────────────────────────────────────────

class TestLexicalFeatures:
    """Verify the underlying lexical feature extraction."""

    def test_valid_python_syntax(self, clean_python_code):
        features = extract_code_lexical_features(clean_python_code, "python")
        assert features["syntax_valid"] is True

    def test_invalid_python_syntax(self, syntax_error_code):
        features = extract_code_lexical_features(syntax_error_code, "python")
        assert features["syntax_valid"] is False

    def test_loops_detected(self, clean_python_code):
        features = extract_code_lexical_features(clean_python_code, "python")
        assert features["has_loops"] is True

    def test_recursion_detected(self, recursive_code):
        features = extract_code_lexical_features(recursive_code, "python")
        assert features["has_recursion"] is True

    def test_no_recursion_in_iterative_code(self, clean_python_code):
        features = extract_code_lexical_features(clean_python_code, "python")
        assert features["has_recursion"] is False


# ────────────────────────────────────────────────────────────────────
# Test 9: Heuristic Fallback
# ────────────────────────────────────────────────────────────────────

class TestHeuristicFallback:
    """Verify the deterministic AST heuristic fallback works correctly."""

    def test_heuristic_returns_valid_score(self):
        """Heuristic should return a valid defect score."""
        lexical = {
            "syntax_valid": True,
            "has_recursion": False,
            "total_lines": 20,
            "non_empty_lines": 15,
            "has_loops": False,
            "has_try_except": False,
        }
        score = CodeDefectDetector._heuristic_defect_score(lexical)
        assert 0.0 <= score <= 1.0

    def test_heuristic_syntax_error_high_score(self):
        """Syntax errors should produce high heuristic score."""
        lexical = {
            "syntax_valid": False,
            "has_recursion": False,
            "total_lines": 10,
            "non_empty_lines": 8,
            "has_loops": False,
            "has_try_except": False,
        }
        score = CodeDefectDetector._heuristic_defect_score(lexical)
        assert score >= 0.6

    def test_heuristic_capped_at_099(self):
        """Heuristic score should never exceed 0.99."""
        lexical = {
            "syntax_valid": False,
            "has_recursion": True,
            "total_lines": 200,
            "non_empty_lines": 2,
            "has_loops": True,
            "has_try_except": False,
        }
        score = CodeDefectDetector._heuristic_defect_score(lexical)
        assert score <= 0.99


# ────────────────────────────────────────────────────────────────────
# Test 10: Model Info and Versioning
# ────────────────────────────────────────────────────────────────────

class TestModelInfo:
    """Verify model versioning and metadata reporting."""

    def test_model_info_structure(self, detector):
        """get_model_info should return complete metadata."""
        info = detector.get_model_info()
        assert "model_version" in info
        assert "is_fine_tuned" in info
        assert "fallback_mode" in info
        assert "device" in info
        assert "base_model" in info

    def test_model_version_string(self, detector):
        """Model version should contain the version prefix."""
        info = detector.get_model_info()
        assert "codebert_defect" in info["model_version"]


# ────────────────────────────────────────────────────────────────────
# Test 11: Non-Python Language Handling
# ────────────────────────────────────────────────────────────────────

class TestNonPythonLanguages:
    """Non-Python code should still produce valid output."""

    def test_javascript_code(self, detector):
        """JavaScript code should not crash the detector."""
        js_code = '''
function fibonacci(n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}
'''
        result = detector.analyze_code(js_code, language="javascript")
        assert 0.0 <= result["defect_probability"] <= 1.0
        assert result["risk_band"] in ("low", "medium", "high")

    def test_c_code(self, detector):
        """C code should produce valid output."""
        c_code = '''
int main() {
    int x = 10;
    char *ptr = NULL;
    *ptr = 'a';  // null pointer dereference
    return 0;
}
'''
        result = detector.analyze_code(c_code, language="c")
        assert "defect_probability" in result

    def test_empty_code(self, detector):
        """Empty code should produce a valid (low risk) result."""
        result = detector.analyze_code("", language="python")
        assert "defect_probability" in result
        assert result["risk_band"] in ("low", "medium", "high")


# ────────────────────────────────────────────────────────────────────
# Test 12: Integration with ML Inference Engine
# ────────────────────────────────────────────────────────────────────

class TestInferenceEngineIntegration:
    """Verify the detector integrates correctly with the MLInferenceEngine."""

    def test_inference_engine_detect_code_defects(self, clean_python_code):
        """MLInferenceEngine.detect_code_defects should return valid output."""
        from ml.inference.engine import MLInferenceEngine
        engine = MLInferenceEngine(device="cpu")
        result = engine.detect_code_defects(clean_python_code, language="python")

        assert "defect_probability" in result or "defect_risk_score" in result
        assert "latency_ms" in result

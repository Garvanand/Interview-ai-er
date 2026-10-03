"""
Comprehensive Test Suite for ML Fallback Resilience and Intelligence Tiers.

Simulates 6 specific failure modes across all ML components:
1. Model unavailable
2. Corrupted model artifact
3. Inference timeout
4. Invalid tokenizer
5. Out-of-memory (OOM)
6. Malformed input

Verifies:
- Three classes of intelligence: PRIMARY ML ("ml"), SECONDARY MODEL ("pretrained"/"deterministic"), LLM FALLBACK ("llm").
- Sources are explicitly labeled and never silently look identical to primary predictions.
- Confidence is authentic to the actual method; never manufactured.
- The interview remains fully usable when optional ML components fail.
"""
from __future__ import annotations

import os
import json
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from ml.fallbacks import (
    IntelligenceSource,
    try_llm_difficulty_fallback,
    try_llm_concept_coverage_fallback,
    try_llm_code_defect_fallback,
    DifficultyLLMSchema,
    ConceptCoverageLLMSchema,
    ConceptItemLLMSchema,
    CodeDefectLLMSchema,
)
from ml.models.difficulty_predictor import QuestionDifficultyPredictor
from ml.models.concept_coverage import ConceptCoverageAnalyzer
from ml.models.defect_detector import CodeDefectDetector
from ml.serving.inference_service import InferenceService
from app.ai.engine import AssessmentEngine
from app.ai.providers.base import AIProvider
from app.ai.schemas import AnswerEvaluation, CodeEvaluation


# ─────────────────────────────────────────────────────────────────────────────
# Mock AI Provider for Testing
# ─────────────────────────────────────────────────────────────────────────────

class MockGeminiProvider(AIProvider):
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    def generate_structured(self, prompt: str, schema: type, max_retries: int = 1, timeout_seconds: int = 5):
        if self.should_fail:
            raise RuntimeError("Gemini quota exceeded or network unavailable")

        if schema == DifficultyLLMSchema:
            data = DifficultyLLMSchema(
                difficulty="intermediate",
                confidence=0.72,
                reasoning="Covers tree traversal and recursion",
            )
            return data, {"provider": "mock-gemini"}

        elif schema == ConceptCoverageLLMSchema:
            data = ConceptCoverageLLMSchema(
                overall_coverage_pct=75.0,
                confidence=0.81,
                concept_results=[
                    ConceptItemLLMSchema(
                        concept="binary search tree",
                        status="covered",
                        score=0.85,
                        explanation="Correctly explained left/right child invariant.",
                    ),
                    ConceptItemLLMSchema(
                        concept="logarithmic complexity",
                        status="partially_covered",
                        score=0.50,
                        explanation="Mentioned O(log n) but didn't address degenerate cases.",
                    ),
                ],
            )
            return data, {"provider": "mock-gemini"}

        elif schema == CodeDefectLLMSchema:
            data = CodeDefectLLMSchema(
                defect_probability=0.25,
                risk_band="low",
                confidence=0.88,
                risk_indicators=["No boundary check on empty list"],
                analysis="Code is mostly clean with minor edge case omission",
            )
            return data, {"provider": "mock-gemini"}

        elif schema == AnswerEvaluation:
            return AnswerEvaluation(
                overall_score=82,
                technical_accuracy=85,
                conceptual_depth=80,
                problem_solving=80,
                communication=85,
                completeness=80,
                evidence="Clear explanation of core principles",
                strengths=["Clear explanation of core principles"],
                weaknesses=["Could elaborate on operational tradeoffs"],
                recommended_follow_up="How would you monitor this in production?",
                confidence=0.85,
            ), {"provider": "mock-gemini"}

        elif schema == CodeEvaluation:
            return CodeEvaluation(
                overall_score=88,
                correctness=90,
                algorithm_quality=85,
                complexity="Time: O(n), Space: O(1)",
                code_quality=88,
                readability=90,
                edge_case_coverage=85,
                testability=85,
                strengths=["Optimal time complexity", "Clean syntax"],
                issues=[],
                recommendations=["Add docstrings"],
                confidence=0.90,
            ), {"provider": "mock-gemini"}

        raise ValueError(f"Unknown schema in mock provider: {schema}")

    def get_metadata(self):
        return {"provider": "mock-gemini", "model_name": "gemini-2.5-flash"}


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite 1: Failure Mode — Model Unavailable
# ─────────────────────────────────────────────────────────────────────────────

class TestModelUnavailable:
    """Verifies graceful fallback when model files or checkpoints are missing."""

    def test_difficulty_predictor_model_unavailable(self):
        predictor = QuestionDifficultyPredictor(weights_path="non/existent/model_weights.joblib")
        result = predictor.predict("Explain how dynamic programming solves the knapsack problem.")

        # Must NOT claim primary ML
        assert result["source"] in (IntelligenceSource.PRETRAINED.value, IntelligenceSource.DETERMINISTIC.value)
        assert result["source"] != IntelligenceSource.ML.value
        assert "difficulty" in result
        assert result["difficulty"] in ("beginner", "intermediate", "advanced")
        # Confidence must be authentic to the fallback method, never 1.0
        assert 0.0 < result["confidence"] < 1.0

    def test_concept_coverage_deberta_unavailable(self):
        analyzer = ConceptCoverageAnalyzer()
        # With DeBERTa cross-encoder unavailable, must fall back to MiniLM or deterministic
        result = analyzer.evaluate_concepts(
            "Database indexing uses B-trees to provide logarithmic search lookup.",
            ["database indexing reduces search space", "B-tree enables logarithmic lookup"]
        )

        assert result["source"] in (IntelligenceSource.PRETRAINED.value, IntelligenceSource.DETERMINISTIC.value)
        assert result["source"] != IntelligenceSource.ML.value
        assert "overall_coverage_pct" in result
        assert result["overall_coverage_pct"] > 30.0
        assert 0.0 <= result["confidence"] <= 1.0

    def test_code_defect_detector_weights_unavailable(self):
        detector = CodeDefectDetector(model_path="non/existent/codebert_defect")
        result = detector.analyze_code("def add(a, b):\n    return a + b\n")

        assert result["source"] in (IntelligenceSource.PRETRAINED.value, IntelligenceSource.DETERMINISTIC.value)
        assert result["source"] != IntelligenceSource.ML.value
        assert result["risk_band"] in ("low", "medium", "high")
        assert 0.0 <= result["defect_probability"] <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite 2: Failure Mode — Corrupted Model Artifact
# ─────────────────────────────────────────────────────────────────────────────

class TestCorruptedArtifact:
    """Verifies that corrupted weight files do not crash the system."""

    def test_difficulty_predictor_corrupted_joblib(self):
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            f.write(b"CORRUPTED_NON_PICKLE_BINARY_DATA_XYZ_123")
            temp_path = f.name

        try:
            predictor = QuestionDifficultyPredictor(weights_path=temp_path)
            # Should safely catch corruption during load and fall back
            result = predictor.predict("What is the time complexity of quicksort?")
            assert result["source"] in (IntelligenceSource.PRETRAINED.value, IntelligenceSource.DETERMINISTIC.value)
            assert result["difficulty"] in ("beginner", "intermediate", "advanced")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_code_defect_corrupted_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.json")
            with open(config_path, "w") as f:
                f.write("{ INVALID JSON CORRUPTED ...")

            detector = CodeDefectDetector(model_path=temp_dir)
            result = detector.analyze_code("def foo():\n    return 42\n")

            # Must fall back from corrupted fine-tuned model
            assert result["source"] != IntelligenceSource.ML.value
            assert result["source"] in (IntelligenceSource.PRETRAINED.value, IntelligenceSource.DETERMINISTIC.value)
            assert result["risk_band"] in ("low", "medium", "high")


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite 3: Failure Mode — Inference Timeout
# ─────────────────────────────────────────────────────────────────────────────

class TestInferenceTimeout:
    """Verifies execution timeout boundaries in InferenceService and components."""

    def test_inference_service_raises_timeout(self):
        def slow_func(model):
            import time
            time.sleep(0.5)
            return "done"

        with pytest.raises(TimeoutError) as exc_info:
            InferenceService.execute("semantic-answer-similarity-v1", slow_func, timeout_seconds=0.02)
        assert "timed out after" in str(exc_info.value)

    def test_concept_coverage_timeout_falls_back(self):
        analyzer = ConceptCoverageAnalyzer()

        with patch("ml.serving.inference_service.InferenceService.execute") as mock_exec:
            mock_exec.side_effect = TimeoutError("Inference timed out after 0.1s")
            result = analyzer.evaluate_concepts(
                "Binary search cuts the search space in half each iteration.",
                ["binary search halves search space", "logarithmic complexity"]
            )

            # Successfully fell back to deterministic lexical without crashing
            assert result["source"] == IntelligenceSource.DETERMINISTIC.value
            assert result["method"] == "lexical_nli_fallback"
            assert result["overall_coverage_pct"] > 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite 4: Failure Mode — Invalid Tokenizer
# ─────────────────────────────────────────────────────────────────────────────

class TestInvalidTokenizer:
    """Verifies handling when tokenizer throws unexpected encoding exceptions."""

    def test_code_defect_tokenizer_failure(self):
        detector = CodeDefectDetector()
        detector._load_attempted = True
        detector._model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_tokenizer.side_effect = ValueError("Invalid tokenizer vocabulary index: [UNK]")
        detector._tokenizer = mock_tokenizer

        # Should catch tokenizer exception and fall back to deterministic AST
        result = detector.analyze_code("def broken_code(): pass")
        assert result["source"] == IntelligenceSource.DETERMINISTIC.value
        assert result["method"] == "deterministic_ast_heuristic"
        assert result["risk_band"] in ("low", "medium", "high")


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite 5: Failure Mode — Out-of-Memory (OOM)
# ─────────────────────────────────────────────────────────────────────────────

class TestOutOfMemory:
    """Verifies memory exhaustion handling and automatic fallback."""

    def test_concept_coverage_oom_fallback(self):
        analyzer = ConceptCoverageAnalyzer()

        with patch.object(analyzer, "_try_deberta_primary", return_value=None):
            with patch("ml.serving.inference_service.InferenceService.execute") as mock_exec:
                mock_exec.side_effect = MemoryError("CUDA out of memory while allocating tensor")
                result = analyzer.evaluate_concepts(
                    "QuickSort partitions around a pivot element.",
                    ["partitioning around pivot", "average case O(n log n)"]
                )

                # Gracefully recovered to deterministic lexical fallback
                assert result["source"] == IntelligenceSource.DETERMINISTIC.value
                assert result["method"] == "lexical_nli_fallback"
                assert "overall_coverage_pct" in result

    def test_code_defect_oom_fallback(self):
        detector = CodeDefectDetector()
        with patch.object(detector, "_run_codebert_inference") as mock_infer:
            mock_infer.side_effect = MemoryError("Out of memory on forward pass")
            detector._model = MagicMock()

            result = detector.analyze_code("def compute():\n    return [x*2 for x in range(10)]\n")
            assert result["source"] == IntelligenceSource.DETERMINISTIC.value
            assert result["method"] == "deterministic_ast_heuristic"


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite 6: Failure Mode — Malformed Input
# ─────────────────────────────────────────────────────────────────────────────

class TestMalformedInput:
    """Verifies system stability against malformed, non-string, null, or extreme inputs."""

    def test_difficulty_malformed_input(self):
        predictor = QuestionDifficultyPredictor()

        # None input
        res_none = predictor.predict(None)
        assert res_none["source"] == IntelligenceSource.UNAVAILABLE.value
        assert res_none["confidence"] == 0.0

        # Integer input
        res_int = predictor.predict(4242)
        assert res_int["source"] == IntelligenceSource.UNAVAILABLE.value
        assert res_int["confidence"] == 0.0

        # Empty / whitespace
        res_empty = predictor.predict("   ")
        assert res_empty["source"] == IntelligenceSource.UNAVAILABLE.value
        assert res_empty["confidence"] == 0.0

    def test_concept_coverage_malformed_input(self):
        analyzer = ConceptCoverageAnalyzer()

        # Non-string candidate answer
        res_bad_ans = analyzer.evaluate_concepts(12345, ["concept a"])
        assert res_bad_ans["source"] == IntelligenceSource.UNAVAILABLE.value
        assert res_bad_ans["confidence"] == 0.0

        # Non-list expected concepts
        res_bad_concepts = analyzer.evaluate_concepts("valid answer", "not a list")
        assert res_bad_concepts["source"] == IntelligenceSource.UNAVAILABLE.value
        assert res_bad_concepts["confidence"] == 0.0

        # Empty rubric -> 100% trivial coverage
        res_empty_rubric = analyzer.evaluate_concepts("some answer", [])
        assert res_empty_rubric["source"] == IntelligenceSource.DETERMINISTIC.value
        assert res_empty_rubric["overall_coverage_pct"] == 100.0

    def test_code_defect_malformed_input(self):
        detector = CodeDefectDetector()

        # None code
        res_none = detector.analyze_code(None)
        assert res_none["source"] == IntelligenceSource.UNAVAILABLE.value
        assert res_none["confidence"] == 0.0
        assert res_none["risk_band"] == "unknown"

        # Non-string code
        res_dict = detector.analyze_code({"code": "def foo(): pass"})
        assert res_dict["source"] == IntelligenceSource.UNAVAILABLE.value
        assert res_dict["confidence"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite 7: LLM Fallback (Tier 3)
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMFallback:
    """Verifies structured Gemini reasoning fallback for all 3 components."""

    @patch("app.ai.providers.get_ai_provider")
    def test_llm_difficulty_fallback(self, mock_get_provider):
        mock_get_provider.return_value = MockGeminiProvider()
        result = try_llm_difficulty_fallback("How does Paxos handle network partitions?")

        assert result is not None
        assert result["source"] == IntelligenceSource.LLM.value
        assert result["difficulty"] == "intermediate"
        assert result["confidence"] == 0.72
        assert "reasoning" in result
        assert result["method"] == "gemini_structured_reasoning"

    @patch("app.ai.providers.get_ai_provider")
    def test_llm_concept_coverage_fallback(self, mock_get_provider):
        mock_get_provider.return_value = MockGeminiProvider()
        result = try_llm_concept_coverage_fallback(
            "BST nodes have left child smaller and right child greater.",
            ["binary search tree", "logarithmic complexity"]
        )

        assert result is not None
        assert result["source"] == IntelligenceSource.LLM.value
        assert result["overall_coverage_pct"] == 75.0
        assert result["confidence"] == 0.81
        assert len(result["concept_results"]) == 2
        assert result["covered_concepts"] == ["binary search tree"]

    @patch("app.ai.providers.get_ai_provider")
    def test_llm_code_defect_fallback(self, mock_get_provider):
        mock_get_provider.return_value = MockGeminiProvider()
        result = try_llm_code_defect_fallback("def find_max(lst):\n    return max(lst)\n")

        assert result is not None
        assert result["source"] == IntelligenceSource.LLM.value
        assert result["defect_probability"] == 0.25
        assert result["risk_band"] == "low"
        assert result["confidence"] == 0.88
        assert "No boundary check on empty list" in result["risk_indicators"]


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite 8: End-to-End Interview Usability
# ─────────────────────────────────────────────────────────────────────────────

class TestInterviewUsabilityWhenMLFails:
    """Verifies that the candidate interview remains fully usable even when all ML models fail."""

    def test_evaluate_answer_survives_complete_ml_failure(self):
        engine = AssessmentEngine(provider=MockGeminiProvider())

        # Simulate complete failure of Hybrid ML evidence generation
        with patch("ml.pipelines.hybrid_assessment.HybridAssessmentPipeline.generate_ml_evidence") as mock_pipeline:
            mock_pipeline.side_effect = RuntimeError("All ML GPU/CPU workers offline")

            evaluation = engine.evaluate_answer(
                question="Explain the difference between TCP and UDP.",
                answer="TCP is connection-oriented and reliable, while UDP is connectionless and faster.",
                question_type="technical"
            )

            # Evaluation must complete successfully despite ML failure!
            assert evaluation is not None
            assert evaluation["overall_score"] == 82
            assert "strengths" in evaluation
            assert "weaknesses" in evaluation

    def test_evaluate_code_survives_complete_ml_failure(self):
        engine = AssessmentEngine(provider=MockGeminiProvider())

        # Simulate CodeDefectDetector throwing an unhandled error
        with patch("ml.models.defect_detector.CodeDefectDetector.analyze_code") as mock_defect:
            mock_defect.side_effect = RuntimeError("CodeBERT CUDA error: out of memory")

            evaluation = engine.evaluate_code(
                code="def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen: return [seen[target-n], i]\n        seen[n] = i\n",
                language="python",
                question="Given an array of integers, return indices of the two numbers that add up to target."
            )

            # Code evaluation must complete successfully and provide feedback!
            assert evaluation is not None
            assert evaluation["overall_score"] == 88
            assert "complexity" in evaluation
            assert len(evaluation["strengths"]) > 0

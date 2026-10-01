"""
Tests for the ML layer components, inference engines, and mathematical fallbacks.
"""
from __future__ import annotations

import pytest
from ml.inference.engine import MLInferenceEngine
from ml.models.registry import MLModelRegistry, ModelCategory, HardwareTarget
from ml.models.skill_mastery import ItemResponseTheoryMasteryModel
from ml.models.adaptive_selector import AdaptiveQuestionSelector
from ml.features.text_embeddings import compute_cosine_similarity
from ml.evaluation.metrics import (
    compute_classification_metrics,
    compute_regression_metrics,
    compute_coverage_calibration_error
)
from ml.pipelines.interview_ml_pipeline import InterviewMLPipeline


def test_model_registry_integrity():
    models = MLModelRegistry.list_all()
    assert len(models) == 8

    # Verify each category is properly set
    categories = {m.category for m in models}
    assert ModelCategory.TRAINED_BY_US in categories
    assert ModelCategory.PRETRAINED in categories
    assert ModelCategory.FINE_TUNED_BY_US in categories

    # Verify all expected model IDs exist
    expected_ids = [
        "question-difficulty-v1",
        "question-skill-classifier-v1",
        "answer-concept-coverage-v1",
        "semantic-answer-similarity-v1",
        "code-defect-detector-v1",
        "voice-stt-whisper-v1",
        "candidate-skill-mastery-irt-v1",
        "adaptive-question-selector-v1",
    ]
    for mid in expected_ids:
        assert MLModelRegistry.get(mid) is not None


def test_question_difficulty_inference():
    engine = MLInferenceEngine()
    result = engine.predict_question_difficulty("Explain the difference between useState and useEffect in React.")
    assert "difficulty" in result
    assert result["difficulty"] in ("beginner", "intermediate", "advanced")
    assert "latency_ms" in result


def test_skill_classification_inference():
    engine = MLInferenceEngine()
    result = engine.classify_question_skills("Design a distributed caching system using Redis and consistent hashing.")
    assert "top_skills" in result
    assert len(result["top_skills"]) > 0
    assert "system-design" in result["top_skills"] or "algorithms" in result["top_skills"]


def test_concept_coverage_analyzer():
    engine = MLInferenceEngine()
    answer = "In a distributed system, Raft uses leader election and log replication to ensure consensus."
    concepts = ["leader election", "log replication", "sharding"]
    res = engine.evaluate_concept_coverage(answer, concepts)
    assert "overall_coverage_pct" in res
    assert "concept_scores" in res
    assert 0.0 <= res["overall_coverage_pct"] <= 100.0


def test_semantic_similarity():
    engine = MLInferenceEngine()
    text_a = "Binary search runs in logarithmic time O(log n)."
    text_b = "The time complexity of binary search is O(log N)."
    res = engine.compute_semantic_similarity(text_a, text_b)
    assert "similarity_score" in res
    assert 0.0 <= res["similarity_score"] <= 1.0


def test_code_defect_detector():
    engine = MLInferenceEngine()
    valid_code = "def add(a, b):\n    return a + b\n"
    res = engine.detect_code_defects(valid_code, "python")
    assert "defect_risk_score" in res
    assert 0.0 <= res["defect_risk_score"] <= 1.0

    broken_code = "def broken(:\n    return\n"
    broken_res = engine.detect_code_defects(broken_code, "python")
    assert broken_res["defect_risk_score"] > 0.5


def test_irt_mastery_model():
    irt = ItemResponseTheoryMasteryModel()
    # Candidate starting at average ability theta = 0.0
    # Answers advanced question with high score (95/100) -> ability should increase
    res = irt.update_ability(current_theta=0.0, score=95.0, difficulty_level="advanced")
    assert res["updated_theta"] > res["previous_theta"]
    assert res["estimated_proficiency"] > 50.0

    # Answers beginner question with poor score (10/100) -> ability should decrease
    res_down = irt.update_ability(current_theta=0.0, score=10.0, difficulty_level="beginner")
    assert res_down["updated_theta"] < res_down["previous_theta"]


def test_adaptive_question_selector():
    selector = AdaptiveQuestionSelector()
    pool = [
        {"id": "q1", "difficulty": "beginner", "skill_focus": "algorithms", "discrimination": 1.2},
        {"id": "q2", "difficulty": "intermediate", "skill_focus": "algorithms", "discrimination": 1.5},
        {"id": "q3", "difficulty": "advanced", "skill_focus": "concurrency", "discrimination": 1.8},
    ]
    # For a high-ability candidate (theta = 1.5), advanced question should yield highest information
    decision = selector.select_next_question(
        candidate_theta=1.5,
        candidate_questions_pool=pool,
        asked_question_ids=[],
        target_skills=["algorithms", "concurrency"],
        skill_coverage_counts={"algorithms": 2, "concurrency": 0},
        exploration_prob=0.0  # pure exploitation
    )
    assert decision["selected_question"] is not None
    assert decision["selected_question"]["id"] == "q3"


def test_evaluation_metrics():
    # Classification metrics
    clf_res = compute_classification_metrics(["a", "b", "a"], ["a", "b", "b"])
    assert "accuracy" in clf_res
    assert clf_res["accuracy"] == pytest.approx(0.6667, abs=1e-3)

    # Regression metrics
    reg_res = compute_regression_metrics([1.0, 2.0], [1.1, 1.9])
    assert "mae" in reg_res
    assert "rmse" in reg_res

    # Calibration error
    ece = compute_coverage_calibration_error([0.8, 0.2], [1, 0])
    assert 0.0 <= ece <= 1.0


def test_interview_ml_pipeline_end_to_end():
    pipeline = InterviewMLPipeline()
    # Process question
    q_meta = pipeline.process_incoming_question("Implement a red-black tree with rotational rebalancing.")
    assert "predicted_difficulty" in q_meta
    assert "detected_skills" in q_meta

    # Process submission
    sub_eval = pipeline.evaluate_candidate_submission(
        question_text="Implement a red-black tree with rotational rebalancing.",
        response_text="Red-black trees maintain balance using color flips and left or right rotations.",
        expected_concepts=["rotations", "color flips", "balance invariant"],
        reference_answer="A red-black tree uses rotations to maintain O(log n) height.",
        is_code=False
    )
    assert "concept_coverage" in sub_eval
    assert "reference_similarity" in sub_eval

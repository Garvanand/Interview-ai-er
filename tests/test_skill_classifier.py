"""
Tests for TACO Multi-Label Question-Skill Classification and Pipeline Integration.
"""
from __future__ import annotations

import json
import os
import pytest
from pathlib import Path

from ml.datasets.taco_loader import (
    TACODatasetLoader,
    CANONICAL_SKILLS,
    map_to_canonical_skills
)
from ml.models.skill_classifier import QuestionSkillClassifier
from app.services.question_skill_service import QuestionSkillService
from app.services.supabase_service import SupabaseService


def test_canonical_taxonomy_composition():
    """Verify that all 21 canonical skills are defined."""
    expected_skills = [
        "arrays", "hashing", "strings", "sorting", "search",
        "two_pointers", "sliding_window", "trees", "graphs",
        "dynamic_programming", "greedy", "backtracking", "heaps",
        "stacks", "queues", "linked_lists", "binary_search",
        "recursion", "complexity", "data_structures", "algorithms"
    ]
    assert len(CANONICAL_SKILLS) == 21
    for skill in expected_skills:
        assert skill in CANONICAL_SKILLS


def test_taxonomy_mapping_layer():
    """Verify mapping layer maps raw TACO tags & skill_types into canonical skills."""
    # Test raw tags from TACO
    mapped_dp = map_to_canonical_skills(tags=["Dynamic programming"], question_text="")
    assert "dynamic_programming" in mapped_dp
    assert "algorithms" in mapped_dp

    mapped_trees = map_to_canonical_skills(tags=["Spanning trees", "Data structures"], question_text="")
    assert "trees" in mapped_trees
    assert "data_structures" in mapped_trees

    mapped_search = map_to_canonical_skills(skill_types=["Complete search"], question_text="")
    assert "search" in mapped_search

    # Test text signals
    text_q = "Find the maximum sum of any contiguous subarray of size k using a sliding window."
    mapped_window = map_to_canonical_skills(tags=[], skill_types=[], question_text=text_q)
    assert "sliding_window" in mapped_window


def test_trained_skill_classifier_inference_schema():
    """Verify the classifier output matches the required inference output schema."""
    classifier = QuestionSkillClassifier()
    assert classifier._model is not None, "Model weights should be loaded"

    question = "Given an array of integers nums and an integer amount, compute the minimum coins needed using dynamic programming."
    result = classifier.predict(question)

    # Required inference schema:
    # {
    #   "skills": [
    #     {
    #       "skill": "dynamic_programming",
    #       "confidence": 0.91
    #     }
    #   ]
    # }
    assert "skills" in result
    assert isinstance(result["skills"], list)
    assert len(result["skills"]) > 0

    first = result["skills"][0]
    assert "skill" in first
    assert "confidence" in first
    assert isinstance(first["skill"], str)
    assert isinstance(first["confidence"], float)
    assert 0.0 <= first["confidence"] <= 1.0

    # Verify canonical skills membership
    for item in result["skills"]:
        assert item["skill"] in CANONICAL_SKILLS

    # Ensure dynamic_programming is recognized
    detected = [s["skill"] for s in result["skills"]]
    assert "dynamic_programming" in detected or "algorithms" in detected


def test_skill_classifier_heuristic_fallback():
    """Verify deterministic fallback works when no weights are loaded."""
    classifier = QuestionSkillClassifier(weights_path="/non_existent/path.joblib")
    assert classifier._model is None

    result = classifier.predict("Traverse a binary tree using breadth-first search and a queue.")
    assert "skills" in result
    detected = [s["skill"] for s in result["skills"]]
    assert "trees" in detected or "queues" in detected


def test_question_skill_service_predict_and_persist():
    """Verify QuestionSkillService derives and persists ML metadata while keeping source metadata separate."""
    supabase = SupabaseService()
    service = QuestionSkillService(supabase)

    question_id = "test-ml-qid-555"
    question_text = "Implement Dijkstra's shortest path algorithm on a weighted directed graph using a min-heap priority queue."

    res = service.predict_and_persist(question_id, question_text)

    # Check returned structure
    assert res["question_id"] == question_id
    assert "predicted_skills" in res
    assert "confidence" in res
    assert "model_version" in res
    assert "timestamp" in res
    assert len(res["predicted_skills"]) > 0

    detected_names = [s["skill"] for s in res["predicted_skills"]]
    assert "graphs" in detected_names or "heaps" in detected_names

    # Check persistence in Supabase / local cache
    persisted = supabase.get_question_skill_prediction(question_id)
    assert persisted is not None
    assert persisted["question_id"] == question_id
    assert persisted["model_version"] == res["model_version"]
    assert persisted["confidence"] == res["confidence"]
    assert persisted["timestamp"] == res["timestamp"]
    assert persisted["predicted_skills"] == res["predicted_skills"]


def test_evaluation_metrics_report_completeness():
    """Verify that the evaluation report contains all required metrics."""
    eval_file = Path("ml/models/weights/skill_evaluation.json")
    assert eval_file.exists(), "Evaluation report JSON must exist"

    with open(eval_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    baseline = data.get("classical_baseline", {})
    assert "micro_f1" in baseline
    assert "macro_f1" in baseline
    assert "hamming_loss" in baseline
    assert "precision" in baseline
    assert "recall" in baseline
    assert "per_label" in baseline

    assert baseline["micro_f1"] > 0.50
    assert baseline["hamming_loss"] < 0.15

    # Verify all 21 canonical skills exist in per_label
    for skill in CANONICAL_SKILLS:
        assert skill in baseline["per_label"], f"Missing per-label metric for {skill}"
        skill_metric = baseline["per_label"][skill]
        assert "f1" in skill_metric
        assert "precision" in skill_metric
        assert "recall" in skill_metric
        assert "support" in skill_metric

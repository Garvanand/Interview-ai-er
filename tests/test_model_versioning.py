"""
Tests for lightweight model versioning and historical evaluation immutability.

Confirms:
1. Every inference stored in the database is attributable to an explicit model version.
2. Canonical identifiers:
   - question-difficulty-v1
   - question-skill-v1
   - answer-nli-v1
   - code-risk-v1
   - mastery-v1
3. Persisted fields:
   - model_name
   - model_version
   - dataset_version
   - training_run
   - inference_timestamp
4. Historical evaluations retain their original model version after a newer model is deployed.
5. Historical model results are NEVER overwritten.
6. Machine-readable registry and docs/MODEL_REGISTRY.md integrity.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
import pytest

from ml.versioning import ModelVersionRegistry, get_registry, stamp_inference
from ml.models.difficulty_predictor import QuestionDifficultyPredictor
from ml.models.skill_classifier import QuestionSkillClassifier
from ml.models.concept_coverage import ConceptCoverageAnalyzer
from ml.models.defect_detector import CodeDefectDetector
from ml.models.skill_mastery import ItemResponseTheoryMasteryModel
from ml.models.registry import MLModelRegistry
from app.services.supabase_service import SupabaseService
from app.services.question_skill_service import QuestionSkillService


REQUIRED_ATTRIBUTION_FIELDS = [
    "model_name",
    "model_version",
    "dataset_version",
    "training_run",
    "inference_timestamp",
]

CANONICAL_MODEL_IDS = [
    "question-difficulty-v1",
    "question-skill-v1",
    "answer-nli-v1",
    "code-risk-v1",
    "mastery-v1",
]


# ── 1. REGISTRY INTEGRITY TESTS ─────────────────────────────────────

def test_machine_readable_registry_exists_and_valid():
    """Confirms machine-readable registry file exists, parses, and contains all 5 models."""
    registry_path = Path("ml/model_registry.json")
    assert registry_path.exists(), "ml/model_registry.json must exist"

    with open(registry_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "models" in data
    models = data["models"]
    for mid in CANONICAL_MODEL_IDS:
        assert mid in models, f"Model '{mid}' must be registered in ml/model_registry.json"
        entry = models[mid]
        for field in ["model_name", "model_version", "dataset_version", "training_run", "status"]:
            assert field in entry, f"Field '{field}' missing from model '{mid}' in registry"
        assert entry["status"] == "active"


def test_markdown_model_registry_docs_exist():
    """Confirms docs/MODEL_REGISTRY.md exists and documents all 5 canonical models."""
    docs_path = Path("docs/MODEL_REGISTRY.md")
    assert docs_path.exists(), "docs/MODEL_REGISTRY.md must exist"

    content = docs_path.read_text(encoding="utf-8")
    for mid in CANONICAL_MODEL_IDS:
        assert mid in content, f"docs/MODEL_REGISTRY.md must document '{mid}'"
    assert "model_name" in content
    assert "model_version" in content
    assert "dataset_version" in content
    assert "training_run" in content
    assert "inference_timestamp" in content


def test_model_registry_aliases_and_lookup():
    """Confirms ModelVersionRegistry correctly resolves canonical IDs and legacy aliases."""
    registry = ModelVersionRegistry.get_instance()
    for mid in CANONICAL_MODEL_IDS:
        entry = registry.get_model_entry(mid)
        assert entry is not None, f"Registry must resolve '{mid}'"
        assert entry["model_name"] == mid

    # Test legacy alias resolution
    assert registry.resolve_model_name("question-skill-classifier-v1") == "question-skill-v1"
    assert registry.resolve_model_name("answer-concept-coverage-v1") == "answer-nli-v1"
    assert registry.resolve_model_name("code-defect-detector-v1") == "code-risk-v1"
    assert registry.resolve_model_name("candidate-skill-mastery-irt-v1") == "mastery-v1"

    # Test MLModelRegistry lookup
    for mid in CANONICAL_MODEL_IDS:
        meta = MLModelRegistry.get(mid)
        assert meta is not None, f"MLModelRegistry.get('{mid}') must not be None"


# ── 2. INFERENCE ATTRIBUTION TESTS FOR ALL 5 MODELS ────────────────

def test_question_difficulty_inference_has_attribution():
    """question-difficulty-v1 must stamp all 5 attribution fields."""
    predictor = QuestionDifficultyPredictor()
    result = predictor.predict("Explain the difference between TCP and UDP.")
    
    for field in REQUIRED_ATTRIBUTION_FIELDS:
        assert field in result, f"Field '{field}' missing from difficulty inference result"
    assert result["model_name"] == "question-difficulty-v1"
    assert len(result["model_version"]) > 0
    assert len(result["dataset_version"]) > 0
    assert len(result["training_run"]) > 0
    assert "T" in result["inference_timestamp"]  # Valid ISO timestamp


def test_question_skill_inference_has_attribution():
    """question-skill-v1 must stamp all 5 attribution fields."""
    classifier = QuestionSkillClassifier()
    result = classifier.predict("Implement an LRU cache with O(1) get and put operations.")
    
    for field in REQUIRED_ATTRIBUTION_FIELDS:
        assert field in result, f"Field '{field}' missing from skill inference result"
    assert result["model_name"] == "question-skill-v1"
    assert len(result["model_version"]) > 0
    assert len(result["dataset_version"]) > 0
    assert len(result["training_run"]) > 0
    assert "T" in result["inference_timestamp"]


def test_answer_nli_inference_has_attribution():
    """answer-nli-v1 must stamp all 5 attribution fields."""
    analyzer = ConceptCoverageAnalyzer()
    result = analyzer.evaluate_concepts(
        candidate_answer="A hash table provides O(1) average lookup time using a hash function.",
        expected_concepts=["hash function", "average constant time lookup", "collision handling"]
    )
    
    for field in REQUIRED_ATTRIBUTION_FIELDS:
        assert field in result, f"Field '{field}' missing from answer NLI inference result"
    assert result["model_name"] == "answer-nli-v1"
    assert len(result["model_version"]) > 0
    assert len(result["dataset_version"]) > 0
    assert len(result["training_run"]) > 0
    assert "T" in result["inference_timestamp"]


def test_code_risk_inference_has_attribution():
    """code-risk-v1 must stamp all 5 attribution fields."""
    detector = CodeDefectDetector()
    result = detector.analyze_code("def add(a, b): return a + b", language="python")
    
    for field in REQUIRED_ATTRIBUTION_FIELDS:
        assert field in result, f"Field '{field}' missing from code risk inference result"
    assert result["model_name"] == "code-risk-v1"
    assert len(result["model_version"]) > 0
    assert len(result["dataset_version"]) > 0
    assert len(result["training_run"]) > 0
    assert "T" in result["inference_timestamp"]


def test_mastery_irt_inference_has_attribution():
    """mastery-v1 must stamp all 5 attribution fields."""
    irt = ItemResponseTheoryMasteryModel()
    result = irt.update_ability(current_theta=0.0, score=85.0, difficulty_level="intermediate")
    
    for field in REQUIRED_ATTRIBUTION_FIELDS:
        assert field in result, f"Field '{field}' missing from IRT mastery result"
    assert result["model_name"] == "mastery-v1"
    assert len(result["model_version"]) > 0
    assert len(result["dataset_version"]) > 0
    assert len(result["training_run"]) > 0
    assert "T" in result["inference_timestamp"]


# ── 3. DATABASE PERSISTENCE & HISTORICAL IMMUTABILITY TESTS ─────────

def test_database_persistence_persists_attribution_fields():
    """
    Confirms that storing an answer evaluation in the database (or fallback cache)
    persists model_name, model_version, dataset_version, training_run, and inference_timestamp.
    """
    supabase = SupabaseService()
    session_id = f"test-sess-{uuid.uuid4()}"
    question_id = f"test-q-{uuid.uuid4()}"
    
    # Initialize session and question in service
    supabase.create_local_session(session_id, user_id=f"user-{uuid.uuid4()}")
    supabase._local_questions[session_id] = [{
        "id": question_id,
        "question_text": "What is the time complexity of binary search?",
        "difficulty": "intermediate",
    }]
    
    evaluation = {
        "score": 90,
        "feedback": "Accurate explanation of logarithmic complexity.",
        "model_name": "answer-nli-v1",
        "model_version": "1.0.0",
        "dataset_version": "mnli-snli-v1",
        "training_run": "answer-nli-v1_pretrained_deberta_minilm",
        "inference_timestamp": "2026-10-03T10:00:00+00:00",
    }
    
    success = supabase.store_answer(
        session_id=session_id,
        question_id=question_id,
        answer_text="Binary search runs in O(log n) time by halving the search space.",
        evaluation=evaluation,
    )
    assert success is True
    
    # Verify stored question
    stored_questions = supabase.get_session_questions(session_id)
    assert len(stored_questions) == 1
    stored_q = stored_questions[0]
    
    eval_details = stored_q.get("evaluation_details")
    assert eval_details is not None
    assert eval_details["model_name"] == "answer-nli-v1"
    assert eval_details["model_version"] == "1.0.0"
    assert eval_details["dataset_version"] == "mnli-snli-v1"
    assert eval_details["training_run"] == "answer-nli-v1_pretrained_deberta_minilm"
    assert eval_details["inference_timestamp"] == "2026-10-03T10:00:00+00:00"


def test_historical_evaluations_retain_original_model_version_after_new_model_deployed():
    """
    CRITICAL REQUIREMENT TEST:
    Historical interview results must remain interpretable and retain their original
    model version even after a newer model is deployed. Historical results must never be overwritten.
    """
    supabase = SupabaseService()
    registry = ModelVersionRegistry.get_instance()
    
    # ── Phase 1: Candidate A completes an interview under Model v1.0.0 ──
    session_id_v1 = f"session-historical-v1-{uuid.uuid4()}"
    q_id_v1 = f"q-hist-{uuid.uuid4()}"
    
    supabase.create_local_session(session_id_v1, user_id="candidate-1")
    supabase._local_questions[session_id_v1] = [{
        "id": q_id_v1,
        "question_text": "Explain quicksort average and worst case time complexity.",
        "difficulty": "intermediate",
    }]
    
    # Evaluation generated by original deployed model v1.0.0
    eval_v1 = stamp_inference(
        "answer-nli-v1",
        {
            "score": 85,
            "feedback": "Good understanding of O(n log n) average and O(n^2) worst case.",
        },
        version_override="1.0.0",
        run_override="answer-nli-v1_run_20260930",
        dataset_override="mnli-snli-v1",
    )
    assert eval_v1["model_version"] == "1.0.0"
    
    supabase.store_answer(
        session_id=session_id_v1,
        question_id=q_id_v1,
        answer_text="Quicksort is O(n log n) average, O(n^2) worst case when poorly partitioned.",
        evaluation=eval_v1,
    )
    
    # Verify S1 is persisted with v1.0.0
    s1_eval_before = supabase.get_historical_evaluation(session_id_v1, q_id_v1)
    assert s1_eval_before is not None
    assert s1_eval_before["model_version"] == "1.0.0"
    assert s1_eval_before["training_run"] == "answer-nli-v1_run_20260930"
    
    # ── Phase 2: A newer model version v2.0.0 is deployed ───────────────
    registry.deploy_new_version(
        model_identifier="answer-nli-v1",
        new_version="2.0.0",
        dataset_version="mnli-snli-v2-augmented",
        training_run="answer-nli-v1_run_20261101",
        artifact_hash="hash_deberta_v2_new",
        notes="Upgraded cross-encoder weights with domain adaptation.",
    )
    
    # Verify active metadata is now v2.0.0
    active_meta = registry.get_active_metadata("answer-nli-v1")
    assert active_meta.model_version == "2.0.0"
    assert active_meta.training_run == "answer-nli-v1_run_20261101"
    
    # ── Phase 3: Candidate B completes an interview under Model v2.0.0 ──
    session_id_v2 = f"session-new-v2-{uuid.uuid4()}"
    q_id_v2 = f"q-new-{uuid.uuid4()}"
    
    supabase.create_local_session(session_id_v2, user_id="candidate-2")
    supabase._local_questions[session_id_v2] = [{
        "id": q_id_v2,
        "question_text": "Explain quicksort average and worst case time complexity.",
        "difficulty": "intermediate",
    }]
    
    # Evaluation generated by the newly active v2.0.0 model
    eval_v2 = stamp_inference(
        "answer-nli-v1",
        {
            "score": 88,
            "feedback": "Accurate complexity analysis under v2 model.",
        },
        version_override="2.0.0",
        run_override="answer-nli-v1_run_20261101",
        dataset_override="mnli-snli-v2-augmented",
    )
    
    supabase.store_answer(
        session_id=session_id_v2,
        question_id=q_id_v2,
        answer_text="Quicksort is O(n log n) average, O(n^2) worst case when poorly partitioned.",
        evaluation=eval_v2,
    )
    
    # ── Phase 4: Verification of Historical Immutability ────────────────
    # Query Candidate A's historical interview from the database
    s1_eval_after = supabase.get_historical_evaluation(session_id_v1, q_id_v1)
    assert s1_eval_after is not None
    
    # 1. Historical evaluation MUST retain its original model version
    assert s1_eval_after["model_version"] == "1.0.0", (
        f"Historical evaluation model_version was mutated! Expected '1.0.0', got '{s1_eval_after['model_version']}'"
    )
    assert s1_eval_after["training_run"] == "answer-nli-v1_run_20260930"
    assert s1_eval_after["dataset_version"] == "mnli-snli-v1"
    
    # 2. Candidate B's evaluation reflects the new model version
    s2_eval = supabase.get_historical_evaluation(session_id_v2, q_id_v2)
    assert s2_eval is not None
    assert s2_eval["model_version"] == "2.0.0"
    assert s2_eval["training_run"] == "answer-nli-v1_run_20261101"
    assert s2_eval["dataset_version"] == "mnli-snli-v2-augmented"
    
    # 3. Registry allows looking up both the historical retired version AND active version
    historical_info = registry.get_historical_version("answer-nli-v1", "1.0.0")
    assert historical_info is not None
    assert historical_info["status"] == "retired"
    assert historical_info["model_version"] == "1.0.0"
    
    active_info = registry.get_historical_version("answer-nli-v1", "2.0.0")
    assert active_info is not None
    assert active_info["status"] == "active"
    assert active_info["model_version"] == "2.0.0"


def test_re_evaluation_does_not_overwrite_historical_model_result():
    """
    Confirms that if an answer is re-evaluated with a newer model,
    the original historical evaluation details are preserved in evaluation_history
    and NOT destructively overwritten.
    """
    supabase = SupabaseService()
    session_id = f"re-eval-session-{uuid.uuid4()}"
    q_id = f"re-eval-q-{uuid.uuid4()}"
    
    supabase.create_local_session(session_id, user_id="candidate-re-eval")
    supabase._local_questions[session_id] = [{
        "id": q_id,
        "question_text": "What is a deadlock in OS?",
        "difficulty": "intermediate",
    }]
    
    # First evaluation under v1.0.0
    eval_original = {
        "score": 75,
        "feedback": "Mentioned mutual exclusion but missed hold and wait.",
        "model_name": "answer-nli-v1",
        "model_version": "1.0.0",
        "dataset_version": "mnli-snli-v1",
        "training_run": "run-v1",
        "inference_timestamp": "2026-10-01T12:00:00+00:00",
    }
    
    supabase.store_answer(
        session_id=session_id,
        question_id=q_id,
        answer_text="A deadlock happens when threads wait for each other.",
        evaluation=eval_original,
    )
    
    # Second evaluation (e.g. re-evaluation or newer model v2.0.0)
    eval_newer = {
        "score": 80,
        "feedback": "Improved rubric coverage assessment under v2.",
        "model_name": "answer-nli-v1",
        "model_version": "2.0.0",
        "dataset_version": "mnli-snli-v2",
        "training_run": "run-v2",
        "inference_timestamp": "2026-10-03T12:00:00+00:00",
    }
    
    supabase.store_answer(
        session_id=session_id,
        question_id=q_id,
        answer_text="A deadlock happens when threads wait for each other.",
        evaluation=eval_newer,
    )
    
    # Fetch questions
    questions = supabase.get_session_questions(session_id)
    assert len(questions) == 1
    q = questions[0]
    
    # Original historical evaluation must STILL be retained
    assert q["evaluation_details"]["model_version"] == "1.0.0"
    assert q["evaluation_details"]["training_run"] == "run-v1"
    
    # Evaluation history must contain BOTH records in order
    history = q.get("evaluation_history", [])
    assert len(history) == 2
    assert history[0]["model_version"] == "1.0.0"
    assert history[1]["model_version"] == "2.0.0"


def test_question_skill_service_persists_attribution():
    """Confirms QuestionSkillService persists attribution fields with question skill predictions."""
    supabase = SupabaseService()
    svc = QuestionSkillService(supabase)
    
    q_id = f"skill-q-{uuid.uuid4()}"
    q_text = "Implement Dijkstra's shortest path algorithm using a min-heap."
    
    result = svc.predict_and_persist(question_id=q_id, question_text=q_text)
    
    for field in REQUIRED_ATTRIBUTION_FIELDS:
        assert field in result, f"Field '{field}' missing from QuestionSkillService result"
    assert result["model_name"] == "question-skill-v1"
    
    # Retrieve from supabase service
    stored = supabase.get_question_skill_prediction(q_id)
    assert stored is not None
    assert stored["model_name"] == "question-skill-v1"
    assert stored["question_id"] == q_id
    assert "model_version" in stored
    assert "dataset_version" in stored
    assert "training_run" in stored
    assert "inference_timestamp" in stored


def test_code_submission_retains_attribution():
    """Confirms code submissions persist attribution fields and do not overwrite historical results."""
    supabase = SupabaseService()
    session_id = f"code-sess-{uuid.uuid4()}"
    q_id = f"code-q-{uuid.uuid4()}"
    
    supabase.create_local_session(session_id, user_id="code-user")
    supabase._local_questions[session_id] = [{
        "id": q_id,
        "question_text": "Write a function to reverse a linked list.",
        "difficulty": "intermediate",
    }]
    
    eval_code = {
        "score": 95,
        "feedback": "Optimal O(n) iterative solution.",
        "model_name": "code-risk-v1",
        "model_version": "1.0.0",
        "dataset_version": "CodeXGLUE-defect-v1",
        "training_run": "code-risk-v1_codebert_ast_analysis",
        "inference_timestamp": "2026-10-02T15:00:00+00:00",
    }
    
    code_text = "def reverseList(head): prev = None; ... return prev"
    success = supabase.store_code_submission(
        session_id=session_id,
        question_id=q_id,
        code=code_text,
        language="python",
        evaluation=eval_code,
    )
    assert success is True
    
    # Retrieve historical evaluation
    hist_eval = supabase.get_historical_evaluation(session_id, q_id)
    assert hist_eval is not None
    assert hist_eval["model_name"] == "code-risk-v1"
    assert hist_eval["model_version"] == "1.0.0"
    assert hist_eval["dataset_version"] == "CodeXGLUE-defect-v1"
    assert hist_eval["training_run"] == "code-risk-v1_codebert_ast_analysis"

"""
Deterministic unit tests for ML Adaptive Question Selector and Orchestrator Integration.

Validates the full deterministic decision pipeline:
    candidate skill state
    ↓
    candidate weaknesses
    ↓
    eligible questions
    ↓
    difficulty prediction
    ↓
    skill coverage
    ↓
    semantic deduplication
    ↓
    adaptive ranking
    ↓
    next question

Tests enforce:
    1. Deterministic selection reproducibility.
    2. Strict compliance with user's logging schema.
    3. Weakness remediation prioritization.
    4. 2PL-IRT latent ability difficulty adaptation.
    5. Dense semantic deduplication and novelty penalties.
    6. Skill coverage and curriculum balancing.
    7. Time budget pacing and duration constraints.
    8. Auditable explainability answering: 'Why was this question selected?'.
    9. End-to-end integration with InterviewOrchestrator.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from ml.models.adaptive_selector import (
    AdaptiveQuestionSelector,
    CatalogQuestion,
    CANONICAL_QUESTION_CATALOG,
    MODEL_VERSIONS,
)
from ml.models.skill_mastery import ItemResponseTheoryMasteryModel
from app.services.orchestrator.models import (
    OrchestratorState,
    SkillSignal,
    QuestionRecord,
    InterviewPhase,
    DifficultyLevel,
    SessionPolicy,
)
from app.services.orchestrator.service import InterviewOrchestrator


from ml.features.text_embeddings import TextEmbeddingExtractor

REQUIRED_DECISION_KEYS = {
    "candidate_skill",
    "current_mastery",
    "target_skill",
    "candidate_question_score",
    "difficulty_fit",
    "novelty",
    "selected",
    "model_versions",
}


@pytest.fixture
def selector() -> AdaptiveQuestionSelector:
    extractor = TextEmbeddingExtractor(enable_transformer=False)
    return AdaptiveQuestionSelector(embedding_extractor=extractor)


# ─────────────────────────────────────────────────────────────────────────────
# 1. DETERMINISTIC REPRODUCIBILITY & SCHEMA COMPLIANCE
# ─────────────────────────────────────────────────────────────────────────────
class TestDeterministicSelectionAndSchema:

    def test_selection_is_100_percent_deterministic(self, selector: AdaptiveQuestionSelector):
        """The exact same candidate state must produce the exact same selected question."""
        skill_state = {
            "arrays": {
                "mastery": 0.40,
                "scores": [40.0],
                "questions_count": 1,
                "weaknesses": ["Time complexity optimization"],
                "strengths": [],
                "theta": -0.6,
            }
        }
        res_a = selector.select_next_question(
            candidate_skill_state=skill_state,
            current_difficulty="beginner",
            previous_question_history=[],
            time_budget_seconds=2700,
            elapsed_seconds=300,
        )
        res_b = selector.select_next_question(
            candidate_skill_state=skill_state,
            current_difficulty="beginner",
            previous_question_history=[],
            time_budget_seconds=2700,
            elapsed_seconds=300,
        )

        assert res_a["selected_question"]["id"] == res_b["selected_question"]["id"]
        assert res_a["decision"]["candidate_question_score"] == res_b["decision"]["candidate_question_score"]
        assert res_a["decision"]["difficulty_fit"] == res_b["decision"]["difficulty_fit"]
        assert res_a["decision"]["novelty"] == res_b["decision"]["novelty"]

    def test_decision_log_matches_exact_user_schema(self, selector: AdaptiveQuestionSelector):
        """Validates that logged decision dictionary matches the required user schema."""
        skill_state = {
            "algorithms": {
                "mastery": 0.42,
                "scores": [42.0],
                "questions_count": 1,
                "weaknesses": ["edge cases"],
                "strengths": [],
            }
        }
        result = selector.select_next_question(
            candidate_skill_state=skill_state,
            current_difficulty="intermediate",
            previous_question_history=[],
        )
        decision = result["decision"]

        # Validate all required keys are present
        assert set(decision.keys()) == REQUIRED_DECISION_KEYS
        assert isinstance(decision["candidate_skill"], str)
        assert isinstance(decision["current_mastery"], (int, float))
        assert 0.0 <= decision["current_mastery"] <= 1.0
        assert isinstance(decision["target_skill"], str)
        assert isinstance(decision["candidate_question_score"], (int, float))
        assert 0.0 <= decision["candidate_question_score"] <= 1.0
        assert isinstance(decision["difficulty_fit"], (int, float))
        assert 0.0 <= decision["difficulty_fit"] <= 1.0
        assert isinstance(decision["novelty"], (int, float))
        assert 0.0 <= decision["novelty"] <= 1.0
        assert decision["selected"] is True
        assert isinstance(decision["model_versions"], list)
        assert len(decision["model_versions"]) >= 4

    def test_all_decisions_log_format(self, selector: AdaptiveQuestionSelector):
        """Every evaluated candidate question must have a conforming log entry with exactly one winner."""
        result = selector.select_next_question(
            candidate_skill_state={},
            current_difficulty="intermediate",
            previous_question_history=[],
        )
        all_decisions = result["all_decisions"]
        assert len(all_decisions) > 1

        selected_count = sum(1 for d in all_decisions if d["selected"] is True)
        assert selected_count == 1
        assert all_decisions[0]["selected"] is True

        for entry in all_decisions:
            assert set(entry.keys()) == REQUIRED_DECISION_KEYS


# ─────────────────────────────────────────────────────────────────────────────
# 2. WEAKNESS REMEDIATION PRIORITIZATION
# ─────────────────────────────────────────────────────────────────────────────
class TestWeaknessPrioritization:

    def test_active_weakness_prioritizes_remedial_question(self, selector: AdaptiveQuestionSelector):
        """Candidate who struggled on arrays (score 35%) should be served an arrays question."""
        skill_state = {
            "arrays": {
                "mastery": 0.35,
                "scores": [35.0],
                "questions_count": 1,
                "weaknesses": ["hash map lookup bounds"],
                "strengths": [],
                "theta": -0.8,
            },
            "trees": {
                "mastery": 0.85,
                "scores": [85.0],
                "questions_count": 1,
                "weaknesses": [],
                "strengths": ["recursion"],
                "theta": 0.8,
            },
        }

        # Provide a pool with an arrays question and a trees question
        pool = [
            {
                "id": "q_arr",
                "title": "Array Two Sum",
                "question_text": "Solve two sum in O(N) using hashing.",
                "interview_type": "coding",
                "target_role": "Software Engineer",
                "skill_focus": "arrays",
                "difficulty": "beginner",
                "expected_time_minutes": 10,
            },
            {
                "id": "q_tree",
                "title": "Binary Tree Inversion",
                "question_text": "Invert a binary tree recursively.",
                "interview_type": "coding",
                "target_role": "Software Engineer",
                "skill_focus": "trees",
                "difficulty": "intermediate",
                "expected_time_minutes": 10,
            },
        ]

        result = selector.select_next_question(
            candidate_skill_state=skill_state,
            current_difficulty="beginner",
            previous_question_history=[],
            candidate_questions_pool=pool,
        )

        assert result["selected_question"]["id"] == "q_arr"
        assert result["target_skill"] == "arrays"
        assert result["current_mastery"] == 0.35


# ─────────────────────────────────────────────────────────────────────────────
# 3. DIFFICULTY ADAPTATION VIA 2PL-IRT LATENT ABILITY
# ─────────────────────────────────────────────────────────────────────────────
class TestDifficultyAdaptation:

    def test_high_ability_candidate_gets_advanced_question(self, selector: AdaptiveQuestionSelector):
        """Candidate with high latent ability (theta >= 1.2) should receive an advanced question."""
        pool = [
            {"id": "q_beg", "difficulty": "beginner", "skill_focus": "arrays", "question_text": "Beginner arrays", "target_role": "Software Engineer", "interview_type": "coding"},
            {"id": "q_int", "difficulty": "intermediate", "skill_focus": "arrays", "question_text": "Intermediate arrays", "target_role": "Software Engineer", "interview_type": "coding"},
            {"id": "q_adv", "difficulty": "advanced", "skill_focus": "arrays", "question_text": "Advanced arrays", "target_role": "Software Engineer", "interview_type": "coding"},
        ]

        result = selector.select_next_question(
            candidate_skill_state={"_candidate_theta": 1.4},
            current_difficulty="advanced",
            previous_question_history=[],
            candidate_questions_pool=pool,
        )

        assert result["selected_question"]["id"] == "q_adv"
        assert result["decision"]["difficulty_fit"] > 0.80

    def test_low_ability_candidate_gets_beginner_question(self, selector: AdaptiveQuestionSelector):
        """Candidate with low latent ability (theta <= -1.0) should receive a beginner question."""
        pool = [
            {"id": "q_beg", "difficulty": "beginner", "skill_focus": "arrays", "question_text": "Beginner arrays", "target_role": "Software Engineer", "interview_type": "coding"},
            {"id": "q_int", "difficulty": "intermediate", "skill_focus": "arrays", "question_text": "Intermediate arrays", "target_role": "Software Engineer", "interview_type": "coding"},
            {"id": "q_adv", "difficulty": "advanced", "skill_focus": "arrays", "question_text": "Advanced arrays", "target_role": "Software Engineer", "interview_type": "coding"},
        ]

        result = selector.select_next_question(
            candidate_skill_state={"_candidate_theta": -1.2},
            current_difficulty="beginner",
            previous_question_history=[],
            candidate_questions_pool=pool,
        )

        assert result["selected_question"]["id"] == "q_beg"
        assert result["decision"]["difficulty_fit"] > 0.80


# ─────────────────────────────────────────────────────────────────────────────
# 4. SEMANTIC DEDUPLICATION & NOVELTY PENALTIES
# ─────────────────────────────────────────────────────────────────────────────
class TestSemanticDeduplication:

    def test_identical_or_near_duplicate_question_is_penalized(self, selector: AdaptiveQuestionSelector):
        """Questions identical or semantically duplicate to previous ones must be demoted."""
        asked_text = "Given an array of integers nums and an integer target, return indices of two numbers that add up to target."
        prev_history = [{"question_id": "q_prev", "question_text": asked_text, "score": 75.0}]

        pool = [
            {
                "id": "q_duplicate",
                "title": "Two Sum Paraphrased",
                "question_text": "Find two integers in nums that add up to target and return their indices.",  # Paraphrased near-duplicate
                "skill_focus": "arrays",
                "difficulty": "intermediate",
                "target_role": "Software Engineer",
                "interview_type": "coding",
            },
            {
                "id": "q_fresh",
                "title": "Reverse Linked List",
                "question_text": "Given the head of a singly linked list, reverse the list and return its head.",
                "skill_focus": "linked_lists",
                "difficulty": "intermediate",
                "target_role": "Software Engineer",
                "interview_type": "coding",
            },
        ]

        result = selector.select_next_question(
            candidate_skill_state={},
            current_difficulty="intermediate",
            previous_question_history=prev_history,
            candidate_questions_pool=pool,
        )

        assert result["selected_question"]["id"] == "q_fresh"

        # Check that the near-duplicate entry had a lower novelty than the fresh question
        dup_decision = next(d for d in result["all_decisions"] if d["candidate_skill"] == "arrays")
        fresh_decision = next(d for d in result["all_decisions"] if d["candidate_skill"] == "linked_lists")
        assert dup_decision["novelty"] < fresh_decision["novelty"]

    def test_already_asked_id_is_excluded(self, selector: AdaptiveQuestionSelector):
        """Questions with previously asked IDs must not be eligible."""
        pool = [
            {"id": "q1", "question_text": "What is hoisting?", "skill_focus": "javascript", "difficulty": "intermediate", "target_role": "Software Engineer", "interview_type": "coding"},
            {"id": "q2", "question_text": "Explain the event loop.", "skill_focus": "javascript", "difficulty": "intermediate", "target_role": "Software Engineer", "interview_type": "coding"},
        ]
        result = selector.select_next_question(
            candidate_skill_state={},
            current_difficulty="intermediate",
            previous_question_history=[{"question_id": "q1", "question_text": "What is hoisting?"}],
            candidate_questions_pool=pool,
        )
        assert result["selected_question"]["id"] == "q2"


# ─────────────────────────────────────────────────────────────────────────────
# 5. SKILL COVERAGE & CURRICULUM BALANCING
# ─────────────────────────────────────────────────────────────────────────────
class TestSkillCoverageBalancing:

    def test_untested_skill_prioritized_over_repeatedly_tested_skill(self, selector: AdaptiveQuestionSelector):
        """When a skill has already been tested multiple times proficiently, unassessed skills are chosen."""
        skill_state = {
            "arrays": {
                "mastery": 0.85,
                "scores": [85.0, 90.0],
                "questions_count": 2,
                "weaknesses": [],
                "strengths": ["hash mapping", "sliding window"],
            },
            "dynamic_programming": {
                "mastery": 0.50,
                "scores": [],
                "questions_count": 0,
                "weaknesses": [],
                "strengths": [],
            },
        }

        pool = [
            {"id": "q_arr_3", "skill_focus": "arrays", "difficulty": "intermediate", "question_text": "Third array problem", "target_role": "Software Engineer", "interview_type": "coding"},
            {"id": "q_dp_1", "skill_focus": "dynamic_programming", "difficulty": "intermediate", "question_text": "First DP problem: Climbing stairs", "target_role": "Software Engineer", "interview_type": "coding"},
        ]

        result = selector.select_next_question(
            candidate_skill_state=skill_state,
            current_difficulty="intermediate",
            previous_question_history=[{"question_id": "q_arr_1", "question_text": "Q1"}, {"question_id": "q_arr_2", "question_text": "Q2"}],
            candidate_questions_pool=pool,
            role_skills=["arrays", "dynamic_programming"],
        )

        assert result["selected_question"]["id"] == "q_dp_1"
        assert result["target_skill"] == "dynamic_programming"


# ─────────────────────────────────────────────────────────────────────────────
# 6. TIME BUDGET PACING
# ─────────────────────────────────────────────────────────────────────────────
class TestTimeBudgetConstraints:

    def test_time_running_out_favors_shorter_question(self, selector: AdaptiveQuestionSelector):
        """With very low time budget remaining (3 minutes), a 10m question beats a 30m question."""
        pool = [
            {
                "id": "q_long",
                "title": "Distributed Key-Value Store",
                "question_text": "Design a geo-distributed key-value store with raft consensus.",
                "skill_focus": "system_design",
                "difficulty": "intermediate",
                "expected_time_minutes": 35,
                "target_role": "Software Engineer",
                "interview_type": "coding",
            },
            {
                "id": "q_short",
                "title": "Reverse Words in String",
                "question_text": "Given a string s, reverse the order of characters in each word.",
                "skill_focus": "strings",
                "difficulty": "intermediate",
                "expected_time_minutes": 8,
                "target_role": "Software Engineer",
                "interview_type": "coding",
            },
        ]

        # 180 seconds left (3 minutes) for 1 question
        result = selector.select_next_question(
            candidate_skill_state={},
            current_difficulty="intermediate",
            previous_question_history=[],
            candidate_questions_pool=pool,
            time_budget_seconds=1800,
            elapsed_seconds=1620,  # 3 min remaining
            max_questions=1,
        )

        assert result["selected_question"]["id"] == "q_short"


# ─────────────────────────────────────────────────────────────────────────────
# 7. EXPLAINABILITY: 'Why was this question selected?'
# ─────────────────────────────────────────────────────────────────────────────
class TestRankingExplainability:

    def test_explanation_answers_why_with_historical_evidence(self, selector: AdaptiveQuestionSelector):
        """System must explain question selection referencing candidate's specific session history."""
        skill_state = {
            "dynamic_programming": {
                "mastery": 0.35,
                "scores": [35.0],
                "questions_count": 1,
                "weaknesses": ["Memoization state transitions"],
                "strengths": [],
                "theta": -0.7,
            }
        }
        prev_history = [
            {
                "question_id": "q1",
                "question_text": "Coin change minimum coins",
                "skill_focus": "dynamic_programming",
                "score": 35.0,
            }
        ]

        result = selector.select_next_question(
            candidate_skill_state=skill_state,
            current_difficulty="beginner",
            previous_question_history=prev_history,
        )

        why_selected = result["why_selected"]
        assert isinstance(why_selected, str)
        assert len(why_selected) > 40

        # Must mention the target skill or score
        assert "dynamic_programming" in why_selected or "score" in why_selected.lower()
        # Must mention theta / ability or difficulty fit
        assert "fit" in why_selected.lower() or "theta" in why_selected.lower()
        # Must mention novelty or diversity
        assert "novelty" in why_selected.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 8. ORCHESTRATOR INTEGRATION & LATENT ABILITY UPDATES
# ─────────────────────────────────────────────────────────────────────────────
class TestOrchestratorIntegration:

    def test_orchestrator_deterministic_flow(self, selector: AdaptiveQuestionSelector):
        mock_db = MagicMock()
        mock_db.store_question.return_value = "db_q_101"
        mock_db.store_question_skill_prediction.return_value = {"id": "ml_pred_1"}
        mock_db.get_session.return_value = {
            "id": "test_session_1",
            "target_role": "Software Engineer",
            "interview_type": "coding",
            "status": "in_progress",
        }
        mock_ai = MagicMock()
        mock_ai.evaluate_answer.return_value = {
            "overall_score": 90.0,
            "strengths": ["optimal time complexity"],
            "weaknesses": [],
            "recommended_follow_up": "",
        }
        orchestrator = InterviewOrchestrator(
            supabase_service=mock_db,
            ai_engine=mock_ai,
            adaptive_selector=selector
        )

        # 1. Get initial question
        q1_result = orchestrator.get_next_question("test_session_1")
        assert q1_result["question_id"] == "db_q_101"
        assert "selection_decision" in q1_result
        assert "why_selected" in q1_result

        decision = q1_result["selection_decision"]
        assert set(decision.keys()) == REQUIRED_DECISION_KEYS
        assert decision["selected"] is True

        # Verify Supabase logged the selection event
        mock_db.log_event.assert_any_call(
            "test_session_1",
            "orchestrator_question_selected",
            {
                "question_id": "db_q_101",
                "decision": decision,
                "why_selected": q1_result["why_selected"],
            }
        )

        # 2. Evaluate answer and verify latent ability theta updates
        eval_res = orchestrator.record_and_evaluate_answer(
            session_id="test_session_1",
            question_id="db_q_101",
            answer_text="Using a hash map gives O(N) lookup.",
        )
        assert eval_res["evaluation"]["overall_score"] == 90.0

        state = orchestrator.get_or_restore_state("test_session_1")
        # Candidate performed well, theta should have increased from initial 0.0
        assert state.candidate_theta > 0.0

        # 3. Query rationale API helper
        rationale_data = orchestrator.get_question_selection_rationale("test_session_1", "db_q_101")
        assert rationale_data is not None
        assert rationale_data["question_id"] == "db_q_101"
        assert rationale_data["decision"] == decision
        assert rationale_data["why_selected"] == q1_result["why_selected"]

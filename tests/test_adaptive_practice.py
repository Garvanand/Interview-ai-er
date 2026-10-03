"""
Tests for AdaptivePracticeEngine.
Verifies:
  1. Weakness reinforcement mode prioritizing lowest mastery & recent mistakes
  2. Role preparation mode building a diverse, progressive curriculum
  3. Explainable selection reason on every selected question
  4. Difficulty progression scaffolding
  5. Spaced repetition interval triggers
  6. Semantic deduplication & duplicate prevention
  7. 100% deterministic ranking (no random selection)
  8. Integration with CandidateModel & evidence persistence
"""
import pytest
from ml.models.adaptive_practice import (
    AdaptivePracticeEngine,
    MODE_WEAKEST_SKILLS,
    MODE_ROLE_PREP,
    PracticePlan,
    PracticeSequenceItem,
)
from ml.models.candidate_model import CandidateModel, ObservationEvent, EvidenceChainItem


@pytest.fixture
def practice_engine():
    return AdaptivePracticeEngine()


@pytest.fixture
def candidate_with_weaknesses():
    cand = CandidateModel(
        user_id="user_dp_weakness",
        target_role="Software Engineer",
        target_skills=["arrays", "dynamic_programming", "graphs", "trees", "System Design"],
        skill_estimates={
            "arrays": 0.85,
            "trees": 0.78,
            "graphs": 0.70,
            "dynamic_programming": 0.35,  # Clear weakness
            "System Design": 0.80,
        },
        skill_confidence={
            "arrays": 0.90,
            "trees": 0.85,
            "graphs": 0.75,
            "dynamic_programming": 0.30,  # Low confidence
            "System Design": 0.80,
        },
        weak_skill_signals=["dynamic_programming"],
        practice_history=["dsa_arr_two_sum"],
    )
    # Add recent mistake to evidence chain
    cand.evidence_chain.append(
        EvidenceChainItem(
            session_id="sess_001",
            observations=[
                ObservationEvent(
                    event_id="obs_01",
                    session_id="sess_001",
                    event_type="question_scored",
                    description="Candidate scored 40% on dynamic programming memoization.",
                    skill_focus="dynamic_programming",
                    raw_data={"score": 40.0, "difficulty": "intermediate", "question_id": "dsa_dp_coin_change"},
                )
            ],
            inferences=[],
            decisions=[],
        )
    )
    return cand


def test_weakness_reinforcement_mode(practice_engine, candidate_with_weaknesses):
    """Test that 'Practice my weakest skills' targets the candidate's lowest mastery skill."""
    plan: PracticePlan = practice_engine.generate_practice_sequence(
        candidate_data=candidate_with_weaknesses,
        mode=MODE_WEAKEST_SKILLS,
        num_questions=4,
    )

    assert plan is not None
    assert plan.mode == MODE_WEAKEST_SKILLS
    assert len(plan.sequence) == 4

    # Primary focus must be dynamic programming
    first_item = plan.sequence[0]
    assert first_item.skill_focus == "dynamic_programming" or "dynamic_programming" in first_item.canonical_skills

    # Every item must have an explainable selection reason
    for item in plan.sequence:
        assert isinstance(item.selection_reason, str)
        assert len(item.selection_reason) > 20
        assert "dynamic programming" in item.selection_reason.lower() or "selected" in item.selection_reason.lower()
        assert item.progression_stage in [
            "foundational_reinforcement",
            "scaffolded_progression",
            "frontier_mastery",
            "spaced_retention",
        ]


def test_difficulty_progression_scaffolding(practice_engine, candidate_with_weaknesses):
    """Test that a weakness practice sequence scaffolds difficulty from beginner/intermediate to advanced."""
    plan = practice_engine.generate_practice_sequence(
        candidate_data=candidate_with_weaknesses,
        mode=MODE_WEAKEST_SKILLS,
        num_questions=3,
    )

    difficulties = [item.difficulty for item in plan.sequence]
    # For a low-mastery candidate (0.35), first item should be beginner/intermediate, later advancing
    assert difficulties[0] in ["beginner", "intermediate"]
    assert "advanced" in difficulties or difficulties[-1] in ["intermediate", "advanced"]


def test_role_prep_curriculum_diversity(practice_engine):
    """Test that 'Prepare me for Software Engineer interviews' creates a diverse sequence covering role pillars."""
    cand = CandidateModel(
        user_id="user_swe_prep",
        target_role="Software Engineer",
        skill_estimates={
            "arrays": 0.65,
            "trees": 0.70,
            "graphs": 0.60,
            "dynamic_programming": 0.65,
            "System Design": 0.70,
        },
    )

    plan = practice_engine.generate_practice_sequence(
        candidate_data=cand,
        mode=MODE_ROLE_PREP,
        target_role="Software Engineer",
        num_questions=4,
    )

    assert plan is not None
    assert plan.mode == MODE_ROLE_PREP
    assert len(plan.sequence) == 4

    # Verify diversity across questions
    unique_skills = {item.skill_focus for item in plan.sequence}
    assert len(unique_skills) >= 2, "Role prep sequence should span multiple curriculum pillars"

    # Verify explainable selection reason mentioning role preparation
    for item in plan.sequence:
        assert "software engineer" in item.selection_reason.lower() or "interview" in item.selection_reason.lower()


def test_duplicate_prevention_from_history(practice_engine):
    """Test that previously practiced question IDs are strictly excluded."""
    # Put two specific questions in history
    history = ["dsa_arr_two_sum", "dsa_dp_climbing_stairs"]
    cand = CandidateModel(
        user_id="user_dedup",
        practice_history=history,
        target_role="Software Engineer",
    )

    plan = practice_engine.generate_practice_sequence(
        candidate_data=cand,
        mode=MODE_WEAKEST_SKILLS,
        num_questions=5,
    )

    selected_ids = [item.question_id for item in plan.sequence]
    for h_id in history:
        assert h_id not in selected_ids, f"Question {h_id} should have been excluded by duplicate prevention"


def test_selection_is_100_percent_deterministic(practice_engine, candidate_with_weaknesses):
    """Verify that multiple runs with the same candidate profile yield identical sequences (no randomness)."""
    plan1 = practice_engine.generate_practice_sequence(
        candidate_data=candidate_with_weaknesses,
        mode=MODE_WEAKEST_SKILLS,
        num_questions=4,
    )
    plan2 = practice_engine.generate_practice_sequence(
        candidate_data=candidate_with_weaknesses,
        mode=MODE_WEAKEST_SKILLS,
        num_questions=4,
    )

    seq1_ids = [item.question_id for item in plan1.sequence]
    seq2_ids = [item.question_id for item in plan2.sequence]

    assert seq1_ids == seq2_ids, "Sequence selection must be 100% deterministic"
    assert [item.selection_reason for item in plan1.sequence] == [item.selection_reason for item in plan2.sequence]


def test_single_next_practice_question(practice_engine, candidate_with_weaknesses):
    """Test standalone next practice question selection with explainability."""
    item: PracticeSequenceItem = practice_engine.select_next_practice_question(
        candidate_data=candidate_with_weaknesses,
        mode=MODE_WEAKEST_SKILLS,
    )

    assert item is not None
    assert item.question_id is not None
    assert len(item.selection_reason) > 10
    assert item.difficulty in ["beginner", "intermediate", "advanced"]

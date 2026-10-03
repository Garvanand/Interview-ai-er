import pytest
from app.services.orchestrator.models import OrchestratorState, QuestionRecord, SkillSignal
from ml.models.candidate_model import CandidateModel
from datetime import datetime, timezone

def test_candidate_model_evolution():
    state = OrchestratorState(
        session_id="session_123",
        user_id="user_abc",
        target_role="Data Engineer",
        interview_type="Data Engineer",
    )
    
    # Mock questions
    q1 = QuestionRecord(
        question_id="q1",
        question_text="Explain graphs.",
        difficulty="intermediate",
        skill_focus="Graph Traversal",
        score=40.0
    )
    
    q2 = QuestionRecord(
        question_id="q2",
        question_text="Write a BFS.",
        difficulty="intermediate",
        skill_focus="Graph Traversal",
        score=45.0
    )
    
    state.questions_asked = [q1, q2]
    state.weaknesses_discovered = ["missed graph traversal concept", "poor BFS complexity"]
    state.strengths_discovered = ["good variable naming"]
    
    # Mock skill signals
    state.skills_distribution = {
        "Graph Traversal": SkillSignal(
            skill_name="Graph Traversal",
            scores=[40.0, 45.0],
            average_score=42.5,
            questions_count=2,
            mastery=0.42,
            theta=-0.5
        )
    }
    
    candidate = CandidateModel(user_id="user_abc")
    
    # Run evolution
    evidence = candidate.evolve_from_session(state)
    
    # Verify basic updates
    assert candidate.target_role == "Data Engineer"
    assert "session_123" in candidate.practice_history
    assert "Graph Traversal" in candidate.target_skills
    assert candidate.skill_estimates["Graph Traversal"] == 0.42
    assert "missed graph traversal concept" in candidate.weak_skill_signals
    
    # Verify difficulty exposure
    assert candidate.difficulty_exposure["Graph Traversal"]["intermediate"] == 2
    
    # Verify evidence chain
    assert len(candidate.evidence_chain) == 1
    assert candidate.evidence_chain[0] == evidence
    
    # Verify Observations
    obs = evidence.observations
    assert any(o.event_type == "question_scored" for o in obs)
    assert any(o.event_type == "weakness_discovered" for o in obs)
    
    # Verify Inferences
    infs = evidence.inferences
    assert len(infs) == 1
    assert infs[0].skill_name == "Graph Traversal"
    assert infs[0].mastery_estimate == 0.42
    
    # Verify Decisions
    decs = evidence.decisions
    assert len(decs) > 0
    assert "Graph Traversal" in decs[0].recommended_action

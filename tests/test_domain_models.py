"""
Unit tests for domain entity dataclasses.
Validates instantiation, type correctness, and enum constraints for all 11 core concepts.
"""
from datetime import datetime, timezone
import pytest
from app.domain import (
    InterviewSession,
    InterviewQuestion,
    CandidateResponse,
    Evaluation,
    SkillEvidence,
    CandidateSkillProfile,
    Recommendation,
    IntegrityEvent,
    CodeSubmission,
    ExecutionRun,
    AIRun,
    SessionStatus,
    Difficulty,
    IntegrityEventSeverity,
    RecommendationPriority,
    RecommendationStatus,
)


def test_interview_session_instantiation():
    session = InterviewSession(
        id="session-1",
        user_id="user-1",
        interview_type="Software Engineer",
        status=SessionStatus.ACTIVE,
        start_time=datetime.now(timezone.utc),
        score=82.5,
    )
    assert session.id == "session-1"
    assert session.status == SessionStatus.ACTIVE
    assert session.score == 82.5


def test_interview_question_instantiation():
    q = InterviewQuestion(
        id="q-1",
        session_id="session-1",
        question_text="Explain eventual consistency vs strong consistency.",
        question_type="system_design",
        difficulty=Difficulty.INTERMEDIATE,
        skill_focus="Distributed Systems",
    )
    assert q.id == "q-1"
    assert q.difficulty == Difficulty.INTERMEDIATE
    assert q.skill_focus == "Distributed Systems"


def test_candidate_response_instantiation():
    resp = CandidateResponse(
        id="resp-1",
        question_id="q-1",
        response_text="Eventual consistency guarantees replicas converge over time...",
        submitted_at=datetime.now(timezone.utc),
        is_code=False,
    )
    assert resp.id == "resp-1"
    assert not resp.is_code


def test_evaluation_instantiation():
    ev = Evaluation(
        id="eval-1",
        response_id="resp-1",
        score=88.0,
        feedback="Accurate tradeoff explanation with clear CAP theorem context.",
        evaluation_details={"accuracy": 90, "clarity": 85},
    )
    assert ev.score == 88.0
    assert ev.status == "COMPLETED"


def test_skill_evidence_instantiation():
    evidence = SkillEvidence(
        session_id="session-1",
        question_id="q-1",
        skill_name="Distributed Systems",
        score=88.0,
        difficulty=Difficulty.INTERMEDIATE,
        timestamp=datetime.now(timezone.utc),
        evidence_text="Candidate articulated quorum reads/writes clearly.",
    )
    assert evidence.skill_name == "Distributed Systems"
    assert evidence.score == 88.0


def test_candidate_skill_profile_instantiation():
    profile = CandidateSkillProfile(
        user_id="user-1",
        skill_name="Distributed Systems",
        estimated_proficiency=84.0,
        evidence_count=5,
        recent_performance=88.0,
        historical_performance=80.0,
        improvement_trend="improving",
        confidence="high",
    )
    assert profile.estimated_proficiency == 84.0
    assert profile.improvement_trend == "improving"


def test_recommendation_instantiation():
    rec = Recommendation(
        id="rec-1",
        user_id="user-1",
        target_skill="Distributed Systems",
        strategy="review_tradeoffs",
        reason="Good foundation, can be pushed on partition tolerance edge cases.",
        evidence={"score": 88.0},
        recommended_activity={"type": "deep_dive", "topic": "Paxos and Raft consensus"},
        priority=RecommendationPriority.MEDIUM,
        expected_learning_objective="Understand leader election guarantees",
        status=RecommendationStatus.PENDING,
    )
    assert rec.target_skill == "Distributed Systems"
    assert rec.priority == RecommendationPriority.MEDIUM


def test_integrity_event_instantiation():
    event = IntegrityEvent(
        id="integ-1",
        session_id="session-1",
        event_type="focus_loss",
        severity=IntegrityEventSeverity.LOW,
        evidence_details={"blur_count": 2},
        timestamp=datetime.now(timezone.utc),
    )
    assert event.event_type == "focus_loss"
    assert event.severity == IntegrityEventSeverity.LOW


def test_code_submission_instantiation():
    sub = CodeSubmission(
        id="code-1",
        question_id="q-1",
        code_text="def two_sum(nums, target): return {}",
        programming_language="python",
        submitted_at=datetime.now(timezone.utc),
    )
    assert sub.programming_language == "python"


def test_execution_run_instantiation():
    run = ExecutionRun(
        id="run-1",
        code_submission_id="code-1",
        status="COMPLETED",
        stdout="[0, 1]",
        stderr="",
        exit_code=0,
        execution_time_ms=45,
    )
    assert run.status == "COMPLETED"
    assert run.exit_code == 0


def test_ai_run_instantiation():
    airun = AIRun(
        id="airun-1",
        session_id="session-1",
        operation="generate_question",
        model="gemini-2.5-flash",
        prompt_tokens=420,
        latency_seconds=1.24,
        status="success",
    )
    assert airun.operation == "generate_question"
    assert airun.latency_seconds == 1.24

import pytest
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.services.orchestrator.models import (
    InterviewPhase,
    DifficultyLevel,
    SessionPolicy,
    OrchestratorState,
    QuestionRecord,
    FollowUpOpportunity
)
from app.services.orchestrator.service import InterviewOrchestrator
from app.services.orchestrator.skills import get_skills_for_role

class MockSupabaseService:
    def __init__(self):
        self.sessions = {}
        self.questions = {}
        self.logs = []

    def create_session(self, user_id: str, interview_type: str) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        session = {
            'id': session_id,
            'user_id': user_id,
            'interview_type': interview_type,
            'status': 'active',
            'score': 0.0,
            'start_time': datetime.now(timezone.utc).isoformat()
        }
        self.sessions[session_id] = session
        return {'success': True, 'session_id': session_id, 'data': session}

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sessions.get(session_id)

    def store_question(self, session_id: str, question_text: str, interview_type: str) -> str:
        q_id = str(uuid.uuid4())
        q = {
            'id': q_id,
            'session_id': session_id,
            'question_text': question_text,
            'interview_type': interview_type,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        if session_id not in self.questions:
            self.questions[session_id] = []
        self.questions[session_id].append(q)
        return q_id

    def store_answer(self, session_id: str, question_id: str, answer_text: str, evaluation: Dict[str, Any]) -> bool:
        for q in self.questions.get(session_id, []):
            if q['id'] == question_id:
                q['answer_text'] = answer_text
                q['evaluation_score'] = evaluation.get('overall_score', 0)
                q['evaluation_details'] = evaluation
                return True
        return False

    def store_code_submission(self, session_id: str, question_id: str, code: str, language: str, evaluation: Dict[str, Any]) -> bool:
        for q in self.questions.get(session_id, []):
            if q['id'] == question_id:
                q['code_text'] = code
                q['programming_language'] = language
                q['code_evaluation_score'] = evaluation.get('overall_score', 0)
                q['code_evaluation_details'] = evaluation
                return True
        return False

    def update_session_score(self, session_id: str, new_score: float) -> bool:
        if session_id in self.sessions:
            self.sessions[session_id]['score'] = new_score
            return True
        return False

    def end_session(self, session_id: str, final_score: float = None) -> bool:
        if session_id in self.sessions:
            self.sessions[session_id]['status'] = 'completed'
            if final_score is not None:
                self.sessions[session_id]['score'] = final_score
            return True
        return False

    def get_session_questions(self, session_id: str) -> List[Dict[str, Any]]:
        return self.questions.get(session_id, [])

    def log_event(self, session_id: str, event_type: str, details: Dict[str, Any] = None) -> bool:
        self.logs.append({
            'session_id': session_id,
            'event_type': event_type,
            'details': details or {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        return True

    def log_anomaly(self, session_id: str, anomaly_type: str, severity: str, details: Dict[str, Any] = None) -> bool:
        return True

class MockAssessmentEngine:
    def __init__(self):
        self.generated_questions = []
        self.evaluations = []
        self.next_score = 85
        self.next_weaknesses = ["Incomplete concurrency handling"]
        self.duplicate_mode = False

    def generate_question(
        self,
        interview_type: str,
        difficulty: str = 'intermediate',
        topic: Optional[str] = None,
        skill_focus: Optional[str] = None,
        target_role: Optional[str] = None,
        excluded_questions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        if self.duplicate_mode and len(self.generated_questions) > 0 and not (excluded_questions and "Duplicate test question" in excluded_questions):
            q_text = "Duplicate test question"
        else:
            q_text = f"Explain {skill_focus or 'core concepts'} at {difficulty} level for {target_role} (id: {len(self.generated_questions)+1})"
        
        self.generated_questions.append(q_text)
        return {
            "question_text": q_text,
            "question_type": interview_type,
            "domain": "backend",
            "skill_tags": [skill_focus or "General"],
            "difficulty": difficulty,
            "expected_reasoning": "Clear explanation",
            "evaluation_rubric": "Accuracy and depth",
            "follow_up_axes": ["Scaling", "Fault tolerance"],
            "_metadata": {"status": "success", "latency_seconds": 0.1}
        }

    def evaluate_answer(self, question: str, answer: str, question_type: str = 'technical') -> Dict[str, Any]:
        ev = {
            "overall_score": self.next_score,
            "technical_accuracy": self.next_score,
            "conceptual_depth": self.next_score,
            "problem_solving": self.next_score,
            "communication": self.next_score,
            "completeness": self.next_score,
            "evidence": "Demonstrated solid grasp",
            "strengths": ["Clear explanation", "Good terminology"],
            "weaknesses": list(self.next_weaknesses),
            "recommended_follow_up": f"How would you address {self.next_weaknesses[0] if self.next_weaknesses else 'edge cases'}?",
            "confidence": 0.95,
            "_metadata": {"status": "success", "latency_seconds": 0.15}
        }
        self.evaluations.append(ev)
        return ev

    def evaluate_code(self, code: str, language: str, question: str) -> Dict[str, Any]:
        return {
            "overall_score": self.next_score,
            "correctness": self.next_score,
            "algorithm_quality": self.next_score,
            "complexity": "O(N) time, O(1) space",
            "code_quality": self.next_score,
            "readability": self.next_score,
            "edge_case_coverage": self.next_score,
            "testability": self.next_score,
            "strengths": ["Clean idiomatic code"],
            "issues": list(self.next_weaknesses),
            "recommendations": ["Add edge case test"],
            "confidence": 0.95,
            "_metadata": {"status": "success", "latency_seconds": 0.2}
        }

    def generate_follow_up_question(
        self,
        original_question: str,
        candidate_answer: str,
        evaluation: Dict[str, Any],
        weakness: Optional[str] = None,
        skill_focus: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> Dict[str, Any]:
        return {
            "question_text": f"Follow-up: Probe deeper into {weakness or 'weakness'} in {skill_focus or 'general'}",
            "question_type": "technical",
            "domain": "backend",
            "skill_tags": [skill_focus or "General"],
            "difficulty": difficulty or "intermediate",
            "expected_reasoning": "Deeper analysis",
            "evaluation_rubric": "Addresses weakness",
            "follow_up_axes": [],
            "_metadata": {"status": "success", "latency_seconds": 0.1}
        }

    def synthesize_session(self, session_data: str) -> Dict[str, Any]:
        return {
            "overall_rating": "Hire",
            "summary": "Solid candidate performance across tested skills.",
            "key_strengths": ["Technical clarity", "Good fundamentals"],
            "red_flags": [],
            "_metadata": {"status": "success", "latency_seconds": 0.2}
        }

@pytest.fixture
def orchestrator_setup():
    mock_supabase = MockSupabaseService()
    mock_ai = MockAssessmentEngine()
    orch = InterviewOrchestrator(supabase_service=mock_supabase, ai_engine=mock_ai)
    return orch, mock_supabase, mock_ai

# ==================== TESTS FOR STATE TRANSITIONS ====================

def test_state_machine_valid_lifecycle(orchestrator_setup):
    orch, mock_db, mock_ai = orchestrator_setup
    session_res = mock_db.create_session("user-123", "Software Engineer")
    session_id = session_res['session_id']

    # 1. INITIALIZING
    state = orch.initialize_session(session_id, "user-123", "Software Engineer", "Software Engineer")
    assert state.phase == InterviewPhase.INITIALIZING

    # 2. Transition to QUESTIONING on get_next_question
    q1 = orch.get_next_question(session_id)
    assert q1['phase'] == InterviewPhase.QUESTIONING.value
    state = orch.get_or_restore_state(session_id)
    assert state.phase == InterviewPhase.QUESTIONING

    # 3. Transition to EVALUATING & DIFFICULTY_ADJUSTMENT on answer submission
    eval_res = orch.record_and_evaluate_answer(
        session_id=session_id,
        question_id=q1['question_id'],
        answer_text="Here is my detailed solution"
    )
    assert eval_res['current_phase'] == InterviewPhase.DIFFICULTY_ADJUSTMENT.value
    state = orch.get_or_restore_state(session_id)
    assert state.phase == InterviewPhase.DIFFICULTY_ADJUSTMENT

    # 4. Finalize to FINAL_ASSESSMENT and COMPLETED
    final_res = orch.finalize_interview(session_id)
    assert final_res['is_completed'] is True
    assert final_res['phase'] == InterviewPhase.COMPLETED.value
    state = orch.get_or_restore_state(session_id)
    assert state.phase == InterviewPhase.COMPLETED

def test_state_machine_rejects_invalid_transitions(orchestrator_setup):
    orch, mock_db, _ = orchestrator_setup
    session_res = mock_db.create_session("user-456", "Software Engineer")
    session_id = session_res['session_id']

    state = orch.initialize_session(session_id, "user-456", "Software Engineer", "Software Engineer")
    assert state.phase == InterviewPhase.INITIALIZING

    # Cannot transition directly from INITIALIZING to EVALUATING or COMPLETED
    res = orch._transition_to(state, InterviewPhase.EVALUATING)
    assert res is False
    assert state.phase == InterviewPhase.INITIALIZING

    # Transition to COMPLETED
    orch._transition_to(state, InterviewPhase.QUESTIONING)
    orch._transition_to(state, InterviewPhase.FINAL_ASSESSMENT)
    orch._transition_to(state, InterviewPhase.COMPLETED)
    assert state.phase == InterviewPhase.COMPLETED

    # Cannot transition out of COMPLETED
    res2 = orch._transition_to(state, InterviewPhase.QUESTIONING)
    assert res2 is False
    assert state.phase == InterviewPhase.COMPLETED

# ==================== TESTS FOR DIFFICULTY ADAPTATION ====================

def test_difficulty_adaptation_increases_on_strong_streak(orchestrator_setup):
    orch, mock_db, mock_ai = orchestrator_setup
    session_res = mock_db.create_session("user-789", "Software Engineer")
    session_id = session_res['session_id']

    policy = SessionPolicy(
        consecutive_strong_for_increase=2,
        strong_score_threshold=80.0
    )
    orch.initialize_session(session_id, "user-789", "Software Engineer", "Software Engineer", policy=policy)

    # Starts at INTERMEDIATE
    state = orch.get_or_restore_state(session_id)
    assert state.difficulty == DifficultyLevel.INTERMEDIATE

    # Strong answer 1
    mock_ai.next_score = 90
    q1 = orch.get_next_question(session_id, policy=policy)
    res1 = orch.record_and_evaluate_answer(session_id, q1['question_id'], "Great answer 1", policy=policy)
    assert res1['current_difficulty'] == DifficultyLevel.INTERMEDIATE.value

    # Strong answer 2 -> triggers difficulty bump to ADVANCED
    mock_ai.next_score = 92
    q2 = orch.get_next_question(session_id, policy=policy)
    res2 = orch.record_and_evaluate_answer(session_id, q2['question_id'], "Great answer 2", policy=policy)
    assert res2['current_difficulty'] == DifficultyLevel.ADVANCED.value
    assert res2['difficulty_adjusted'] is True

    # High score at ADVANCED stays bounded at ADVANCED
    q3 = orch.get_next_question(session_id, policy=policy)
    res3 = orch.record_and_evaluate_answer(session_id, q3['question_id'], "Great answer 3", policy=policy)
    assert res3['current_difficulty'] == DifficultyLevel.ADVANCED.value

def test_difficulty_adaptation_decreases_on_weak_streak(orchestrator_setup):
    orch, mock_db, mock_ai = orchestrator_setup
    session_res = mock_db.create_session("user-101", "Software Engineer")
    session_id = session_res['session_id']

    policy = SessionPolicy(
        consecutive_weak_for_decrease=2,
        weak_score_threshold=50.0
    )
    orch.initialize_session(session_id, "user-101", "Software Engineer", "Software Engineer", policy=policy)

    state = orch.get_or_restore_state(session_id)
    assert state.difficulty == DifficultyLevel.INTERMEDIATE

    # Weak answer 1
    mock_ai.next_score = 40
    q1 = orch.get_next_question(session_id, policy=policy)
    res1 = orch.record_and_evaluate_answer(session_id, q1['question_id'], "Poor answer 1", policy=policy)
    assert res1['current_difficulty'] == DifficultyLevel.INTERMEDIATE.value

    # Weak answer 2 -> triggers decrease to BEGINNER
    mock_ai.next_score = 45
    q2 = orch.get_next_question(session_id, policy=policy)
    res2 = orch.record_and_evaluate_answer(session_id, q2['question_id'], "Poor answer 2", policy=policy)
    assert res2['current_difficulty'] == DifficultyLevel.BEGINNER.value
    assert res2['difficulty_adjusted'] is True

    # Weak answer at BEGINNER stays bounded at BEGINNER
    q3 = orch.get_next_question(session_id, policy=policy)
    res3 = orch.record_and_evaluate_answer(session_id, q3['question_id'], "Poor answer 3", policy=policy)
    assert res3['current_difficulty'] == DifficultyLevel.BEGINNER.value

def test_difficulty_streak_resets_on_middle_score(orchestrator_setup):
    orch, mock_db, mock_ai = orchestrator_setup
    session_res = mock_db.create_session("user-102", "Software Engineer")
    session_id = session_res['session_id']

    policy = SessionPolicy(consecutive_strong_for_increase=2, strong_score_threshold=80.0)
    orch.initialize_session(session_id, "user-102", "Software Engineer", "Software Engineer", policy=policy)

    # 1 strong answer
    mock_ai.next_score = 85
    q1 = orch.get_next_question(session_id, policy=policy)
    orch.record_and_evaluate_answer(session_id, q1['question_id'], "Answer 1", policy=policy)
    state = orch.get_or_restore_state(session_id)
    assert state.current_consecutive_strong == 1

    # 1 average answer -> streak resets
    mock_ai.next_score = 65
    q2 = orch.get_next_question(session_id, policy=policy)
    orch.record_and_evaluate_answer(session_id, q2['question_id'], "Answer 2", policy=policy)
    state = orch.get_or_restore_state(session_id)
    assert state.current_consecutive_strong == 0
    assert state.difficulty == DifficultyLevel.INTERMEDIATE

# ==================== TESTS FOR DUPLICATE QUESTION PREVENTION ====================

def test_duplicate_question_prevention(orchestrator_setup):
    orch, mock_db, mock_ai = orchestrator_setup
    session_res = mock_db.create_session("user-dup", "Software Engineer")
    session_id = session_res['session_id']

    orch.initialize_session(session_id, "user-dup", "Software Engineer", "Software Engineer")

    # Ask first question
    q1 = orch.get_next_question(session_id)

    # Enable duplicate mode in mock AI to simulate AI trying to repeat
    mock_ai.duplicate_mode = True

    # Next question must not equal previous question
    q2 = orch.get_next_question(session_id)
    assert q1['question_text'] != q2['question_text']

    # Verifying exclusion list was passed to AI
    state = orch.get_or_restore_state(session_id)
    assert len(state.questions_asked) == 2
    assert state.questions_asked[0].question_text != state.questions_asked[1].question_text

# ==================== TESTS FOR SKILL DISTRIBUTION & FOLLOW-UPS ====================

def test_balanced_skill_distribution(orchestrator_setup):
    orch, mock_db, mock_ai = orchestrator_setup
    session_res = mock_db.create_session("user-skills", "Software Engineer")
    session_id = session_res['session_id']

    orch.initialize_session(session_id, "user-skills", "Software Engineer", "Software Engineer")
    skills = get_skills_for_role("Software Engineer")

    # Ask 3 questions and verify each tackles a distinct skill focus
    seen_skills = []
    for _ in range(3):
        q = orch.get_next_question(session_id)
        orch.record_and_evaluate_answer(session_id, q['question_id'], "Standard answer")
        seen_skills.append(q['skill_focus'])

    # Ensure all 3 chosen skills were unique and drawn from the role's skill set
    assert len(set(seen_skills)) == 3
    for s in seen_skills:
        assert s in skills

def test_targeted_follow_up_on_weakness(orchestrator_setup):
    orch, mock_db, mock_ai = orchestrator_setup
    session_res = mock_db.create_session("user-followup", "Software Engineer")
    session_id = session_res['session_id']

    policy = SessionPolicy(follow_up_threshold=65.0, max_follow_ups_per_session=1)
    orch.initialize_session(session_id, "user-followup", "Software Engineer", "Software Engineer", policy=policy)

    # Initial question
    q1 = orch.get_next_question(session_id, policy=policy)
    assert q1['is_follow_up'] is False

    # Submit weak answer with specific weakness
    mock_ai.next_score = 55
    mock_ai.next_weaknesses = ["Failed to explain thread safety"]
    orch.record_and_evaluate_answer(session_id, q1['question_id'], "Vague answer", policy=policy)

    state = orch.get_or_restore_state(session_id)
    assert len(state.follow_up_opportunities) == 1

    # Next question must be a targeted follow-up!
    q2 = orch.get_next_question(session_id, policy=policy)
    assert q2['is_follow_up'] is True
    assert "thread safety" in q2['question_text'] or "Failed to explain thread safety" in q2['question_text']
    assert q2['phase'] == InterviewPhase.FOLLOW_UP.value

def test_session_policy_auto_completion(orchestrator_setup):
    orch, mock_db, mock_ai = orchestrator_setup
    session_res = mock_db.create_session("user-policy", "Software Engineer")
    session_id = session_res['session_id']

    # Set policy with max 2 questions
    policy = SessionPolicy(max_questions=2)
    orch.initialize_session(session_id, "user-policy", "Software Engineer", "Software Engineer", policy=policy)

    q1 = orch.get_next_question(session_id, policy=policy)
    orch.record_and_evaluate_answer(session_id, q1['question_id'], "Answer 1", policy=policy)

    q2 = orch.get_next_question(session_id, policy=policy)
    orch.record_and_evaluate_answer(session_id, q2['question_id'], "Answer 2", policy=policy)

    # Next get_question must trigger finalization and completion
    final_res = orch.get_next_question(session_id, policy=policy)
    assert final_res['is_completed'] is True
    assert final_res['phase'] == InterviewPhase.COMPLETED.value

    # Session state endpoint verifies completion
    session_state = orch.get_session_state(session_id)
    assert session_state['is_completed'] is True
    assert session_state['phase'] == InterviewPhase.COMPLETED.value
    assert session_state['answered_count'] == 2

def test_state_transitions_persist_events(orchestrator_setup):
    orch, mock_db, _ = orchestrator_setup
    session_res = mock_db.create_session("user-events", "Software Engineer")
    session_id = session_res['session_id']

    orch.initialize_session(session_id, "user-events", "Software Engineer", "Software Engineer")
    q = orch.get_next_question(session_id)
    orch.record_and_evaluate_answer(session_id, q['question_id'], "Answer text")

    # Check that events were logged in mock Supabase
    event_types = [log['event_type'] for log in mock_db.logs if log['session_id'] == session_id]
    assert 'orchestrator_initialized' in event_types
    assert 'state_transition' in event_types
    assert 'orchestrator_question_delivered' in event_types

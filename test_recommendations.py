import pytest
from app.services.orchestrator.intelligence import CandidateSkillProfile, SkillEvidence
from app.services.orchestrator.recommendations import (
    RecommendationEngine,
    Recommendation,
    RecommendationStrategy,
    RecommendationPriority,
    RecommendationStatus
)
from app.services.supabase_service import SupabaseService
import os
import json

# Ensure test environment variables are set for Flask app factory
os.environ.setdefault('SUPABASE_URL', 'https://dummy.supabase.co')
os.environ.setdefault('SUPABASE_KEY', 'dummy-key')
os.environ.setdefault('GEMINI_API_KEY', 'dummy-gemini-key')

from app import create_app

# ---------------------------------------------------------------------------
# Test 1: Explainability & Structure Validation
# ---------------------------------------------------------------------------

def test_recommendation_structure_and_explainability():
    """Verify that every generated recommendation contains all required explainability fields."""
    engine = RecommendationEngine()
    user_id = "candidate_123"

    profile = CandidateSkillProfile(
        user_id=user_id,
        skill_name="Data Structures & Algorithms",
        estimated_proficiency=42.0,
        confidence="medium confidence",
        evidence_count=3,
        recent_performance=40.0,
        historical_performance=45.0,
        improvement_trend="declining"
    )

    recs = engine.generate_recommendations(user_id=user_id, skill_profiles=[profile])

    assert len(recs) > 0
    for rec in recs:
        # Must contain all required fields
        assert rec.target_skill != ""
        assert rec.reason != ""
        assert rec.evidence is not None and len(rec.evidence) > 0
        assert rec.recommended_activity is not None and len(rec.recommended_activity) > 0
        assert rec.priority in [p for p in RecommendationPriority]
        assert rec.expected_learning_objective != ""

        # Check for explainability vs generic fluff
        assert "keep up" not in rec.reason.lower()
        assert "believe" not in rec.reason.lower()
        assert "motivat" not in rec.reason.lower()


# ---------------------------------------------------------------------------
# Test 2: Specific Scenario 1 - Weak Algorithmic Reasoning
# ---------------------------------------------------------------------------

def test_recommendation_weak_algorithmic_reasoning():
    """Weak algorithmic reasoning should recommend targeted algorithm practice."""
    engine = RecommendationEngine()
    user_id = "candidate_algo"

    profile = CandidateSkillProfile(
        user_id=user_id,
        skill_name="Data Structures & Algorithms",
        estimated_proficiency=45.0,
        confidence="medium confidence",
        evidence_count=3,
        recent_performance=40.0,
        historical_performance=50.0,
        improvement_trend="declining"
    )

    recs = engine.generate_recommendations(user_id=user_id, skill_profiles=[profile])

    algo_recs = [r for r in recs if r.strategy == RecommendationStrategy.PRACTICE_SESSION and "algorithm" in r.target_skill.lower()]
    assert len(algo_recs) >= 1
    algo_rec = algo_recs[0]
    assert algo_rec.target_skill == "Data Structures & Algorithms"
    assert "algorithmic" in algo_rec.reason.lower() or "proficiency" in algo_rec.reason.lower()
    assert "practice" in algo_rec.recommended_activity.get('type', '') or "drill" in algo_rec.recommended_activity.get('title', '').lower()
    assert algo_rec.priority in (RecommendationPriority.HIGH, RecommendationPriority.CRITICAL)


# ---------------------------------------------------------------------------
# Test 3: Specific Scenario 2 - Strong Coding Correctness but Weak Explanation
# ---------------------------------------------------------------------------

def test_recommendation_strong_code_weak_explanation():
    """Strong coding correctness with weak readability/code quality should recommend explanation-focused interview questions."""
    engine = RecommendationEngine()
    user_id = "candidate_code_comm"

    # Evaluated question: 95 correctness, but readability 40, code_quality 50
    session_questions = [{
        'id': 'q_coding_1',
        'question_text': 'Implement an LRU Cache with O(1) operations.',
        'code_text': 'class LRUCache:...',
        'code_evaluation_score': 70.0,
        'code_evaluation_details': {
            'overall_score': 70,
            'correctness': 95,
            'readability': 40,
            'code_quality': 50,
            'issues': ['Variable names obscure', 'No commentary on invariants']
        }
    }]

    comm_profile = CandidateSkillProfile(
        user_id=user_id,
        skill_name="Communication",
        estimated_proficiency=55.0,
        confidence="low confidence",
        evidence_count=1
    )

    recs = engine.generate_recommendations(
        user_id=user_id,
        skill_profiles=[comm_profile],
        session_questions=session_questions,
        session_id="sess_101"
    )

    explanation_recs = [r for r in recs if r.strategy == RecommendationStrategy.NEXT_INTERVIEW and r.target_skill == "Communication"]
    assert len(explanation_recs) == 1
    rec = explanation_recs[0]
    assert "correctness" in rec.reason.lower()
    assert "explanation" in rec.reason.lower() or "clarity" in rec.reason.lower()
    assert rec.priority == RecommendationPriority.HIGH
    assert "articulate" in rec.expected_learning_objective.lower() or "explain" in rec.expected_learning_objective.lower()


# ---------------------------------------------------------------------------
# Test 4: Specific Scenario 3 - Strong Implementation but Poor Complexity Analysis
# ---------------------------------------------------------------------------

def test_recommendation_strong_implementation_poor_complexity():
    """Strong implementation but poor complexity analysis should generate targeted complexity drill."""
    engine = RecommendationEngine()
    user_id = "candidate_complexity"

    session_questions = [{
        'id': 'q_code_2',
        'question_text': 'Find all triplets in array that sum to zero.',
        'code_text': 'def threeSum(nums):...',
        'code_evaluation_score': 75.0,
        'code_evaluation_details': {
            'overall_score': 75,
            'correctness': 85,
            'complexity': 'Suboptimal O(N^3) cubic time complexity when O(N^2) was achievable',
            'issues': ['Cubic time complexity issue', 'Unnecessary nested loops']
        }
    }]

    dsa_profile = CandidateSkillProfile(
        user_id=user_id,
        skill_name="Data Structures & Algorithms",
        estimated_proficiency=65.0,
        confidence="medium confidence",
        evidence_count=2
    )

    recs = engine.generate_recommendations(
        user_id=user_id,
        skill_profiles=[dsa_profile],
        session_questions=session_questions
    )

    comp_recs = [r for r in recs if "complexity" in r.recommended_activity.get('title', '').lower()]
    assert len(comp_recs) == 1
    rec = comp_recs[0]
    assert rec.strategy == RecommendationStrategy.PRACTICE_SESSION
    assert "complexity" in rec.reason.lower()
    assert "big-o" in rec.expected_learning_objective.lower() or "complexity" in rec.expected_learning_objective.lower()


# ---------------------------------------------------------------------------
# Test 5: Specific Scenario 4 - Repeated Weakness in System Design
# ---------------------------------------------------------------------------

def test_recommendation_repeated_system_design_weakness():
    """Repeated weakness in system design should recommend progressive system design practice."""
    engine = RecommendationEngine()
    user_id = "candidate_sys_design"

    profile = CandidateSkillProfile(
        user_id=user_id,
        skill_name="System Design",
        estimated_proficiency=48.0,
        confidence="high confidence",
        evidence_count=4,
        recent_performance=45.0,
        historical_performance=50.0,
        improvement_trend="declining"
    )

    recs = engine.generate_recommendations(user_id=user_id, skill_profiles=[profile])

    sd_recs = [r for r in recs if r.target_skill == "System Design" and r.strategy == RecommendationStrategy.PRACTICE_SESSION]
    assert len(sd_recs) == 1
    rec = sd_recs[0]
    assert rec.priority == RecommendationPriority.CRITICAL  # Repeated is elevated to CRITICAL
    assert "repeated" in rec.reason.lower()
    assert "progressive" in rec.recommended_activity.get('title', '').lower() or "progressive" in str(rec.recommended_activity).lower()


# ---------------------------------------------------------------------------
# Test 6: Strategies - Skill Reinforcement & Weak-Signal Validation
# ---------------------------------------------------------------------------

def test_recommendation_skill_reinforcement_and_weak_signal():
    """Test skill reinforcement for high performers and weak-signal validation for sparse signals."""
    engine = RecommendationEngine()
    user_id = "candidate_multi"

    high_skill = CandidateSkillProfile(
        user_id=user_id,
        skill_name="Database Concepts",
        estimated_proficiency=88.0,
        confidence="medium confidence",
        evidence_count=3,
        recent_performance=90.0,
        historical_performance=86.0,
        improvement_trend="improving"
    )

    sparse_skill = CandidateSkillProfile(
        user_id=user_id,
        skill_name="Machine Learning",
        estimated_proficiency=65.0,
        confidence="insufficient evidence",
        evidence_count=1,
        recent_performance=65.0,
        historical_performance=0.0,
        improvement_trend="neutral"
    )

    recs = engine.generate_recommendations(user_id=user_id, skill_profiles=[high_skill, sparse_skill])

    strategies = [r.strategy for r in recs]
    assert RecommendationStrategy.SKILL_REINFORCEMENT in strategies
    assert RecommendationStrategy.WEAK_SIGNAL_VALIDATION in strategies

    # Verify reinforcement
    reinf_rec = next(r for r in recs if r.strategy == RecommendationStrategy.SKILL_REINFORCEMENT)
    assert reinf_rec.target_skill == "Database Concepts"
    assert "reinforce" in reinf_rec.reason.lower()

    # Verify weak-signal
    weak_rec = next(r for r in recs if r.strategy == RecommendationStrategy.WEAK_SIGNAL_VALIDATION)
    assert weak_rec.target_skill == "Machine Learning"
    assert "confidence" in weak_rec.reason.lower() or "evidence" in weak_rec.reason.lower()


# ---------------------------------------------------------------------------
# Test 7: Review of Prior Mistakes Strategy
# ---------------------------------------------------------------------------

def test_recommendation_review_prior_mistakes():
    """Failed question should trigger review_prior_mistakes recommendation."""
    engine = RecommendationEngine()
    user_id = "candidate_mistakes"

    session_questions = [{
        'id': 'q_failed_1',
        'question_text': 'Explain consensus algorithms in distributed systems.',
        'interview_type': 'System Design',
        'evaluation_score': 35.0,
        'evaluation_details': {
            'overall_score': 35,
            'weaknesses': ['Confused Raft leader election with Paxos', 'Did not handle network partition split brain']
        }
    }]

    recs = engine.generate_recommendations(
        user_id=user_id,
        skill_profiles=[],
        session_questions=session_questions
    )

    mistake_recs = [r for r in recs if r.strategy == RecommendationStrategy.REVIEW_PRIOR_MISTAKES]
    assert len(mistake_recs) == 1
    rec = mistake_recs[0]
    assert rec.priority == RecommendationPriority.HIGH
    assert "scored 35" in rec.reason or "35.0" in rec.reason
    assert "raft" in str(rec.evidence).lower()


# ---------------------------------------------------------------------------
# Test 8: Outcome Tracking & Performance Delta Evaluation
# ---------------------------------------------------------------------------

def test_recommendation_outcome_evaluation():
    """Test tracking outcome of recommendation and calculating delta."""
    engine = RecommendationEngine()
    user_id = "candidate_outcome"

    rec = Recommendation(
        user_id=user_id,
        target_skill="Data Structures & Algorithms",
        strategy=RecommendationStrategy.PRACTICE_SESSION,
        reason="Initial score was low",
        evidence={"score": 45.0},
        recommended_activity={"title": "Algorithm Drill"},
        priority=RecommendationPriority.HIGH,
        expected_learning_objective="Improve tree traversal",
        baseline_proficiency=45.0
    )

    assert rec.status == RecommendationStatus.PENDING

    # Candidate improves from 45.0 to 65.0 (+20.0 delta)
    evaluated = engine.evaluate_outcome(rec, current_proficiency=65.0)

    assert evaluated.status == RecommendationStatus.COMPLETED
    assert evaluated.baseline_proficiency == 45.0
    assert evaluated.post_outcome_proficiency == 65.0
    assert evaluated.outcome_delta == 20.0
    assert evaluated.outcome_assessment == "improved"
    assert evaluated.completed_at is not None

    # Test declined scenario
    rec_declined = Recommendation(
        user_id=user_id,
        target_skill="System Design",
        strategy=RecommendationStrategy.PRACTICE_SESSION,
        reason="Needs work",
        priority=RecommendationPriority.HIGH,
        expected_learning_objective="Scale caching",
        baseline_proficiency=60.0
    )
    evaluated_declined = engine.evaluate_outcome(rec_declined, current_proficiency=50.0)
    assert evaluated_declined.outcome_delta == -10.0
    assert evaluated_declined.outcome_assessment == "declined"


# ---------------------------------------------------------------------------
# Test 9: Supabase Persistence & Local Fallback
# ---------------------------------------------------------------------------

def test_supabase_recommendation_persistence():
    """Verify SupabaseService persistence methods and retrieval."""
    supabase = SupabaseService()
    user_id = "u_persist_test"

    rec_data = {
        'user_id': user_id,
        'target_skill': 'Debugging',
        'strategy': RecommendationStrategy.PRACTICE_SESSION.value,
        'reason': 'Multiple syntax & runtime errors encountered',
        'evidence': {'error_count': 3},
        'recommended_activity': {'type': 'debugger_drill'},
        'priority': RecommendationPriority.HIGH.value,
        'expected_learning_objective': 'Systematic stack trace inspection',
        'status': RecommendationStatus.PENDING.value,
        'baseline_proficiency': 50.0
    }

    # 1. Create
    created = supabase.create_recommendations(user_id, [rec_data])
    assert len(created) == 1
    rec_id = created[0]['id']

    # 2. Get list
    fetched_list = supabase.get_recommendations(user_id, status="PENDING")
    assert any(r['id'] == rec_id for r in fetched_list)

    # 3. Get single
    single = supabase.get_recommendation(rec_id)
    assert single is not None
    assert single['target_skill'] == 'Debugging'

    # 4. Update status
    updated = supabase.update_recommendation(rec_id, {'status': 'COMPLETED', 'outcome_delta': 15.0})
    assert updated is True

    updated_single = supabase.get_recommendation(rec_id)
    assert updated_single['status'] == 'COMPLETED'
    assert updated_single['outcome_delta'] == 15.0


# ---------------------------------------------------------------------------
# Test 10: Backend API Endpoints Integration Test
# ---------------------------------------------------------------------------

def test_recommendation_api_endpoints():
    """Test Flask routes for recommendation generation, listing, status update, and outcome evaluation."""
    app = create_app()
    client = app.test_client()
    user_id = "u_api_candidate"

    # 1. Generate recommendations
    gen_resp = client.post(f'/api/intelligence/recommendations/{user_id}/generate', json={})
    assert gen_resp.status_code == 201
    gen_data = gen_resp.get_json()
    assert gen_data['success'] is True
    recs = gen_data['recommendations']
    assert len(recs) > 0

    target_rec_id = recs[0]['id']

    # 2. List recommendations
    list_resp = client.get(f'/api/intelligence/recommendations/{user_id}?status=PENDING')
    assert list_resp.status_code == 200
    list_data = list_resp.get_json()
    assert list_data['success'] is True
    assert list_data['count'] > 0

    # 3. Update status (e.g. ACCEPTED)
    status_resp = client.patch(f'/api/intelligence/recommendations/{target_rec_id}/status', json={'status': 'ACCEPTED'})
    assert status_resp.status_code == 200
    status_data = status_resp.get_json()
    assert status_data['recommendation']['status'] == 'ACCEPTED'

    # 4. Evaluate outcome
    outcome_resp = client.post(
        f'/api/intelligence/recommendations/{target_rec_id}/evaluate_outcome',
        json={'current_proficiency': 82.0}
    )
    assert outcome_resp.status_code == 200
    outcome_data = outcome_resp.get_json()
    assert outcome_data['success'] is True
    assert outcome_data['outcome']['status'] == 'COMPLETED'
    assert outcome_data['outcome']['post_outcome_proficiency'] == 82.0

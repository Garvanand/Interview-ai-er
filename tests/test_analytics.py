import pytest
from datetime import datetime, timezone, timedelta
from app.services.analytics.models import (
    AnalyticsFilter,
    LongitudinalAnalyticsResponse
)
from app.services.analytics.methodology import (
    calculate_score_trends,
    calculate_skill_trends,
    calculate_question_type_performance,
    calculate_difficulty_progression,
    calculate_consistency,
    calculate_repeated_weaknesses,
    calculate_recommendation_impact,
    calculate_recent_vs_historical,
    calculate_completion_behavior,
    generate_next_practice_recommendations
)
from app.services.analytics.service import LongitudinalAnalyticsService

# ============================================================================
# Known Fixture Datasets
# ============================================================================

@pytest.fixture
def growth_candidate_dataset():
    """Known fixture: Candidate demonstrating steady, sustained improvement across 5 sessions."""
    base_time = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    sessions = [
        {
            'id': 'sess-1',
            'interview_type': 'Fullstack Engineer',
            'start_time': (base_time + timedelta(days=1)).isoformat(),
            'end_time': (base_time + timedelta(days=1, minutes=45)).isoformat(),
            'score': 55.0,
            'status': 'completed'
        },
        {
            'id': 'sess-2',
            'interview_type': 'Fullstack Engineer',
            'start_time': (base_time + timedelta(days=3)).isoformat(),
            'end_time': (base_time + timedelta(days=3, minutes=40)).isoformat(),
            'score': 62.0,
            'status': 'completed'
        },
        {
            'id': 'sess-3',
            'interview_type': 'Fullstack Engineer',
            'start_time': (base_time + timedelta(days=6)).isoformat(),
            'end_time': (base_time + timedelta(days=6, minutes=50)).isoformat(),
            'score': 72.0,
            'status': 'completed'
        },
        {
            'id': 'sess-4',
            'interview_type': 'Fullstack Engineer',
            'start_time': (base_time + timedelta(days=10)).isoformat(),
            'end_time': (base_time + timedelta(days=10, minutes=45)).isoformat(),
            'score': 80.0,
            'status': 'completed'
        },
        {
            'id': 'sess-5',
            'interview_type': 'Fullstack Engineer',
            'start_time': (base_time + timedelta(days=15)).isoformat(),
            'end_time': (base_time + timedelta(days=15, minutes=45)).isoformat(),
            'score': 88.0,
            'status': 'completed'
        }
    ]

    questions_by_session = {
        'sess-1': [
            {'id': 'q1', 'session_id': 'sess-1', 'difficulty': 'beginner', 'skill_focus': 'Algorithms', 'evaluation_score': 55.0, 'created_at': (base_time + timedelta(days=1)).isoformat()}
        ],
        'sess-2': [
            {'id': 'q2', 'session_id': 'sess-2', 'difficulty': 'intermediate', 'skill_focus': 'Algorithms', 'evaluation_score': 62.0, 'created_at': (base_time + timedelta(days=3)).isoformat()}
        ],
        'sess-3': [
            {'id': 'q3', 'session_id': 'sess-3', 'difficulty': 'intermediate', 'skill_focus': 'System Design', 'evaluation_score': 72.0, 'created_at': (base_time + timedelta(days=6)).isoformat()}
        ],
        'sess-4': [
            {'id': 'q4', 'session_id': 'sess-4', 'difficulty': 'advanced', 'skill_focus': 'Algorithms', 'evaluation_score': 80.0, 'created_at': (base_time + timedelta(days=10)).isoformat()}
        ],
        'sess-5': [
            {'id': 'q5', 'session_id': 'sess-5', 'difficulty': 'advanced', 'skill_focus': 'System Design', 'evaluation_score': 88.0, 'created_at': (base_time + timedelta(days=15)).isoformat()}
        ]
    }
    return sessions, questions_by_session


@pytest.fixture
def volatile_candidate_scores():
    """Known fixture: Candidate with wildly inconsistent performance."""
    return [95.0, 42.0, 90.0, 38.0, 88.0]


@pytest.fixture
def repeated_weakness_dataset():
    """Known fixture: Candidate with repeated errors in time complexity and edge cases."""
    base_time = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    return [
        {
            'id': 'q101',
            'session_id': 'sess-10',
            'skill_focus': 'Algorithms',
            'evaluation_score': 50.0,
            'created_at': (base_time + timedelta(days=1)).isoformat(),
            'evaluation_details': {
                'weaknesses': ['Suboptimal time complexity O(n^2), expected O(n log n)', 'Failed null input edge case']
            }
        },
        {
            'id': 'q102',
            'session_id': 'sess-11',
            'skill_focus': 'Algorithms',
            'evaluation_score': 58.0,
            'created_at': (base_time + timedelta(days=3)).isoformat(),
            'evaluation_details': {
                'weaknesses': ['Runtime exceeded limits due to quadratic time complexity', 'Did not handle empty boundary']
            }
        },
        {
            'id': 'q103',
            'session_id': 'sess-12',
            'skill_focus': 'Data Structures',
            'evaluation_score': 60.0,
            'created_at': (base_time + timedelta(days=6)).isoformat(),
            'evaluation_details': {
                'weaknesses': ['Inefficient loop resulting in slow execution and timeout']
            }
        },
        {
            'id': 'q104',
            'session_id': 'sess-13',
            'skill_focus': 'Algorithms',
            'evaluation_score': 65.0,
            'created_at': (base_time + timedelta(days=8)).isoformat(),
            'evaluation_details': {
                'weaknesses': ['Missed zero index boundary condition and overflow edge case']
            }
        }
    ]


# ============================================================================
# Unit & Regression Tests
# ============================================================================

def test_growth_trajectory_regression_slope(growth_candidate_dataset):
    """Verifies OLS slope calculation, difficulty adjustment, and trajectory classification."""
    sessions, questions_by_session = growth_candidate_dataset
    trend = calculate_score_trends(sessions, questions_by_session)

    # With scores [55, 62, 72, 80, 88] over x = [1, 2, 3, 4, 5]:
    # x_mean = 3, y_mean = 71.4
    # numerator = (-2*-16.4) + (-1*-9.4) + (0) + (1*8.6) + (2*16.6) = 32.8 + 9.4 + 8.6 + 33.2 = 84.0
    # denominator = 4 + 1 + 0 + 1 + 4 = 10
    # slope = 8.4
    assert trend.total_sessions_analyzed == 5
    assert trend.linear_regression_slope == pytest.approx(8.4, abs=0.1)
    assert trend.r_squared >= 0.95
    assert trend.trajectory_classification == "significant_improvement"

    # Difficulty normalization test:
    # Session 5 (score 88, difficulty advanced=1.25) -> 88 * (0.7 + 0.3 * 1.25) = 88 * 1.075 = 94.6
    s5_point = trend.data_points[-1]
    assert s5_point.difficulty_adjusted_score > s5_point.raw_score
    assert s5_point.difficulty_adjusted_score == pytest.approx(94.6, abs=0.2)

    # 3-period Moving Average on session 5 should average [72, 80, 88] = 80.0
    assert s5_point.sma_3 == pytest.approx(80.0, abs=0.1)


def test_consistency_and_dispersion(volatile_candidate_scores):
    """Verifies that volatile scores trigger High Variance classification and valid CV."""
    consistency = calculate_consistency(volatile_candidate_scores)

    # Scores: [95, 42, 90, 38, 88] -> Mean = 70.6
    assert consistency.score_count == 5
    assert consistency.mean_score == pytest.approx(70.6, abs=0.2)
    assert consistency.median_score == 88.0
    assert consistency.min_score == 38.0
    assert consistency.max_score == 95.0
    assert consistency.score_range == 57.0

    # High standard deviation and CV >= 30%
    assert consistency.standard_deviation > 24.0
    assert consistency.coefficient_of_variation > 34.0
    assert consistency.consistency_category == "Volatile / High Variance"
    # Consistency index should be penalized below 50
    assert consistency.consistency_index < 50.0


def test_repeated_weaknesses_clustering_and_persistence(repeated_weakness_dataset):
    """Verifies canonical clustering and persistent blocker detection across multiple sessions."""
    weaknesses = calculate_repeated_weaknesses(repeated_weakness_dataset, total_sessions_count=4)

    clusters = {w.weakness_cluster: w for w in weaknesses}
    assert "time_complexity" in clusters
    assert "edge_case_handling" in clusters

    tc = clusters["time_complexity"]
    assert tc.canonical_label == "Time Complexity & Algorithmic Efficiency"
    assert tc.total_occurrences >= 3
    # Distinct sessions: sess-10, sess-11, sess-12 (3 distinct sessions out of 4 = 75%)
    assert tc.distinct_sessions_count == 3
    assert tc.persistence_status == "persistent_blocker"
    assert len(tc.evidence_snippets) > 0

    ec = clusters["edge_case_handling"]
    assert ec.canonical_label == "Edge Case & Boundary Condition Coverage"
    assert ec.distinct_sessions_count >= 2


def test_difficulty_progression_frontier():
    """Verifies adaptive difficulty frontier and promotion retention rate."""
    base_time = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    questions = [
        # Session 1: Beginner (85) -> Intermediate (75) [Sustained promotion]
        {'id': 'q1', 'session_id': 's1', 'difficulty': 'beginner', 'evaluation_score': 85.0, 'created_at': (base_time + timedelta(minutes=5)).isoformat()},
        {'id': 'q2', 'session_id': 's1', 'difficulty': 'intermediate', 'evaluation_score': 75.0, 'created_at': (base_time + timedelta(minutes=15)).isoformat()},
        # Session 2: Intermediate (72) -> Advanced (55) [Failed promotion]
        {'id': 'q3', 'session_id': 's2', 'difficulty': 'intermediate', 'evaluation_score': 72.0, 'created_at': (base_time + timedelta(days=2, minutes=5)).isoformat()},
        {'id': 'q4', 'session_id': 's2', 'difficulty': 'advanced', 'evaluation_score': 55.0, 'created_at': (base_time + timedelta(days=2, minutes=20)).isoformat()},
        # Session 3: Advanced (58)
        {'id': 'q5', 'session_id': 's3', 'difficulty': 'advanced', 'evaluation_score': 58.0, 'created_at': (base_time + timedelta(days=3)).isoformat()},
    ]

    prog = calculate_difficulty_progression(questions)

    # 2 promotions attempted (b->i, i->a); 1 sustained (75 >= 70, but 55 < 70)
    assert prog.promotion_transitions_attempted == 2
    assert prog.promotion_sustained_rate == 50.0

    # Intermediate has 2 questions with scores 75 and 72 (avg 73.5 >= 70)
    # Advanced has 2 questions with scores 55 and 58 (avg 56.5 < 70)
    # Frontier should be intermediate
    assert prog.current_performance_frontier == "intermediate"
    assert prog.levels["intermediate"].average_score == pytest.approx(73.5, abs=0.1)
    assert prog.levels["advanced"].average_score == pytest.approx(56.5, abs=0.1)


def test_recommendation_impact_lift():
    """Verifies that post-recommendation questions measure intervention effectiveness."""
    base_time = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    rec_time = base_time + timedelta(days=2)

    recommendations = [
        {
            'id': 'rec-100',
            'target_skill': 'System Design',
            'strategy': 'practice_session',
            'reason': 'Weak horizontal scaling concepts',
            'status': 'COMPLETED',
            'baseline_proficiency': 55.0,
            'completed_at': rec_time.isoformat()
        }
    ]

    # Candidate did 2 subsequent questions after completing recommendation
    questions = [
        {
            'id': 'q_pre',
            'skill_focus': 'System Design',
            'evaluation_score': 52.0,
            'created_at': (base_time + timedelta(days=1)).isoformat()
        },
        {
            'id': 'q_post1',
            'skill_focus': 'System Design',
            'evaluation_score': 78.0,
            'created_at': (base_time + timedelta(days=3)).isoformat()
        },
        {
            'id': 'q_post2',
            'skill_focus': 'System Design',
            'evaluation_score': 82.0,
            'created_at': (base_time + timedelta(days=4)).isoformat()
        }
    ]

    impact_list = calculate_recommendation_impact(recommendations, questions)
    assert len(impact_list) == 1
    imp = impact_list[0]

    assert imp.recommendation_id == 'rec-100'
    assert imp.baseline_proficiency == 55.0
    # Post questions avg = (78 + 82) / 2 = 80.0
    assert imp.post_proficiency == 80.0
    # Delta = 80.0 - 55.0 = +25.0
    assert imp.delta == 25.0
    assert imp.outcome_status == "verified_improvement"
    assert imp.post_questions_evaluated == 2


def test_next_practice_recommendation_priorities():
    """Verifies actionability engine priorities based on real signals."""
    from app.services.analytics.models import SkillTrendSummary, DifficultyProgression, ConsistencyAnalysis

    skill_trends = [
        SkillTrendSummary(
            skill_name="Algorithms",
            evidence_count=5,
            estimated_proficiency=68.0,  # Frontier near mastery (60-74)
            decayed_proficiency=69.0,
            recent_average=72.0,
            historical_average=64.0,
            net_delta=8.0,
            volatility_sd=8.5,
            confidence="medium confidence",
            trend_status="demonstrated_growth"
        ),
        SkillTrendSummary(
            skill_name="Security",
            evidence_count=1,
            estimated_proficiency=60.0,  # Uncalibrated (count 1)
            decayed_proficiency=60.0,
            recent_average=60.0,
            historical_average=60.0,
            net_delta=0.0,
            volatility_sd=0.0,
            confidence="insufficient evidence",
            trend_status="uncalibrated"
        )
    ]

    from app.services.analytics.models import RepeatedWeakness
    repeated_weaknesses = [
        RepeatedWeakness(
            weakness_cluster="time_complexity",
            canonical_label="Time Complexity & Algorithmic Efficiency",
            total_occurrences=4,
            distinct_sessions_count=3,
            session_percentage=60.0,
            recency_flag=True,
            persistence_status="persistent_blocker",
            evidence_snippets=["Quadratic nested iteration"],
            target_skill="Algorithms"
        )
    ]

    diff_prog = DifficultyProgression(current_performance_frontier="intermediate")
    consistency = ConsistencyAnalysis(coefficient_of_variation=14.0)

    practice_recs = generate_next_practice_recommendations(
        skill_trends=skill_trends,
        repeated_weaknesses=repeated_weaknesses,
        difficulty_progression=diff_prog,
        consistency=consistency
    )

    assert len(practice_recs) >= 2
    # Priority 1 must address the persistent blocker
    assert practice_recs[0].priority == 1
    assert "Time Complexity" in practice_recs[0].learning_objective
    assert practice_recs[0].target_skill == "Algorithms"

    # Priority 2 must address the near-frontier mastery skill (Algorithms at 68.0%)
    assert practice_recs[1].priority == 2
    assert "Mastery Threshold" in practice_recs[1].learning_objective


def test_service_filtering_and_empty_state():
    """Verifies that the analytics service applies multidimensional filters cleanly."""
    service = LongitudinalAnalyticsService()

    base_time = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    sessions = [
        {'id': 's1', 'interview_type': 'Frontend Engineer', 'start_time': (base_time + timedelta(days=1)).isoformat(), 'score': 70.0, 'status': 'completed'},
        {'id': 's2', 'interview_type': 'Backend Engineer', 'start_time': (base_time + timedelta(days=5)).isoformat(), 'score': 85.0, 'status': 'completed'}
    ]
    questions = [
        {'id': 'q1', 'session_id': 's1', 'difficulty': 'beginner', 'skill_focus': 'CSS/React', 'interview_type': 'Frontend Engineer', 'evaluation_score': 70.0, 'created_at': (base_time + timedelta(days=1)).isoformat()},
        {'id': 'q2', 'session_id': 's2', 'difficulty': 'advanced', 'skill_focus': 'Databases', 'interview_type': 'Backend Engineer', 'evaluation_score': 85.0, 'created_at': (base_time + timedelta(days=5)).isoformat()}
    ]

    # Filter for Frontend only
    f_sessions, f_questions = service.apply_filters(
        sessions=sessions,
        questions=questions,
        filters=AnalyticsFilter(interview_type='Frontend')
    )
    assert len(f_sessions) == 1
    assert f_sessions[0]['id'] == 's1'
    assert len(f_questions) == 1
    assert f_questions[0]['id'] == 'q1'

    # Filter for impossible date range (empty state)
    f_empty_s, f_empty_q = service.apply_filters(
        sessions=sessions,
        questions=questions,
        filters=AnalyticsFilter(start_date='2027-01-01T00:00:00Z')
    )
    assert len(f_empty_s) == 0
    assert len(f_empty_q) == 0

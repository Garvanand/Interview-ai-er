from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class AnalyticsFilter(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    interview_type: Optional[str] = None
    skill: Optional[str] = None
    difficulty: Optional[str] = None
    question_type: Optional[str] = None

class ScoreTrendPoint(BaseModel):
    session_id: str
    session_index: int
    date: str
    interview_type: str
    raw_score: float
    difficulty_adjusted_score: float
    sma_3: Optional[float] = None
    ema: Optional[float] = None
    difficulty_level: str = "intermediate"
    questions_count: int = 0
    is_completed: bool = True

class ScoreTrendSummary(BaseModel):
    data_points: List[ScoreTrendPoint] = Field(default_factory=list)
    linear_regression_slope: float = 0.0
    r_squared: float = 0.0
    trajectory_classification: str = "insufficient_data"  # significant_improvement, moderate_improvement, stable, moderate_decline, concerning_decline, insufficient_data
    baseline_score: float = 0.0
    current_moving_average: float = 0.0
    difficulty_adjusted_current: float = 0.0
    total_sessions_analyzed: int = 0
    methodology: str = "OLS linear regression on chronologically indexed session scores with 3-period SMA and difficulty-weighted normalization (Beginner=0.85, Intermediate=1.0, Advanced=1.25)."

class SkillTrendSummary(BaseModel):
    skill_name: str
    evidence_count: int
    estimated_proficiency: float
    decayed_proficiency: float
    recent_average: float
    historical_average: float
    net_delta: float
    volatility_sd: float
    confidence: str  # insufficient evidence, low confidence, medium confidence, high confidence
    trend_status: str  # demonstrated_growth, plateaued, skill_regression, uncalibrated
    last_evaluated: Optional[str] = None
    score_history: List[Dict[str, Any]] = Field(default_factory=list)

class QuestionTypePerformance(BaseModel):
    question_type: str  # coding, system_design, algorithmic, conceptual/behavioral
    total_attempted: int
    average_score: float
    median_score: float
    pass_rate: float  # % >= 70.0
    top_strengths: List[str] = Field(default_factory=list)
    top_weaknesses: List[str] = Field(default_factory=list)

class DifficultyLevelStats(BaseModel):
    level: str
    total_attempted: int = 0
    average_score: float = 0.0
    pass_rate: float = 0.0
    standard_deviation: float = 0.0

class DifficultyProgression(BaseModel):
    levels: Dict[str, DifficultyLevelStats] = Field(default_factory=dict)
    promotion_transitions_attempted: int = 0
    promotion_sustained_rate: float = 0.0  # % of times candidate sustained >= 70 when promoted
    current_performance_frontier: str = "beginner"  # highest difficulty where avg >= 70 with >= 2 attempts
    methodology: str = "Evaluates score maintenance across difficulty transitions within adaptive sessions and calculates current frontier threshold (avg >= 70 on >= 2 samples)."

class ConsistencyAnalysis(BaseModel):
    score_count: int = 0
    mean_score: float = 0.0
    median_score: float = 0.0
    standard_deviation: float = 0.0
    coefficient_of_variation: float = 0.0  # (SD / Mean) * 100
    iqr: float = 0.0
    min_score: float = 0.0
    max_score: float = 0.0
    score_range: float = 0.0
    consistency_index: float = 0.0  # max(0, 100 - (CV * 1.5))
    consistency_category: str = "Insufficient Data"  # Highly Consistent, Moderately Consistent, Volatile / High Variance
    methodology: str = "Dispersion measured via Coefficient of Variation (CV = sigma / mu) and Interquartile Range (IQR). Consistency Index scales inverse CV to 0-100."

class RepeatedWeakness(BaseModel):
    weakness_cluster: str
    canonical_label: str
    total_occurrences: int
    distinct_sessions_count: int
    session_percentage: float
    recency_flag: bool  # Appeared in most recent session
    persistence_status: str  # persistent_blocker, emerging_issue, resolving, sporadic
    evidence_snippets: List[str] = Field(default_factory=list)
    target_skill: Optional[str] = None

class RecommendationImpact(BaseModel):
    recommendation_id: str
    target_skill: str
    strategy: str
    reason: str
    completed_at: Optional[str] = None
    baseline_proficiency: float = 0.0
    post_proficiency: Optional[float] = None
    delta: Optional[float] = None
    outcome_status: str = "awaiting_evidence"  # verified_improvement, no_measurable_change, regression, awaiting_evidence
    post_questions_evaluated: int = 0

class RecentVsHistorical(BaseModel):
    recent_period_label: str = "Last 3 Sessions"
    historical_period_label: str = "Prior Sessions"
    recent_average_score: float = 0.0
    historical_average_score: float = 0.0
    score_delta: float = 0.0
    score_pct_change: float = 0.0
    recent_advanced_ratio: float = 0.0
    historical_advanced_ratio: float = 0.0
    recent_consistency_cv: float = 0.0
    historical_consistency_cv: float = 0.0
    recent_sample_size: int = 0
    historical_sample_size: int = 0
    statistically_meaningful: bool = False
    verdict: str = "Insufficient baseline"

class CompletionBehavior(BaseModel):
    total_sessions: int = 0
    completed_sessions: int = 0
    abandoned_sessions: int = 0
    completion_rate: float = 0.0
    avg_duration_minutes: float = 0.0
    avg_questions_per_session: float = 0.0
    completed_avg_score: float = 0.0
    abandoned_avg_score: float = 0.0

class NextPracticeRecommendation(BaseModel):
    priority: int  # 1 = Highest
    target_skill: str
    recommended_difficulty: str
    question_type: str
    learning_objective: str
    rationale: str
    evidence_context: str

class LongitudinalAnalyticsResponse(BaseModel):
    user_id: str
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    filters_applied: AnalyticsFilter
    score_trends: ScoreTrendSummary
    skill_trends: List[SkillTrendSummary] = Field(default_factory=list)
    question_type_performance: List[QuestionTypePerformance] = Field(default_factory=list)
    difficulty_progression: DifficultyProgression
    consistency: ConsistencyAnalysis
    repeated_weaknesses: List[RepeatedWeakness] = Field(default_factory=list)
    recommendation_impact: List[RecommendationImpact] = Field(default_factory=list)
    recent_vs_historical: RecentVsHistorical
    completion_behavior: CompletionBehavior
    next_practice_recommendations: List[NextPracticeRecommendation] = Field(default_factory=list)
    session_evidence: List[Dict[str, Any]] = Field(default_factory=list)

"""
Domain entities for the Interview AI platform.

These are plain Python dataclasses — no ORM, no framework coupling.
They represent the core concepts the system reasons about.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────

class SessionStatus(str, Enum):
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class Difficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class IntegrityEventSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RecommendationPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RecommendationStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    COMPLETED = "COMPLETED"
    DISMISSED = "DISMISSED"


# ─────────────────────────────────────────────────────────────────
# Core entities
# ─────────────────────────────────────────────────────────────────

@dataclass
class InterviewSession:
    id: str
    user_id: str
    interview_type: str
    status: SessionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InterviewQuestion:
    id: str
    session_id: str
    question_text: str
    question_type: str
    difficulty: Difficulty
    skill_focus: Optional[str] = None
    interview_type: Optional[str] = None
    domain: Optional[str] = None
    expected_reasoning: Optional[str] = None
    evaluation_rubric: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class CandidateResponse:
    id: str
    question_id: str
    response_text: str
    submitted_at: datetime
    is_code: bool = False
    programming_language: Optional[str] = None


@dataclass
class Evaluation:
    id: str
    response_id: str
    score: float  # 0–100
    feedback: str
    evaluation_details: Dict[str, Any] = field(default_factory=dict)
    status: str = "COMPLETED"
    created_at: Optional[datetime] = None


@dataclass
class SkillEvidence:
    session_id: str
    question_id: str
    skill_name: str
    score: float
    difficulty: Difficulty
    timestamp: datetime
    evidence_text: Optional[str] = None


@dataclass
class CandidateSkillProfile:
    user_id: str
    skill_name: str
    estimated_proficiency: float        # 0–100
    evidence_count: int
    recent_performance: float
    historical_performance: float
    improvement_trend: str              # 'improving' | 'declining' | 'stable'
    confidence: str                     # 'insufficient evidence' | 'low' | 'medium' | 'high'
    last_evaluated: Optional[datetime] = None


@dataclass
class Recommendation:
    id: str
    user_id: str
    target_skill: str
    strategy: str
    reason: str
    evidence: Dict[str, Any]
    recommended_activity: Dict[str, Any]
    priority: RecommendationPriority
    expected_learning_objective: str
    status: RecommendationStatus = RecommendationStatus.PENDING
    session_id: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    baseline_proficiency: float = 0.0
    post_outcome_proficiency: Optional[float] = None


@dataclass
class IntegrityEvent:
    id: str
    session_id: str
    event_type: str
    severity: IntegrityEventSeverity
    evidence_details: Dict[str, Any]
    timestamp: datetime
    confidence: float = 1.0
    source: str = "browser_api"


@dataclass
class CodeSubmission:
    id: str
    question_id: str
    code_text: str
    programming_language: str
    submitted_at: datetime


@dataclass
class ExecutionRun:
    id: str
    code_submission_id: str
    status: str                # COMPLETED | FAILED | TIMEOUT | SANDBOXED
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    execution_time_ms: Optional[int] = None
    sandbox_note: Optional[str] = None


@dataclass
class AIRun:
    """Records a single AI model invocation for audit and debugging."""
    id: str
    session_id: Optional[str]
    operation: str             # generate_question | evaluate_answer | evaluate_code | synthesize
    model: str
    prompt_tokens: Optional[int]
    latency_seconds: float
    status: str                # success | failed
    error: Optional[str] = None
    created_at: Optional[datetime] = None

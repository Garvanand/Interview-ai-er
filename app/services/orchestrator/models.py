from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class InterviewPhase(str, Enum):
    INITIALIZING = "INITIALIZING"
    QUESTIONING = "QUESTIONING"
    EVALUATING = "EVALUATING"
    FOLLOW_UP = "FOLLOW_UP"
    DIFFICULTY_ADJUSTMENT = "DIFFICULTY_ADJUSTMENT"
    FINAL_ASSESSMENT = "FINAL_ASSESSMENT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

    @classmethod
    def normalize(cls, val: str) -> "DifficultyLevel":
        v = (val or "").strip().lower()
        if v in ("beginner", "easy", "junior"):
            return cls.BEGINNER
        elif v in ("advanced", "hard", "senior"):
            return cls.ADVANCED
        return cls.INTERMEDIATE

    def next_harder(self) -> "DifficultyLevel":
        if self == DifficultyLevel.BEGINNER:
            return DifficultyLevel.INTERMEDIATE
        return DifficultyLevel.ADVANCED

    def next_easier(self) -> "DifficultyLevel":
        if self == DifficultyLevel.ADVANCED:
            return DifficultyLevel.INTERMEDIATE
        return DifficultyLevel.BEGINNER

class SkillSignal(BaseModel):
    skill_name: str
    scores: List[float] = Field(default_factory=list)
    average_score: float = 0.0
    questions_count: int = 0
    weaknesses: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)

    def record_score(self, score: float, strengths: Optional[List[str]] = None, weaknesses: Optional[List[str]] = None):
        self.scores.append(score)
        self.questions_count += 1
        self.average_score = round(sum(self.scores) / len(self.scores), 2)
        if strengths:
            for s in strengths:
                if s not in self.strengths:
                    self.strengths.append(s)
        if weaknesses:
            for w in weaknesses:
                if w not in self.weaknesses:
                    self.weaknesses.append(w)

class QuestionRecord(BaseModel):
    question_id: str
    question_text: str
    difficulty: str
    skill_focus: str
    domain: Optional[str] = None
    is_follow_up: bool = False
    parent_question_id: Optional[str] = None
    score: Optional[float] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class FollowUpOpportunity(BaseModel):
    parent_question_id: str
    parent_question_text: str
    weakness_addressed: str
    suggested_prompt: str
    skill_focus: str

class SessionPolicy(BaseModel):
    max_questions: int = 5
    time_budget_seconds: int = 2700  # 45 minutes
    consecutive_strong_for_increase: int = 2
    consecutive_weak_for_decrease: int = 2
    strong_score_threshold: float = 75.0
    weak_score_threshold: float = 50.0
    follow_up_threshold: float = 65.0
    max_follow_ups_per_session: int = 2

class OrchestratorState(BaseModel):
    session_id: str
    user_id: str
    target_role: str
    interview_type: str
    phase: InterviewPhase = InterviewPhase.INITIALIZING
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    current_skill_focus: Optional[str] = None
    skills_distribution: Dict[str, SkillSignal] = Field(default_factory=dict)
    questions_asked: List[QuestionRecord] = Field(default_factory=list)
    weaknesses_discovered: List[str] = Field(default_factory=list)
    strengths_discovered: List[str] = Field(default_factory=list)
    follow_up_opportunities: List[FollowUpOpportunity] = Field(default_factory=list)
    time_budget_seconds: int = 2700
    start_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    current_consecutive_strong: int = 0
    current_consecutive_weak: int = 0
    follow_ups_asked_count: int = 0
    final_score: Optional[float] = None
    final_assessment: Optional[Dict[str, Any]] = None
    status_message: str = "Interview initialized"

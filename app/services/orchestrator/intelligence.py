from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import math

class SkillEvidence(BaseModel):
    session_id: str
    question_id: str
    score: float
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CandidateSkillProfile(BaseModel):
    user_id: str
    skill_name: str
    estimated_proficiency: float = 0.0
    confidence: str = "insufficient evidence"  # insufficient evidence, low confidence, medium confidence, high confidence
    evidence_count: int = 0
    recent_performance: float = 0.0
    historical_performance: float = 0.0
    improvement_trend: str = "neutral"  # improving, declining, stable, neutral
    last_evaluated_timestamp: Optional[str] = None
    evidence_history: List[SkillEvidence] = Field(default_factory=list)

class SkillEvidenceAggregator:
    """
    Transforms raw interview interactions into a structured longitudinal representation
    of candidate skills. Uses mathematically transparent aggregations.
    """
    
    def __init__(self, recent_window_size: int = 3, historical_weight: float = 0.4, recent_weight: float = 0.6):
        self.recent_window_size = recent_window_size
        self.historical_weight = historical_weight
        self.recent_weight = recent_weight

    def _determine_confidence(self, count: int) -> str:
        """Calculate model confidence based on evidence count (transparent language)."""
        if count < 2:
            return "insufficient evidence"
        elif count < 4:
            return "low confidence"
        elif count < 8:
            return "medium confidence"
        else:
            return "high confidence"

    def _determine_trend(self, recent: float, historical: float, count: int) -> str:
        if count <= self.recent_window_size:
            return "neutral"
        diff = recent - historical
        if diff >= 10.0:
            return "improving"
        elif diff <= -10.0:
            return "declining"
        else:
            return "stable"

    def process_evidence(self, profile: CandidateSkillProfile, new_evidence: SkillEvidence) -> CandidateSkillProfile:
        """
        Incorporate an evidence-backed signal into the candidate skill profile.
        Separates recent vs historical performance explicitly.
        """
        profile.evidence_history.append(new_evidence)
        profile.evidence_history.sort(key=lambda x: x.timestamp)
        
        count = len(profile.evidence_history)
        profile.evidence_count = count
        profile.last_evaluated_timestamp = new_evidence.timestamp
        profile.confidence = self._determine_confidence(count)

        if count == 0:
            return profile
            
        scores = [e.score for e in profile.evidence_history]
        
        if count <= self.recent_window_size:
            # Only recent evidence exists
            profile.recent_performance = round(sum(scores) / count, 2)
            profile.historical_performance = 0.0
            profile.estimated_proficiency = profile.recent_performance
            profile.improvement_trend = "neutral"
        else:
            recent_scores = scores[-self.recent_window_size:]
            historical_scores = scores[:-self.recent_window_size]
            
            profile.recent_performance = round(sum(recent_scores) / len(recent_scores), 2)
            profile.historical_performance = round(sum(historical_scores) / len(historical_scores), 2)
            
            # Weighted aggregation
            proficiency = (self.historical_weight * profile.historical_performance) + (self.recent_weight * profile.recent_performance)
            profile.estimated_proficiency = round(proficiency, 2)
            
            profile.improvement_trend = self._determine_trend(profile.recent_performance, profile.historical_performance, count)

        return profile

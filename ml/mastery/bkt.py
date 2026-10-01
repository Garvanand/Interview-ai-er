"""
Bayesian Knowledge Tracing (BKT) implementation for skill mastery estimation.

This provides a transparent baseline for estimating candidate mastery over time
based on their interaction history.

Note on future calibration:
Once sufficient first-party Interview-ai-er data exists, the P(L0), P(T), P(S), 
and P(G) parameters should be calibrated using Expectation-Maximization (EM) 
or gradient descent on the real interview sequences, replacing these heuristic defaults.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class MasteryEstimate:
    skill: str
    mastery: float
    confidence: float
    evidence_count: int
    trend: str

@dataclass
class Interaction:
    correct: bool
    difficulty: float  # e.g., 0.0 (easy) to 1.0 (hard)
    timestamp: float   # Epoch time
    
class BKTModel:
    def __init__(self, 
                 p_L0: float = 0.3,   # Initial mastery probability
                 p_T: float = 0.1,    # Probability of learning
                 p_G: float = 0.2,    # Probability of guess
                 p_S: float = 0.1):   # Probability of slip
        """
        Initialize BKT parameters. 
        """
        self.p_L0 = p_L0
        self.p_T = p_T
        self.p_G = p_G
        self.p_S = p_S
        
    def _adjust_for_difficulty(self, difficulty: float, p_S: float, p_G: float) -> tuple[float, float]:
        """
        Adjust Slip and Guess probabilities based on question difficulty.
        High difficulty -> higher slip, lower guess.
        Low difficulty -> lower slip, higher guess.
        """
        # Linear adjustment as a baseline heuristic
        adj_S = min(0.9, max(0.01, p_S + (difficulty - 0.5) * 0.1))
        adj_G = min(0.9, max(0.01, p_G - (difficulty - 0.5) * 0.1))
        return adj_S, adj_G

    def predict_sequence(self, skill: str, interactions: List[Interaction]) -> MasteryEstimate:
        """
        Evaluate a sequence of interactions in temporal order to estimate current mastery.
        """
        if not interactions:
            return MasteryEstimate(
                skill=skill,
                mastery=self.p_L0,
                confidence=0.1,  # Low confidence with no evidence
                evidence_count=0,
                trend="stable"
            )
            
        # Sort by timestamp to ensure temporal order
        sorted_interactions = sorted(interactions, key=lambda x: x.timestamp)
        
        p_L = self.p_L0
        mastery_history = [p_L]
        
        for obs in sorted_interactions:
            # Adjust guess/slip dynamically by difficulty
            adj_S, adj_G = self._adjust_for_difficulty(obs.difficulty, self.p_S, self.p_G)
            
            # 1. Update posterior based on observation
            if obs.correct:
                p_L_given_obs = (p_L * (1 - adj_S)) / (p_L * (1 - adj_S) + (1 - p_L) * adj_G)
            else:
                p_L_given_obs = (p_L * adj_S) / (p_L * adj_S + (1 - p_L) * (1 - adj_G))
                
            # 2. Add probability of transition (learning during/after the step)
            p_L = p_L_given_obs + (1 - p_L_given_obs) * self.p_T
            mastery_history.append(p_L)
            
        # Determine trend
        trend = "stable"
        if len(mastery_history) >= 3:
            recent_delta = mastery_history[-1] - mastery_history[-3]
            if recent_delta > 0.05:
                trend = "improving"
            elif recent_delta < -0.05:
                trend = "declining"
                
        # Confidence increases with more evidence, asymptoting at ~0.95
        evidence_count = len(sorted_interactions)
        confidence = min(0.95, 0.1 + 0.1 * evidence_count)

        return MasteryEstimate(
            skill=skill,
            mastery=round(p_L, 3),
            confidence=round(confidence, 3),
            evidence_count=evidence_count,
            trend=trend
        )

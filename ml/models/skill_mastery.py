"""
Candidate Skill & Mastery Modeling using Item Response Theory (2PL-IRT).
Category: TRAINED BY US.
Dataset Foundation: mgor/EDNet.

Models candidate latent ability (theta) across skills and updates mastery dynamically.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ItemParameters:
    difficulty: float      # b parameter (-3.0 to +3.0)
    discrimination: float  # a parameter (0.5 to 2.5)


class ItemResponseTheoryMasteryModel:
    """
    Two-Parameter Logistic Item Response Theory (2PL-IRT) engine for candidate skill mastery.
    """

    def __init__(self, default_discrimination: float = 1.2):
        self.default_discrimination = default_discrimination
        self.difficulty_priors = {
            "beginner": -1.2,
            "intermediate": 0.0,
            "advanced": +1.4,
        }

    def probability_correct(self, theta: float, difficulty_b: float, discrimination_a: Optional[float] = None) -> float:
        """
        Compute 2PL-IRT probability:
        P(Y = 1 | theta) = 1 / (1 + exp(-a * (theta - b)))
        """
        a = discrimination_a or self.default_discrimination
        z = a * (theta - difficulty_b)
        # Numerical stability clamp
        z = max(-20.0, min(20.0, z))
        return 1.0 / (1.0 + math.exp(-z))

    def update_ability(
        self,
        current_theta: float,
        score: float,  # Candidate score out of 100
        difficulty_level: str,
        learning_rate: float = 0.35
    ) -> Dict[str, Any]:
        """
        Update candidate latent ability theta using Maximum A Posteriori / Stochastic Gradient step.
        """
        b = self.difficulty_priors.get(difficulty_level.lower(), 0.0)
        expected_p = self.probability_correct(current_theta, b)
        observed_p = max(0.0, min(1.0, score / 100.0))

        # Prediction error: (y - p)
        residual = observed_p - expected_p
        new_theta = current_theta + (learning_rate * residual * self.default_discrimination)
        # Bound theta to standard interval [-3.0, +3.0]
        new_theta = max(-3.0, min(3.0, new_theta))

        # Convert theta to normalized 0-100 proficiency scale
        proficiency_100 = round((new_theta + 3.0) / 6.0 * 100.0, 1)

        return {
            "previous_theta": round(current_theta, 3),
            "updated_theta": round(new_theta, 3),
            "estimated_proficiency": proficiency_100,
            "expected_prob": round(expected_p, 3),
            "observed_prob": round(observed_p, 3),
            "residual": round(residual, 3),
            "method": "2pl_irt_update"
        }

    def theta_to_proficiency(self, theta: float) -> float:
        """Map latent ability theta [-3, +3] to [0, 100]."""
        return round(max(0.0, min(100.0, (theta + 3.0) / 6.0 * 100.0)), 1)

    def proficiency_to_theta(self, proficiency_100: float) -> float:
        """Map proficiency [0, 100] to latent ability theta [-3, +3]."""
        clamped = max(0.0, min(100.0, proficiency_100))
        return round((clamped / 100.0 * 6.0) - 3.0, 3)

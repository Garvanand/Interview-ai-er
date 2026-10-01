"""
ML-Assisted Adaptive Question Selector.
Category: TRAINED BY US / HYBRID.
Algorithm: Computerized Adaptive Testing (CAT) via Fisher Information Maximization.

Selects the next optimal question that minimizes uncertainty in candidate latent ability.
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional
from ml.models.skill_mastery import ItemResponseTheoryMasteryModel


class AdaptiveQuestionSelector:
    """Selects next assessment question using Fisher Information optimization and role skill balancing."""

    def __init__(self, irt_model: Optional[ItemResponseTheoryMasteryModel] = None):
        self.irt = irt_model or ItemResponseTheoryMasteryModel()

    def fisher_information(self, theta: float, difficulty_b: float, discrimination_a: float = 1.2) -> float:
        """
        Fisher Information for 2PL-IRT:
        I(theta) = a^2 * P(theta) * (1 - P(theta))
        Maximum information occurs when P(theta) = 0.5 (i.e. theta == b).
        """
        p = self.irt.probability_correct(theta, difficulty_b, discrimination_a)
        return (discrimination_a ** 2) * p * (1.0 - p)

    def select_next_question(
        self,
        candidate_theta: float,
        candidate_questions_pool: List[Dict[str, Any]],
        asked_question_ids: List[str],
        target_skills: List[str],
        skill_coverage_counts: Dict[str, int],
        exploration_prob: float = 0.15
    ) -> Dict[str, Any]:
        """
        Score available questions by Fisher Information + Skill Deficit weighting.
        """
        available = [q for q in candidate_questions_pool if str(q.get("id")) not in asked_question_ids]

        if not available:
            # Fallback if pool exhausted
            return {
                "selected_question": None,
                "strategy": "pool_exhausted",
                "target_difficulty": "intermediate",
            }

        # Exploration epsilon (Thompson / Epsilon-greedy)
        if random.random() < exploration_prob:
            chosen = random.choice(available)
            return {
                "selected_question": chosen,
                "strategy": "epsilon_exploration",
                "fisher_information": round(self.fisher_information(candidate_theta, 0.0), 3),
            }

        best_score = -1e9
        best_question = available[0]
        best_info = 0.0

        for q in available:
            diff_level = q.get("difficulty", "intermediate")
            b = self.irt.difficulty_priors.get(diff_level, 0.0)
            a = float(q.get("discrimination", 1.2))

            info = self.fisher_information(candidate_theta, b, a)

            # Skill deficit bonus: favor skills that have been tested least
            q_skill = q.get("skill_focus") or q.get("domain", "general")
            coverage = skill_coverage_counts.get(q_skill, 0)
            skill_bonus = 1.0 / (1.0 + coverage)

            total_utility = info * 0.7 + skill_bonus * 0.3

            if total_utility > best_score:
                best_score = total_utility
                best_question = q
                best_info = info

        return {
            "selected_question": best_question,
            "strategy": "fisher_information_cat",
            "utility_score": round(best_score, 3),
            "fisher_information": round(best_info, 3),
            "target_theta": round(candidate_theta, 2),
        }

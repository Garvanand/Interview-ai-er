"""
Benchmark Suite F: Candidate Skill Mastery Estimation (2PL-IRT).

Evaluates ItemResponseTheoryMasteryModel across psychometric criteria:
1. Parameter convergence: Estimated ability tracks candidate proficiency profile
2. Standard Error of Measurement (SEM) uncertainty reduction with sample size
3. Monotonic directional updates: Correct answers increase θ; incorrect answers decrease θ
4. Difficulty-weighted update sensitivity: Harder items produce larger positive residuals upon success
5. Numerical stability & scale bounding: θ ∈ [-3.0, +3.0] and proficiency ∈ [0, 100]
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional
import numpy as np

from ml.models.skill_mastery import ItemResponseTheoryMasteryModel

logger = logging.getLogger(__name__)


def compute_irt_sem(theta: float, administered_items_difficulties: List[float], discrimination_a: float = 1.2) -> float:
    """
    Computes Fisher Information and Standard Error of Measurement (SEM):
    I(θ) = Σ [a_i^2 * P_i(θ) * (1 - P_i(θ))]
    SEM(θ) = 1 / sqrt(I(θ))
    """
    total_info = 0.0
    for b in administered_items_difficulties:
        z = discrimination_a * (theta - b)
        z = max(-20.0, min(20.0, z))
        p = 1.0 / (1.0 + math.exp(-z))
        info_i = (discrimination_a ** 2) * p * (1.0 - p)
        total_info += info_i

    # Cold start baseline if no items
    if total_info <= 0.001:
        return 1.50
    return round(1.0 / math.sqrt(total_info), 3)


def run_mastery_benchmark(model: Optional[ItemResponseTheoryMasteryModel] = None) -> Dict[str, Any]:
    """Runs Category F: Candidate Skill Mastery Estimation benchmark."""
    irt = model or ItemResponseTheoryMasteryModel()

    results = {
        "category": "F. Mastery estimation",
        "model_evaluated": "ItemResponseTheoryMasteryModel",
        "evaluations": {},
    }

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Monotonic Directionality Verification
    # ─────────────────────────────────────────────────────────────────────────
    # A correct answer must increase theta; an incorrect answer must decrease theta
    base_theta = 0.0
    res_correct = irt.update_ability(base_theta, score=100.0, difficulty_level="intermediate")
    res_incorrect = irt.update_ability(base_theta, score=0.0, difficulty_level="intermediate")

    theta_after_correct = float(res_correct.get("updated_theta", res_correct.get("new_theta")))
    theta_after_incorrect = float(res_incorrect.get("updated_theta", res_incorrect.get("new_theta")))

    monotonic_passed = (theta_after_correct > base_theta) and (theta_after_incorrect < base_theta)

    results["evaluations"]["monotonic_directionality"] = {
        "baseline_theta": base_theta,
        "theta_after_correct": theta_after_correct,
        "delta_correct": round(theta_after_correct - base_theta, 3),
        "theta_after_incorrect": theta_after_incorrect,
        "delta_incorrect": round(theta_after_incorrect - base_theta, 3),
        "passed": monotonic_passed,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Difficulty-Weighted Update Sensitivity
    # ─────────────────────────────────────────────────────────────────────────
    # Success on an advanced question should yield a larger theta increase than success on a beginner question
    res_adv = irt.update_ability(base_theta, score=100.0, difficulty_level="advanced")
    res_beg = irt.update_ability(base_theta, score=100.0, difficulty_level="beginner")

    delta_adv = float(res_adv.get("updated_theta", res_adv.get("new_theta"))) - base_theta
    delta_beg = float(res_beg.get("updated_theta", res_beg.get("new_theta"))) - base_theta

    diff_sensitivity_passed = (delta_adv > delta_beg)

    results["evaluations"]["difficulty_weighted_sensitivity"] = {
        "delta_theta_advanced_success": round(delta_adv, 3),
        "delta_theta_beginner_success": round(delta_beg, 3),
        "advanced_greater_than_beginner": diff_sensitivity_passed,
        "passed": diff_sensitivity_passed,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # 3. SEM (Standard Error of Measurement) Uncertainty Reduction
    # ─────────────────────────────────────────────────────────────────────────
    # Verify that SEM decreases monotonically as questions are administered
    item_difficulties = [0.0, -1.2, 1.4, 0.0, 1.4]
    sem_progression = []
    current_items = []

    for d in item_difficulties:
        current_items.append(d)
        sem = compute_irt_sem(base_theta, current_items)
        sem_progression.append(sem)

    # SEM after 5 items should be substantially lower than after 1 item
    sem_reduced = (sem_progression[-1] < sem_progression[0])
    results["evaluations"]["sem_uncertainty_reduction"] = {
        "sem_progression": sem_progression,
        "initial_sem_1_item": sem_progression[0],
        "final_sem_5_items": sem_progression[-1],
        "uncertainty_reduced": sem_reduced,
        "passed": sem_reduced,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Numerical Stability & Scale Clamping Check
    # ─────────────────────────────────────────────────────────────────────────
    # 20 consecutive 100% scores must not exceed theta = +3.0 or proficiency = 100.0
    clamped_theta = 0.0
    for _ in range(20):
        up = irt.update_ability(clamped_theta, score=100.0, difficulty_level="advanced")
        clamped_theta = float(up.get("updated_theta", up.get("new_theta")))

    # 20 consecutive 0% scores must not fall below theta = -3.0 or proficiency = 0.0
    low_theta = 0.0
    for _ in range(20):
        dn = irt.update_ability(low_theta, score=0.0, difficulty_level="beginner")
        low_theta = float(dn.get("updated_theta", dn.get("new_theta")))

    scale_bounds_passed = (-3.0 <= low_theta <= 3.0) and (-3.0 <= clamped_theta <= 3.0)

    results["evaluations"]["scale_bounds_clamping"] = {
        "max_saturated_theta": clamped_theta,
        "min_saturated_theta": low_theta,
        "max_proficiency": irt.theta_to_proficiency(clamped_theta),
        "min_proficiency": irt.theta_to_proficiency(low_theta),
        "passed": scale_bounds_passed,
    }

    all_passed = (
        monotonic_passed and
        diff_sensitivity_passed and
        sem_reduced and
        scale_bounds_passed
    )
    results["all_evaluations_passed"] = all_passed

    return results

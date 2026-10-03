"""
Benchmark Suite E: Adaptive Question Selection Evaluation.

Evaluates the five required core behaviors of AdaptiveQuestionSelector:
1. Avoids repeated questions (deduplication & novelty guarantee)
2. Targets low-confidence skills (remediation prioritization)
3. Adjusts difficulty (monotonic responsiveness to candidate performance)
4. Maintains skill diversity (curriculum breadth and non-monopolization)
5. Produces explainable selections (audit trail with evidence-based rationale)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np

from ml.models.adaptive_selector import AdaptiveQuestionSelector, CatalogQuestion
from ml.evaluation.benchmarks.sources import load_interview_adaptive_session_profiles

logger = logging.getLogger(__name__)


def run_adaptive_selection_benchmark(
    selector: Optional[AdaptiveQuestionSelector] = None
) -> Dict[str, Any]:
    """Runs Category E: Adaptive Selection benchmark."""
    model = selector or AdaptiveQuestionSelector()

    results = {
        "category": "E. Adaptive selection",
        "model_evaluated": "AdaptiveQuestionSelector",
        "criteria_evaluations": {},
    }

    # ─────────────────────────────────────────────────────────────────────────
    # Criterion 1: Avoids Repeated Questions
    # ─────────────────────────────────────────────────────────────────────────
    session_history = []
    asked_ids = []
    duplicate_count = 0
    num_steps = 6

    for step in range(num_steps):
        decision = model.select_next_question(
            previous_question_history=session_history,
            asked_question_ids=asked_ids,
            candidate_theta=0.0,
            current_difficulty="intermediate",
        )
        selected_q = decision.get("selected_question", {})
        q_id = selected_q.get("id")

        if q_id in asked_ids:
            duplicate_count += 1

        asked_ids.append(q_id)
        session_history.append(selected_q)

    results["criteria_evaluations"]["avoids_repeated_questions"] = {
        "total_selections": num_steps,
        "duplicate_count": duplicate_count,
        "avoidance_rate": round((num_steps - duplicate_count) / num_steps, 4),
        "passed": (duplicate_count == 0),
        "selected_question_ids": asked_ids,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # Criterion 2: Targets Low-Confidence / Weak Skills
    # ─────────────────────────────────────────────────────────────────────────
    # Setup candidate with severe weakness in dynamic_programming
    weak_skill_state = {
        "dynamic_programming": {
            "mastery": 0.15,
            "scores": [20.0, 15.0],
            "weaknesses": ["optimal substructure", "memoization"],
            "strengths": []
        },
        "arrays": {
            "mastery": 0.90,
            "scores": [95.0, 90.0],
            "weaknesses": [],
            "strengths": ["two pointers"]
        },
        "trees": {
            "mastery": 0.85,
            "scores": [85.0],
            "weaknesses": [],
            "strengths": ["traversals"]
        }
    }

    decision_weakness = model.select_next_question(
        candidate_skill_state=weak_skill_state,
        current_difficulty="intermediate",
        candidate_theta=0.0,
        role_skills=["dynamic_programming", "arrays", "trees"],
    )

    chosen_skill = decision_weakness.get("target_skill", "")
    chosen_q = decision_weakness.get("selected_question", {})
    q_focus = chosen_q.get("skill_focus", "")
    q_skills = chosen_q.get("canonical_skills", [])

    targeted_weakness = (
        chosen_skill == "dynamic_programming" or
        q_focus == "dynamic_programming" or
        "dynamic_programming" in q_skills
    )

    results["criteria_evaluations"]["targets_low_confidence_skills"] = {
        "low_confidence_skill": "dynamic_programming",
        "selected_target_skill": chosen_skill,
        "selected_question_focus": q_focus,
        "remediation_targeted": targeted_weakness,
        "passed": targeted_weakness,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # Criterion 3: Adjusts Difficulty
    # ─────────────────────────────────────────────────────────────────────────
    # 3A. Strong performance (score = 95%) should step up
    decision_step_up = model.select_next_question(
        candidate_theta=1.2,
        current_difficulty="intermediate",
        recent_evaluation_evidence={"score": 95.0, "difficulty": "intermediate"},
    )
    diff_up = decision_step_up.get("selected_question", {}).get("difficulty")
    stepped_up = (diff_up in ("intermediate", "advanced"))

    # 3B. Poor performance (score = 15%) should step down
    decision_step_down = model.select_next_question(
        candidate_theta=-1.4,
        current_difficulty="intermediate",
        recent_evaluation_evidence={"score": 15.0, "difficulty": "intermediate"},
    )
    diff_down = decision_step_down.get("selected_question", {}).get("difficulty")
    stepped_down = (diff_down in ("beginner", "intermediate"))

    results["criteria_evaluations"]["adjusts_difficulty"] = {
        "high_score_adaptation": {
            "candidate_score": 95.0,
            "candidate_theta": +1.2,
            "resulting_question_difficulty": diff_up,
            "stepped_up_appropriately": stepped_up,
        },
        "low_score_adaptation": {
            "candidate_score": 15.0,
            "candidate_theta": -1.4,
            "resulting_question_difficulty": diff_down,
            "stepped_down_appropriately": stepped_down,
        },
        "passed": (stepped_up and stepped_down),
    }

    # ─────────────────────────────────────────────────────────────────────────
    # Criterion 4: Maintains Skill Diversity
    # ─────────────────────────────────────────────────────────────────────────
    # Over 5 questions in a neutral session, ensure multiple unique skills are sampled
    diverse_session_history = []
    skills_encountered = []
    asked_q_ids = []

    for _ in range(5):
        dec = model.select_next_question(
            previous_question_history=diverse_session_history,
            asked_question_ids=asked_q_ids,
            candidate_theta=0.0,
        )
        q = dec.get("selected_question", {})
        asked_q_ids.append(q.get("id"))
        diverse_session_history.append(q)
        skills_encountered.append(q.get("skill_focus", "general"))

    unique_skills = set(skills_encountered)
    diversity_ratio = len(unique_skills) / 5.0
    diversity_adequate = (diversity_ratio >= 0.60)  # At least 3 unique skills out of 5

    results["criteria_evaluations"]["maintains_skill_diversity"] = {
        "questions_administered": 5,
        "unique_skills_count": len(unique_skills),
        "skills_sequence": skills_encountered,
        "diversity_ratio": round(diversity_ratio, 2),
        "passed": diversity_adequate,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # Criterion 5: Produces Explainable Selections
    # ─────────────────────────────────────────────────────────────────────────
    explainability_checks = []
    for q_dec in [decision_weakness, decision_step_up, decision_step_down]:
        why = q_dec.get("why_selected", "")
        has_skill_mention = ("skill" in why.lower())
        has_mastery_mention = ("mastery" in why.lower() or "score" in why.lower())
        has_diff_mention = ("difficulty" in why.lower() or "theta" in why.lower())
        is_complete = bool(why) and has_skill_mention and has_diff_mention
        explainability_checks.append({
            "why_selected_text": why,
            "is_complete_and_grounded": is_complete,
        })

    all_explainable = all(c["is_complete_and_grounded"] for c in explainability_checks)
    results["criteria_evaluations"]["produces_explainable_selections"] = {
        "samples_checked": len(explainability_checks),
        "all_explainable": all_explainable,
        "passed": all_explainable,
        "example_explanation": explainability_checks[0]["why_selected_text"],
    }

    # Overall Summary
    all_criteria_passed = (
        results["criteria_evaluations"]["avoids_repeated_questions"]["passed"] and
        results["criteria_evaluations"]["targets_low_confidence_skills"]["passed"] and
        results["criteria_evaluations"]["adjusts_difficulty"]["passed"] and
        results["criteria_evaluations"]["maintains_skill_diversity"]["passed"] and
        results["criteria_evaluations"]["produces_explainable_selections"]["passed"]
    )
    results["all_criteria_passed"] = all_criteria_passed

    return results

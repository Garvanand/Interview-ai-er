"""
Interview ML Pipeline.
Orchestrates end-to-end multi-model ML evaluation and adaptive routing
for a live or practice interview turn.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ml.inference.engine import MLInferenceEngine

logger = logging.getLogger(__name__)


class InterviewMLPipeline:
    """
    Coordinates machine-learning evaluations alongside the deterministic orchestrator.
    Does NOT replace deterministic business logic or state transitions;
    provides calibrated quantitative signals to augment LLM feedback.
    """

    def __init__(self, engine: Optional[MLInferenceEngine] = None):
        self.engine = engine or MLInferenceEngine()

    def process_incoming_question(self, question_text: str) -> Dict[str, Any]:
        """Classify skills and verify difficulty for newly generated question."""
        diff_res = self.engine.predict_question_difficulty(question_text)
        skill_res = self.engine.classify_question_skills(question_text)
        return {
            "predicted_difficulty": diff_res["difficulty"],
            "difficulty_probabilities": diff_res["probabilities"],
            "detected_skills": skill_res["top_skills"],
            "skill_confidences": skill_res["confidence_scores"],
            "telemetry": {
                "difficulty_latency_ms": diff_res.get("latency_ms", 0),
                "skill_latency_ms": skill_res.get("latency_ms", 0),
            }
        }

    def evaluate_candidate_submission(
        self,
        question_text: str,
        response_text: str,
        expected_concepts: Optional[List[str]] = None,
        reference_answer: Optional[str] = None,
        is_code: bool = False,
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        Run multi-model evaluation over candidate submission.
        """
        results: Dict[str, Any] = {}

        # 1. Concept Coverage (DeBERTa NLI)
        if expected_concepts:
            results["concept_coverage"] = self.engine.evaluate_concept_coverage(
                response_text, expected_concepts
            )

        # 2. Semantic Similarity against reference (MiniLM)
        if reference_answer:
            results["reference_similarity"] = self.engine.compute_semantic_similarity(
                response_text, reference_answer
            )

        # 3. Code Defect Detection (CodeBERT)
        if is_code:
            results["defect_analysis"] = self.engine.detect_code_defects(
                response_text, language=language
            )

        return results

    def advance_adaptive_session(
        self,
        current_theta: float,
        last_score: float,
        last_difficulty: str,
        question_pool: List[Dict[str, Any]],
        asked_ids: List[str],
        target_skills: List[str],
        skill_coverage: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Update candidate latent ability using 2PL-IRT and select the next question
        using Fisher Information CAT.
        """
        mastery_update = self.engine.update_candidate_mastery(
            current_theta=current_theta,
            score=last_score,
            difficulty=last_difficulty
        )

        next_q = self.engine.select_adaptive_question(
            candidate_theta=mastery_update["updated_theta"],
            question_pool=question_pool,
            asked_ids=asked_ids,
            target_skills=target_skills,
            skill_coverage=skill_coverage
        )

        return {
            "mastery": mastery_update,
            "next_question_decision": next_q
        }

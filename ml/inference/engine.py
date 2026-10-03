"""
Unified ML Inference Engine.
Coordinates low-latency local execution across all 8 ML capabilities
with strict fallback boundaries, telemetry, and zero network dependence.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from ml.features.text_embeddings import TextEmbeddingExtractor, compute_cosine_similarity
from ml.models.difficulty_predictor import QuestionDifficultyPredictor
from ml.models.skill_classifier import QuestionSkillClassifier
from ml.models.concept_coverage import ConceptCoverageAnalyzer
from ml.models.defect_detector import CodeDefectDetector
from ml.models.speech_to_text import VoiceTranscriber
from ml.models.skill_mastery import ItemResponseTheoryMasteryModel
from ml.models.adaptive_selector import AdaptiveQuestionSelector

logger = logging.getLogger(__name__)


class MLInferenceEngine:
    """Unified coordinator for local ML evaluations and adaptive selection."""

    def __init__(self, device: str = "cpu"):
        self.device = device
        self.embedding_extractor = TextEmbeddingExtractor(device=device)
        self.difficulty_predictor = QuestionDifficultyPredictor()
        self.skill_classifier = QuestionSkillClassifier()
        self.concept_analyzer = ConceptCoverageAnalyzer(device=device)
        self.defect_detector = CodeDefectDetector(device=device)
        self.transcriber = VoiceTranscriber(device=device)
        self.mastery_model = ItemResponseTheoryMasteryModel()
        self.adaptive_selector = AdaptiveQuestionSelector(self.mastery_model)

    def predict_question_difficulty(self, question_text: str) -> Dict[str, Any]:
        """Capability 1: Predict question difficulty level."""
        t0 = time.time()
        res = self.difficulty_predictor.predict(question_text)
        res["latency_ms"] = round((time.time() - t0) * 1000.0, 2)
        return res

    def classify_question_skills(self, question_text: str, top_k: int = 3) -> Dict[str, Any]:
        """Capability 2: Classify question technical topics."""
        t0 = time.time()
        res = self.skill_classifier.predict(question_text, top_k=top_k)
        res["latency_ms"] = round((time.time() - t0) * 1000.0, 2)
        return res

    def evaluate_concept_coverage(self, candidate_answer: str, expected_concepts: List[str]) -> Dict[str, Any]:
        """Capability 3: Evaluate concept coverage using DeBERTa NLI + MiniLM hybrid pipeline."""
        t0 = time.time()
        res = self.concept_analyzer.evaluate_concepts(candidate_answer, expected_concepts)
        res["latency_ms"] = round((time.time() - t0) * 1000.0, 2)
        res["concept_scores"] = {
            r["concept"]: r["concept_score"]
            for r in res.get("concept_results", [])
        }
        return res

    def hybrid_answer_analysis(
        self,
        candidate_answer: str,
        question_text: str,
        evaluation_rubric: str,
        expected_concepts: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Capability 3+: Full hybrid ML evidence generation for answer analysis.

        Combines DeBERTa NLI concept checks + MiniLM semantic similarity into
        structured evidence ready for Gemini evaluation prompt injection.
        """
        from ml.pipelines.hybrid_assessment import HybridAssessmentPipeline
        t0 = time.time()
        pipeline = HybridAssessmentPipeline(device=self.device)
        evidence = pipeline.generate_ml_evidence(
            candidate_answer=candidate_answer,
            question_text=question_text,
            evaluation_rubric=evaluation_rubric,
            expected_concepts=expected_concepts,
        )
        evidence["latency_ms"] = round((time.time() - t0) * 1000.0, 2)
        return evidence

    def compute_semantic_similarity(self, text_a: str, text_b: str) -> Dict[str, Any]:
        """Capability 4: Compute cosine similarity using MiniLM embeddings."""
        t0 = time.time()
        vec_a = self.embedding_extractor.encode(text_a)
        vec_b = self.embedding_extractor.encode(text_b)
        sim = compute_cosine_similarity(vec_a, vec_b)
        return {
            "similarity_score": round(sim, 3),
            "is_semantically_aligned": sim >= 0.70,
            "latency_ms": round((time.time() - t0) * 1000.0, 2),
            "method": "all_minilm_l6_v2_cosine"
        }

    def detect_code_defects(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Capability 5: Code defect and vulnerability detection via CodeBERT."""
        t0 = time.time()
        res = self.defect_detector.analyze_code(code, language=language)
        res["latency_ms"] = round((time.time() - t0) * 1000.0, 2)
        res["defect_risk_score"] = res.get("defect_probability", 0.0)
        return res

    def transcribe_audio(self, audio_data: Any) -> Dict[str, Any]:
        """Capability 6: Speech-to-Text transcription via Whisper."""
        t0 = time.time()
        res = self.transcriber.transcribe(audio_data)
        res["latency_ms"] = round((time.time() - t0) * 1000.0, 2)
        return res

    def update_candidate_mastery(
        self,
        current_theta: float,
        score: float,
        difficulty: str
    ) -> Dict[str, Any]:
        """Capability 7: Update candidate latent mastery via 2PL-IRT."""
        t0 = time.time()
        res = self.mastery_model.update_ability(current_theta, score, difficulty)
        res["latency_ms"] = round((time.time() - t0) * 1000.0, 2)
        return res

    def select_adaptive_question(
        self,
        candidate_theta: float,
        question_pool: List[Dict[str, Any]],
        asked_ids: List[str],
        target_skills: List[str],
        skill_coverage: Dict[str, int]
    ) -> Dict[str, Any]:
        """Capability 8: Fisher Information CAT question selection."""
        t0 = time.time()
        res = self.adaptive_selector.select_next_question(
            candidate_theta,
            question_pool,
            asked_ids,
            target_skills,
            skill_coverage
        )
        res["latency_ms"] = round((time.time() - t0) * 1000.0, 2)
        return res

"""
Service layer for ML-derived question skill classification and metadata persistence.
Keeps source question metadata and ML predictions strictly separated.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from ml.models.skill_classifier import QuestionSkillClassifier
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


class QuestionSkillService:
    """
    Coordinates question skill classification and separate persistence of
    ML-derived skill metadata for technical/interview questions.
    """

    def __init__(self, supabase_service: Optional[SupabaseService] = None):
        self.supabase = supabase_service or SupabaseService()
        try:
            self.classifier = QuestionSkillClassifier()
            self._enabled = True
        except Exception as e:
            logger.error("Failed to initialize QuestionSkillClassifier: %s", e)
            self._enabled = False

    def is_enabled(self) -> bool:
        return self._enabled

    def classify_skills(self, question_text: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Classifies skills using the trained TACO multi-label classifier.
        Returns:
        {
            "skills": [
                {
                    "skill": "dynamic_programming",
                    "confidence": 0.91
                }
            ]
        }
        """
        if not self._enabled:
            return {
                "skills": [{"skill": "algorithms", "confidence": 0.50}],
                "model_version": "fallback",
                "method": "service_disabled"
            }

        try:
            return self.classifier.predict(question_text, top_k=top_k)
        except Exception as e:
            logger.error("Error in skill classification: %s", e)
            return {
                "skills": [{"skill": "algorithms", "confidence": 0.50}],
                "model_version": "error_fallback",
                "method": "error_fallback"
            }

    def predict_and_persist(
        self,
        question_id: str,
        question_text: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Derives ML skill predictions for a generated question and persists them
        separately from the original question record.
        
        Persisted fields:
        - question_id
        - predicted_skills
        - confidence
        - model_version
        - timestamp
        """
        classification = self.classify_skills(question_text, top_k=top_k)
        predicted_skills = classification.get("skills", [])
        
        # Primary confidence is top prediction confidence
        top_confidence = predicted_skills[0]["confidence"] if predicted_skills else 0.0
        model_name = classification.get("model_name", "question-skill-v1")
        model_version = classification.get("model_version", "1.1.0")
        dataset_version = classification.get("dataset_version", "2026.10")
        training_run = classification.get("training_run", "question-skill-tagger-v1_20261003T063901Z")
        inference_timestamp = classification.get("inference_timestamp", datetime.now(timezone.utc).isoformat())
        current_time = datetime.now(timezone.utc).isoformat()

        # Persist ML metadata without modifying original question record
        persisted_record = self.supabase.store_question_skill_prediction(
            question_id=question_id,
            predicted_skills=predicted_skills,
            confidence=top_confidence,
            model_version=model_version,
            timestamp=current_time,
            model_name=model_name,
            dataset_version=dataset_version,
            training_run=training_run,
            inference_timestamp=inference_timestamp,
        )

        return {
            "question_id": question_id,
            "predicted_skills": predicted_skills,
            "confidence": top_confidence,
            "model_name": model_name,
            "model_version": model_version,
            "dataset_version": dataset_version,
            "training_run": training_run,
            "inference_timestamp": inference_timestamp,
            "timestamp": current_time,
            "skills": predicted_skills,
            "method": classification.get("method", "trained_multilabel_classifier")
        }

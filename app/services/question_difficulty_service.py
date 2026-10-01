from __future__ import annotations
import logging
from typing import Dict, Any, Optional

from ml.inference.engine import MLInferenceEngine

logger = logging.getLogger(__name__)


class QuestionDifficultyService:
    """
    Service layer for question difficulty prediction.
    Overrides LLM-based difficulty assessment with deterministic ML prediction
    when the ML pipeline is enabled.
    """

    def __init__(self):
        # We initialize the unified ML engine (which lazy loads models as needed)
        # Note: If it fails to load, it falls back to heuristics automatically.
        try:
            self.ml_engine = MLInferenceEngine()
            self._enabled = True
        except Exception as e:
            logger.error(f"Failed to initialize MLInferenceEngine: {e}")
            self._enabled = False

    def is_enabled(self) -> bool:
        return self._enabled

    def assess_difficulty(self, question_text: str) -> Dict[str, Any]:
        """
        Predicts the difficulty of the provided question text using the ML model.
        Returns a dictionary matching the schema:
        {
            "predicted_difficulty": "...",
            "confidence": 0.0,
            "model_version": "...",
            "inference_time_ms": 0,
            "method": "..."
        }
        """
        if not self._enabled:
            return {
                "predicted_difficulty": "intermediate",
                "confidence": 0.0,
                "model_version": "fallback",
                "inference_time_ms": 0,
                "method": "service_disabled_fallback"
            }
        
        try:
            return self.ml_engine.predict_question_difficulty(question_text)
        except Exception as e:
            logger.error(f"Error predicting difficulty: {e}")
            return {
                "predicted_difficulty": "intermediate",
                "confidence": 0.0,
                "model_version": "error_fallback",
                "inference_time_ms": 0,
                "method": "error_fallback"
            }


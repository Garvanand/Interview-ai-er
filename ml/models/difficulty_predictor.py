"""
Question Difficulty Prediction Model.
Category: TRAINED BY US
Datasets: BAAI/TACO
"""
from __future__ import annotations

import os
import time
import logging
import re
from typing import Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

DIFFICULTY_CLASSES = ["beginner", "intermediate", "advanced"]


class QuestionDifficultyPredictor:
    """Predicts technical interview question difficulty using classical or transformer models."""

    def __init__(self, weights_path: Optional[str] = None):
        self.weights_path = weights_path
        self._classifier = None
        self._vectorizer = None
        self._transformer_model = None
        self._transformer_tokenizer = None
        self.model_version = "1.0.0"
        self._load_weights()

    def _load_weights(self):
        if not self.weights_path or not os.path.exists(self.weights_path):
            logger.warning("Weights path %s not found. Using heuristic fallback.", self.weights_path)
            return
            
        try:
            if os.path.isdir(self.weights_path):
                # Transformer directory
                from transformers import AutoTokenizer, AutoModelForSequenceClassification
                import torch
                self._transformer_tokenizer = AutoTokenizer.from_pretrained(self.weights_path)
                self._transformer_model = AutoModelForSequenceClassification.from_pretrained(self.weights_path)
                self._transformer_model.eval()
                self.model_version = "transformer_v1"
                logger.info("Loaded transformer difficulty classifier from %s", self.weights_path)
            elif self.weights_path.endswith('.joblib'):
                # Classical joblib
                import joblib
                data = joblib.load(self.weights_path)
                if isinstance(data, dict) and "classifier" in data and "vectorizer" in data:
                    self._classifier = data["classifier"]
                    self._vectorizer = data["vectorizer"]
                else:
                    self._classifier = data
                    # Fallback for old pipeline which used TextEmbeddingExtractor
                    from ml.features.text_embeddings import TextEmbeddingExtractor
                    self._vectorizer = TextEmbeddingExtractor()
                self.model_version = "classical_v1"
                logger.info("Loaded classical difficulty classifier from %s", self.weights_path)
        except Exception as e:
            logger.warning("Could not load weights from %s: %s. Using heuristic fallback.", self.weights_path, e)
            self._classifier = None
            self._transformer_model = None

    def predict(self, question_text: str) -> Dict[str, Any]:
        """Predict difficulty level and confidence distribution."""
        start_time = time.time()
        
        if self._transformer_model is not None:
            import torch
            inputs = self._transformer_tokenizer(question_text, return_tensors="pt", truncation=True, max_length=128)
            with torch.no_grad():
                outputs = self._transformer_model(**inputs)
            
            logits = outputs.logits[0]
            probs = torch.nn.functional.softmax(logits, dim=0).cpu().numpy()
            pred_idx = logits.argmax().item()
            
            # Assuming labels are sorted alphabetically or mapped correctly in the model
            # For robustness, we check id2label
            id2label = self._transformer_model.config.id2label
            pred_class = id2label.get(pred_idx, DIFFICULTY_CLASSES[pred_idx])
            
            prob_dict = {}
            for i, p in enumerate(probs):
                cls_name = id2label.get(i, DIFFICULTY_CLASSES[i])
                prob_dict[cls_name] = float(p)
                
            inference_time = int((time.time() - start_time) * 1000)
            
            return {
                "difficulty": pred_class,
                "predicted_difficulty": pred_class,
                "confidence": float(probs[pred_idx]),
                "probabilities": prob_dict,
                "model_version": self.model_version,
                "inference_time_ms": inference_time,
                "method": "transformer_classifier"
            }
            
        elif self._classifier is not None:
            if hasattr(self._vectorizer, "transform"):
                # TF-IDF
                X = self._vectorizer.transform([question_text])
            else:
                # TextEmbeddingExtractor
                X = self._vectorizer.encode(question_text).reshape(1, -1)
                
            pred_class = self._classifier.predict(X)[0]
            if hasattr(self._classifier, "predict_proba"):
                probs = self._classifier.predict_proba(X)[0]
            else:
                probs = [0.33, 0.33, 0.34]
                
            prob_dict = {cls: float(p) for cls, p in zip(self._classifier.classes_, probs)}
            confidence = prob_dict.get(pred_class, 0.0)
            
            inference_time = int((time.time() - start_time) * 1000)
            return {
                "difficulty": pred_class,
                "predicted_difficulty": pred_class,
                "confidence": confidence,
                "probabilities": prob_dict,
                "model_version": self.model_version,
                "inference_time_ms": inference_time,
                "method": "classical_classifier"
            }

        # DETERMINISTIC HEURISTIC FALLBACK
        text = question_text.lower()
        word_count = len(text.split())

        has_advanced_keywords = bool(re.search(
            r"\b(dynamic programming|segment tree|trie|np-hard|shortest path|concurrency|distributed|paxos|raft|b-tree|lock-free|sharding|memory leak|advanced|hard|complex)\b",
            text
        ))
        has_intermediate_keywords = bool(re.search(
            r"\b(binary search|recursion|tree|graph|hash table|stack|queue|sort|sql|join|index|decorator|memoization|generator|intermediate|medium)\b",
            text
        ))
        has_beginner_keywords = bool(re.search(
            r"\b(beginner|easy|basic|simple|introductory|fundamentals)\b",
            text
        ))

        if has_advanced_keywords or word_count > 150:
            diff = "advanced"
            probs = {"beginner": 0.1, "intermediate": 0.2, "advanced": 0.7}
        elif has_intermediate_keywords or word_count > 60:
            diff = "intermediate"
            probs = {"beginner": 0.2, "intermediate": 0.6, "advanced": 0.2}
        elif has_beginner_keywords or word_count <= 60:
            diff = "beginner"
            probs = {"beginner": 0.7, "intermediate": 0.2, "advanced": 0.1}
        else:
            diff = "intermediate"
            probs = {"beginner": 0.2, "intermediate": 0.6, "advanced": 0.2}

        inference_time = int((time.time() - start_time) * 1000)
        return {
            "difficulty": diff,
            "predicted_difficulty": diff,
            "confidence": probs[diff],
            "probabilities": probs,
            "model_version": "heuristic_fallback_v1",
            "inference_time_ms": inference_time,
            "method": "deterministic_heuristic_fallback",
        }

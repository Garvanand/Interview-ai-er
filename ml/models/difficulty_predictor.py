"""
Question Difficulty Prediction Model with 3-Tier Robust Fallback Architecture.

Classes of Intelligence:
1. PRIMARY ML ("ml"): Trained/fine-tuned classifier.
2. SECONDARY MODEL ("pretrained" or "deterministic"): Pretrained transformer embedding similarity or text heuristic.
3. LLM FALLBACK ("llm"): Structured Gemini reasoning.
4. UNAVAILABLE ("unavailable"): If inputs are malformed or all tiers fail.

Confidence is strictly tied to the actual method; never manufactured.
"""
from __future__ import annotations

import os
import time
import logging
import re
from typing import Dict, Any, Optional, List
import numpy as np

from ml.fallbacks import IntelligenceSource, log_fallback_event, try_llm_difficulty_fallback
from ml.versioning import stamp_inference
from ml.calibration import get_confidence_metadata

logger = logging.getLogger(__name__)

DIFFICULTY_CLASSES = ["beginner", "intermediate", "advanced"]

# Difficulty anchor prototypes for pretrained embedding zero-shot classification
DIFFICULTY_ANCHORS = {
    "beginner": "Basic beginner programming fundamentals simple syntax basic variables loops conditions",
    "intermediate": "Intermediate data structures algorithms recursion binary search trees graphs hash tables",
    "advanced": "Advanced complex dynamic programming distributed systems concurrency NP-hard optimization trie segment tree",
}


class QuestionDifficultyPredictor:
    """Predicts technical interview question difficulty using 3-tier fallback architecture."""

    def __init__(self, weights_path: Optional[str] = None):
        self.weights_path = weights_path
        self._classifier = None
        self._vectorizer = None
        self._transformer_model = None
        self._transformer_tokenizer = None
        self.model_version = "1.0.0"
        self._primary_load_error: Optional[str] = None
        self._load_weights()

    def _load_weights(self):
        """Loads primary ML weights with corruption protection."""
        if not self.weights_path or not os.path.exists(self.weights_path):
            self._primary_load_error = f"Weights path '{self.weights_path}' not found"
            logger.info("%s. Primary ML unavailable; will use fallbacks.", self._primary_load_error)
            return

        try:
            if os.path.isdir(self.weights_path):
                from transformers import AutoTokenizer, AutoModelForSequenceClassification
                self._transformer_tokenizer = AutoTokenizer.from_pretrained(self.weights_path)
                self._transformer_model = AutoModelForSequenceClassification.from_pretrained(self.weights_path)
                self._transformer_model.eval()
                self.model_version = "transformer_v1"
                logger.info("Loaded transformer difficulty classifier from %s", self.weights_path)
            elif self.weights_path.endswith('.joblib'):
                import joblib
                data = joblib.load(self.weights_path)
                if isinstance(data, dict) and "classifier" in data and "vectorizer" in data:
                    self._classifier = data["classifier"]
                    self._vectorizer = data["vectorizer"]
                else:
                    self._classifier = data
                    from ml.features.text_embeddings import TextEmbeddingExtractor
                    self._vectorizer = TextEmbeddingExtractor()
                self.model_version = "classical_v1"
                logger.info("Loaded classical difficulty classifier from %s", self.weights_path)
        except Exception as e:
            self._primary_load_error = f"Corrupted artifact or load failure: {e}"
            logger.warning("Failed to load weights from %s: %s. Primary ML will be marked unavailable.", self.weights_path, e)
            self._classifier = None
            self._transformer_model = None

    def predict(
        self,
        question_text: str,
        allow_llm: bool = True,
        timeout_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Predict difficulty with full 3-tier fallback chain:
        Primary ML -> Secondary Pretrained / Text Heuristic -> LLM Suggestion -> Unavailable
        """
        start_time = time.time()

        # Step 0: Input validation (Malformed input check)
        if not isinstance(question_text, str) or not question_text.strip():
            logger.warning("Malformed input received in QuestionDifficultyPredictor: %r", question_text)
            _conf_meta = get_confidence_metadata("question-difficulty-v1", 0.0, source_tier="unavailable")
            malformed_res = {
                "difficulty": "intermediate",
                "predicted_difficulty": "intermediate",
                "confidence": 0.0,
                "probabilities": {"beginner": 0.0, "intermediate": 0.0, "advanced": 0.0},
                "source": IntelligenceSource.UNAVAILABLE.value,
                "method": "malformed_input_handler",
                "model_version": "unavailable",
                "inference_time_ms": int((time.time() - start_time) * 1000),
                "error": "Malformed input: question_text must be a non-empty string",
                "confidence_metadata": _conf_meta.to_dict(),
                "confidence_band": _conf_meta.confidence_band.value,
            }
            return stamp_inference("question-difficulty-v1", malformed_res, version_override="unavailable")

        # ── Tier 1: PRIMARY ML ──────────────────────────────────────────
        primary_result = self._try_primary_ml(question_text, timeout_seconds)
        if primary_result is not None:
            primary_result["inference_time_ms"] = int((time.time() - start_time) * 1000)
            return stamp_inference("question-difficulty-v1", primary_result)

        # ── Tier 2: SECONDARY MODEL (Pretrained or Text Heuristic) ──────
        secondary_result = self._try_secondary_model(question_text)
        if secondary_result is not None:
            log_fallback_event(
                component="question_difficulty",
                from_source=IntelligenceSource.ML.value,
                to_source=secondary_result["source"],
                reason=self._primary_load_error or "Primary ML unavailable or failed",
            )
            secondary_result["inference_time_ms"] = int((time.time() - start_time) * 1000)
            return stamp_inference("question-difficulty-v1", secondary_result)

        # ── Tier 3: LLM FALLBACK (Structured Gemini Reasoning) ─────────
        if allow_llm:
            llm_result = try_llm_difficulty_fallback(question_text)
            if llm_result is not None:
                log_fallback_event(
                    component="question_difficulty",
                    from_source=IntelligenceSource.PRETRAINED.value,
                    to_source=IntelligenceSource.LLM.value,
                    reason="Pretrained model unavailable; falling back to LLM",
                )
                llm_result["inference_time_ms"] = int((time.time() - start_time) * 1000)
                return stamp_inference("question-difficulty-v1", llm_result)

        # ── Deterministic Heuristic Fallback (Safety Net) ───────────────
        heuristic_res = self._deterministic_heuristic_fallback(question_text)
        heuristic_res["inference_time_ms"] = int((time.time() - start_time) * 1000)
        return stamp_inference("question-difficulty-v1", heuristic_res)

    def _try_primary_ml(self, question_text: str, timeout_seconds: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Executes Primary ML model if available."""
        if self._transformer_model is not None:
            try:
                import torch
                inputs = self._transformer_tokenizer(
                    question_text, return_tensors="pt", truncation=True, max_length=128
                )
                with torch.no_grad():
                    outputs = self._transformer_model(**inputs)

                logits = outputs.logits[0]
                probs = torch.nn.functional.softmax(logits, dim=0).cpu().numpy()
                pred_idx = logits.argmax().item()

                id2label = getattr(self._transformer_model.config, "id2label", {})
                pred_class = id2label.get(pred_idx, DIFFICULTY_CLASSES[pred_idx])

                prob_dict = {
                    id2label.get(i, DIFFICULTY_CLASSES[i]): float(p)
                    for i, p in enumerate(probs)
                }

                _raw_conf = float(probs[pred_idx])
                _conf_meta = get_confidence_metadata("question-difficulty-v1", _raw_conf, source_tier="ml")
                return {
                    "difficulty": pred_class,
                    "predicted_difficulty": pred_class,
                    "confidence": _raw_conf,
                    "probabilities": prob_dict,
                    "model_version": self.model_version,
                    "source": IntelligenceSource.ML.value,
                    "method": "trained_transformer_classifier",
                    "confidence_metadata": _conf_meta.to_dict(),
                    "confidence_band": _conf_meta.confidence_band.value,
                }
            except Exception as e:
                logger.warning("Primary transformer inference failed: %s", e)
                return None

        elif self._classifier is not None:
            try:
                if hasattr(self._vectorizer, "transform"):
                    X = self._vectorizer.transform([question_text])
                else:
                    X = self._vectorizer.encode(question_text).reshape(1, -1)

                pred_class = self._classifier.predict(X)[0]
                if hasattr(self._classifier, "predict_proba"):
                    probs = self._classifier.predict_proba(X)[0]
                else:
                    probs = [0.33, 0.33, 0.34]

                prob_dict = {cls: float(p) for cls, p in zip(self._classifier.classes_, probs)}
                confidence = prob_dict.get(pred_class, 0.0)

                _conf_meta = get_confidence_metadata("question-difficulty-v1", float(confidence), source_tier="ml")
                return {
                    "difficulty": pred_class,
                    "predicted_difficulty": pred_class,
                    "confidence": float(confidence),
                    "probabilities": prob_dict,
                    "model_version": self.model_version,
                    "source": IntelligenceSource.ML.value,
                    "method": "trained_classical_classifier",
                    "confidence_metadata": _conf_meta.to_dict(),
                    "confidence_band": _conf_meta.confidence_band.value,
                }
            except Exception as e:
                logger.warning("Primary classical inference failed: %s", e)
                return None

        return None

    def _try_secondary_model(self, question_text: str) -> Optional[Dict[str, Any]]:
        """
        Tier 2 Secondary Model:
        Uses pretrained sentence embeddings to compute cosine similarity against difficulty anchor descriptions.
        """
        try:
            from ml.serving.inference_service import InferenceService
            anchors_list = [DIFFICULTY_ANCHORS["beginner"], DIFFICULTY_ANCHORS["intermediate"], DIFFICULTY_ANCHORS["advanced"]]
            all_texts = [question_text] + anchors_list

            def _encode(model):
                return model.encode(all_texts, normalize_embeddings=True, show_progress_bar=False)

            resp = InferenceService.execute("semantic-answer-similarity-v1", _encode)
            embeddings = resp["result"]
            q_emb = embeddings[0]

            sims = [float(np.dot(q_emb, embeddings[i])) for i in range(1, 4)]
            temp = 0.2
            exp_sims = np.exp(np.array(sims) / temp)
            emb_probs = exp_sims / np.sum(exp_sims)

            # Blend with text heuristic keyword prior for robust hybrid secondary intelligence
            text = question_text.lower()
            has_advanced = bool(re.search(
                r"\b(dynamic programming|segment tree|trie|np-hard|shortest path|concurrency|distributed|paxos|raft|b-tree|lock-free|sharding|memory leak|advanced|hard|complex)\b",
                text
            ))
            has_intermediate = bool(re.search(
                r"\b(binary search|recursion|tree|graph|hash table|stack|queue|sort|sql|join|index|decorator|memoization|generator|intermediate|medium)\b",
                text
            ))
            has_beginner = bool(re.search(
                r"\b(beginner|easy|basic|simple|introductory|fundamentals)\b",
                text
            ))

            prior = np.array([0.33, 0.34, 0.33])
            if has_advanced:
                prior = np.array([0.05, 0.20, 0.75])
            elif has_intermediate:
                prior = np.array([0.15, 0.70, 0.15])
            elif has_beginner:
                prior = np.array([0.75, 0.20, 0.05])

            probs = 0.5 * emb_probs + 0.5 * prior
            probs = probs / np.sum(probs)

            pred_idx = int(np.argmax(probs))
            classes = ["beginner", "intermediate", "advanced"]
            pred_class = classes[pred_idx]

            prob_dict = {c: round(float(p), 4) for c, p in zip(classes, probs)}

            _raw_conf = round(float(probs[pred_idx]), 4)
            _conf_meta = get_confidence_metadata("question-difficulty-v1", _raw_conf, source_tier="pretrained")
            return {
                "difficulty": pred_class,
                "predicted_difficulty": pred_class,
                "confidence": _raw_conf,
                "probabilities": prob_dict,
                "model_version": "pretrained_minilm_anchors",
                "source": IntelligenceSource.PRETRAINED.value,
                "method": "pretrained_embedding_anchor_similarity",
                "confidence_metadata": _conf_meta.to_dict(),
                "confidence_band": _conf_meta.confidence_band.value,
            }
        except Exception as e:
            logger.debug("Secondary pretrained model unavailable: %s", e)
            return None

    def _deterministic_heuristic_fallback(self, question_text: str) -> Dict[str, Any]:
        """
        Deterministic keyword & token length heuristic fallback.
        Confidence is calibrated to match strength and never manufactured to 1.0.
        """
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
            probs = {"beginner": 0.10, "intermediate": 0.25, "advanced": 0.65}
        elif has_intermediate_keywords or word_count > 60:
            diff = "intermediate"
            probs = {"beginner": 0.20, "intermediate": 0.60, "advanced": 0.20}
        elif has_beginner_keywords or word_count <= 60:
            diff = "beginner"
            probs = {"beginner": 0.65, "intermediate": 0.25, "advanced": 0.10}
        else:
            diff = "intermediate"
            probs = {"beginner": 0.25, "intermediate": 0.50, "advanced": 0.25}

        # Authentic heuristic confidence: reflects coverage probability
        confidence = probs[diff]

        _conf_meta = get_confidence_metadata("question-difficulty-v1", round(confidence, 4), source_tier="deterministic")
        return {
            "difficulty": diff,
            "predicted_difficulty": diff,
            "confidence": round(confidence, 4),
            "probabilities": probs,
            "model_version": "heuristic_fallback_v1",
            "source": IntelligenceSource.DETERMINISTIC.value,
            "method": "deterministic_heuristic_fallback",
            "confidence_metadata": _conf_meta.to_dict(),
            "confidence_band": _conf_meta.confidence_band.value,
        }

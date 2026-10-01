"""
Code Defect & Vulnerability Risk Detection Model.
Category: FINE-TUNED BY US (CodeBERT on CodeXGLUE defect detection corpus).
Base: microsoft/codebert-base
https://huggingface.co/microsoft/codebert-base

Pipeline:
    candidate code
    ↓  language validation
    ↓  CodeBERT encoder
    ↓  classification head
    ↓  defect probability + risk band
    ↓  (downstream: code execution/tests → Gemini code reasoning → combined)

This model outputs an ADDITIONAL code-risk signal.
It is NOT proof that code is incorrect — executable tests remain authoritative
for runtime correctness.

Output format:
    {
        "defect_probability": 0.73,
        "risk_band": "high",
        "model_version": "codebert_defect_v1.0",
        "confidence": 0.85,
        "inference_time_ms": 42.3,
        "risk_indicators": [...],
        "method": "fine_tuned_codebert"
    }

Risk band thresholds (documented & deterministic):
    low:    defect_probability < 0.30
    medium: 0.30 <= defect_probability < 0.65
    high:   defect_probability >= 0.65
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from ml.features.code_features import extract_code_lexical_features

logger = logging.getLogger(__name__)

DEFAULT_CODEBERT_MODEL = "microsoft/codebert-base"
DEFAULT_FINE_TUNED_PATH = "ml/models/weights/codebert_defect"
MODEL_VERSION = "codebert_defect_v1.0"

# Risk band thresholds
LOW_RISK_THRESHOLD = 0.30
HIGH_RISK_THRESHOLD = 0.65

# Supported languages for full analysis
SUPPORTED_LANGUAGES = {"python", "py", "c", "cpp", "c++", "java", "javascript", "js", "go", "rust"}


def _classify_risk_band(defect_prob: float) -> str:
    """Deterministic risk band classification from defect probability."""
    if defect_prob < LOW_RISK_THRESHOLD:
        return "low"
    elif defect_prob < HIGH_RISK_THRESHOLD:
        return "medium"
    else:
        return "high"


class CodeDefectDetector:
    """
    Detects software defect risk and code vulnerability patterns using CodeBERT.

    Loads a fine-tuned CodeBERT model if available at the configured path,
    falls back to the base model, or to deterministic AST heuristics
    if no transformer model can be loaded.

    Inference is optional — the system works when the model artifact is unavailable.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu",
    ):
        # Prefer fine-tuned model, then base model
        self._fine_tuned_path = model_path or DEFAULT_FINE_TUNED_PATH
        self.device = device
        self._tokenizer = None
        self._model = None
        self._model_version = MODEL_VERSION
        self._is_fine_tuned = False
        self._fallback_mode = False
        self._load_attempted = False
        self._training_metadata: Optional[Dict] = None

    def _load_model(self):
        """
        Lazy model loading with graceful fallback chain:
            1. Fine-tuned CodeBERT at DEFAULT_FINE_TUNED_PATH
            2. Base microsoft/codebert-base (zero-init classification head)
            3. Deterministic AST heuristic fallback
        """
        if self._load_attempted:
            return
        self._load_attempted = True

        # Try fine-tuned model first
        ft_path = Path(self._fine_tuned_path)
        if ft_path.exists() and (ft_path / "config.json").exists():
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
                logger.info("Loading fine-tuned CodeBERT defect model from %s", ft_path)
                self._tokenizer = AutoTokenizer.from_pretrained(str(ft_path))
                self._model = AutoModelForSequenceClassification.from_pretrained(str(ft_path))
                self._model.to(self.device)
                self._model.eval()
                self._is_fine_tuned = True

                # Load training metadata if available
                meta_path = ft_path / "training_metadata.json"
                if meta_path.exists():
                    with open(meta_path) as f:
                        self._training_metadata = json.load(f)
                    self._model_version = self._training_metadata.get(
                        "model_version", MODEL_VERSION
                    )

                logger.info(
                    "Fine-tuned CodeBERT loaded successfully (version=%s)",
                    self._model_version,
                )
                return
            except Exception as e:
                logger.warning(
                    "Failed to load fine-tuned model from %s: %s. Trying base model.",
                    ft_path, e,
                )

        # Try base CodeBERT
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            logger.info("Loading base CodeBERT model: %s", DEFAULT_CODEBERT_MODEL)
            self._tokenizer = AutoTokenizer.from_pretrained(DEFAULT_CODEBERT_MODEL)
            self._model = AutoModelForSequenceClassification.from_pretrained(
                DEFAULT_CODEBERT_MODEL, num_labels=2
            )
            self._model.to(self.device)
            self._model.eval()
            self._is_fine_tuned = False
            self._model_version = f"{MODEL_VERSION}_base_zero_init"
            logger.info("Base CodeBERT loaded (zero-init classification head)")
            return
        except Exception as e:
            logger.warning(
                "Could not load CodeBERT (%s): %s. Using deterministic AST fallback.",
                DEFAULT_CODEBERT_MODEL, e,
            )
            self._fallback_mode = True

    def _run_codebert_inference(self, code: str) -> Dict[str, float]:
        """
        Run forward pass through CodeBERT and return class probabilities.

        Returns:
            {"clean_prob": float, "defect_prob": float}
        """
        import torch

        inputs = self._tokenizer(
            code,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding="max_length",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

        clean_prob = float(probs[0])
        defect_prob = float(probs[1]) if len(probs) > 1 else 1.0 - clean_prob

        return {
            "clean_prob": round(clean_prob, 4),
            "defect_prob": round(defect_prob, 4),
        }

    def _compute_confidence(self, defect_prob: float) -> float:
        """
        Confidence = how far the prediction is from the decision boundary (0.5).
        A prediction at exactly 0.5 has 0% confidence; at 0.0 or 1.0 has 100%.
        """
        return round(abs(defect_prob - 0.5) * 2.0, 4)

    def analyze_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Analyze a code submission for defect or vulnerability risk.

        This produces an ADDITIONAL code-risk signal.
        Executable tests remain authoritative for runtime correctness.

        Returns:
            {
                "defect_probability": float,
                "risk_band": "low" | "medium" | "high",
                "model_version": str,
                "confidence": float,
                "inference_time_ms": float,
                "risk_indicators": list,
                "method": str,
                "lexical_features": dict,
            }
        """
        t0 = time.time()

        # Step 1: Language validation + lexical features
        lexical = extract_code_lexical_features(code, language)
        risk_indicators = []

        if not lexical["syntax_valid"] and language.lower() in ("python", "py"):
            risk_indicators.append("Syntax error or invalid language construct detected")

        if (
            lexical["has_loops"]
            and not lexical["has_try_except"]
            and lexical["non_empty_lines"] > 30
        ):
            risk_indicators.append(
                "Complex loop structure without exception isolation"
            )

        if lexical["has_recursion"]:
            risk_indicators.append("Recursive function detected — verify base case")

        # Step 2: Model inference
        self._load_model()

        if self._model is not None and not self._fallback_mode:
            try:
                probs = self._run_codebert_inference(code)
                defect_prob = probs["defect_prob"]
                confidence = self._compute_confidence(defect_prob)
                risk_band = _classify_risk_band(defect_prob)

                method = (
                    "fine_tuned_codebert"
                    if self._is_fine_tuned
                    else "codebert_base_zero_init"
                )

                return {
                    "defect_probability": defect_prob,
                    "risk_band": risk_band,
                    "model_version": self._model_version,
                    "confidence": confidence,
                    "inference_time_ms": round((time.time() - t0) * 1000, 2),
                    "risk_indicators": risk_indicators,
                    "method": method,
                    "lexical_features": lexical,
                    "is_fine_tuned": self._is_fine_tuned,
                    "signal_disclaimer": (
                        "This is an ML-derived code-risk signal, not proof of "
                        "incorrectness. Executable tests remain authoritative."
                    ),
                }
            except Exception as e:
                logger.error(
                    "CodeBERT inference failed: %s. Falling back to AST heuristics.",
                    e,
                )

        # Step 3: Deterministic AST heuristic fallback
        defect_prob = self._heuristic_defect_score(lexical)
        confidence = self._compute_confidence(defect_prob)
        risk_band = _classify_risk_band(defect_prob)

        return {
            "defect_probability": defect_prob,
            "risk_band": risk_band,
            "model_version": f"{MODEL_VERSION}_heuristic",
            "confidence": confidence,
            "inference_time_ms": round((time.time() - t0) * 1000, 2),
            "risk_indicators": risk_indicators,
            "method": "deterministic_ast_heuristic",
            "lexical_features": lexical,
            "is_fine_tuned": False,
            "signal_disclaimer": (
                "This is a heuristic code-risk signal (transformer unavailable), "
                "not proof of incorrectness."
            ),
        }

    @staticmethod
    def _heuristic_defect_score(lexical: Dict[str, Any]) -> float:
        """
        Deterministic fallback defect score based on AST/lexical features.
        Used only when the transformer model is unavailable.
        """
        score = 0.05  # Base risk for any code

        if not lexical["syntax_valid"]:
            score += 0.65  # Syntax errors are strong defect signals

        if lexical["has_recursion"]:
            score += 0.12

        if lexical["total_lines"] > 100:
            score += 0.08

        if lexical["has_loops"] and not lexical["has_try_except"]:
            score += 0.06

        if lexical["non_empty_lines"] < 3:
            score += 0.04  # Very short code might be incomplete

        return round(min(0.99, score), 4)

    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata for versioning and observability."""
        self._load_model()
        return {
            "model_version": self._model_version,
            "is_fine_tuned": self._is_fine_tuned,
            "fallback_mode": self._fallback_mode,
            "device": self.device,
            "base_model": DEFAULT_CODEBERT_MODEL,
            "fine_tuned_path": self._fine_tuned_path,
            "training_metadata": self._training_metadata,
        }

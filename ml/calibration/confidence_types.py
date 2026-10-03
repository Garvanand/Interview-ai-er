"""
Confidence Type Taxonomy and Production Confidence Band Classification.

This module defines the four-level confidence type taxonomy and the three
production-grade confidence bands used to communicate uncertainty to end users.

Confidence Types (per-model):
  - CALIBRATED_PROBABILITY: Post-hoc calibrated via temperature scaling or Platt
    scaling on held-out validation data. The numeric value is a well-calibrated
    probability — "0.85 means the prediction is correct ~85% of the time".
  - MODEL_SCORE: Raw softmax/sigmoid output that has NOT been post-hoc calibrated.
    Modern neural networks are notoriously over-confident; these numbers must not
    be interpreted as calibrated probabilities.
  - HEURISTIC_CONFIDENCE: A synthetic confidence value produced by a deterministic
    rule-based system (keyword regex, Jaccard overlap, etc.). It indicates relative
    signal strength but has no probabilistic interpretation.
  - UNAVAILABLE: No meaningful confidence can be assigned (malformed input, total
    model failure, or a method that produces no numeric uncertainty signal).

Production Confidence Bands:
  - HIGH_CONFIDENCE: Calibrated probability >= 0.75 OR model score >= 0.85 with
    calibration metadata indicating reasonable calibration.
  - MODERATE_CONFIDENCE: Calibrated probability in [0.45, 0.75) OR model score in
    [0.65, 0.85) OR heuristic confidence >= 0.60.
  - INSUFFICIENT_EVIDENCE: Everything else — the signal is too weak to present
    with conviction.

Design rationale:
  - Raw model scores require HIGHER thresholds than calibrated probabilities
    because uncalibrated neural networks are systematically overconfident.
  - Heuristic confidence is inherently coarser, so it is binned more
    conservatively.
  - The user-facing label deliberately avoids numeric precision to prevent
    false confidence.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


class ConfidenceType(str, enum.Enum):
    """Four-level taxonomy describing the provenance of a confidence value."""
    CALIBRATED_PROBABILITY = "calibrated_probability"
    MODEL_SCORE = "model_score"
    HEURISTIC_CONFIDENCE = "heuristic_confidence"
    UNAVAILABLE = "unavailable"


class ConfidenceBand(str, enum.Enum):
    """Production-grade confidence labels for end users."""
    HIGH = "High confidence"
    MODERATE = "Moderate confidence"
    INSUFFICIENT = "Insufficient evidence"


@dataclass
class ConfidenceMetadata:
    """
    Structured confidence metadata attached to every inference output.

    Fields:
        raw_score: The original numeric output from the model/heuristic.
        confidence_type: One of ConfidenceType — indicates provenance.
        confidence_band: Production label — one of ConfidenceBand.
        calibration_method: How calibration was performed (e.g. "temperature_scaling",
                            "platt_scaling", "isotonic_regression", or None).
        calibration_dataset_size: Number of validation samples used for calibration.
        temperature: If temperature scaling was applied, the learned T value.
        ece_on_calibration_set: Expected Calibration Error measured on the
                                calibration validation set (lower is better).
        interpretation_note: Human-readable note explaining what the confidence
                             value means for THIS specific model.
    """
    raw_score: float
    confidence_type: ConfidenceType
    confidence_band: ConfidenceBand
    calibration_method: Optional[str] = None
    calibration_dataset_size: Optional[int] = None
    temperature: Optional[float] = None
    ece_on_calibration_set: Optional[float] = None
    interpretation_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_score": self.raw_score,
            "confidence_type": self.confidence_type.value,
            "confidence_band": self.confidence_band.value,
            "calibration_method": self.calibration_method,
            "calibration_dataset_size": self.calibration_dataset_size,
            "temperature": self.temperature,
            "ece_on_calibration_set": self.ece_on_calibration_set,
            "interpretation_note": self.interpretation_note,
        }


# ── Production Confidence Band Classification ──────────────────────────────

# Thresholds are intentionally asymmetric: uncalibrated model scores must
# clear a higher bar because neural networks are systematically overconfident.

_BAND_THRESHOLDS = {
    ConfidenceType.CALIBRATED_PROBABILITY: {
        "high": 0.75,
        "moderate": 0.45,
    },
    ConfidenceType.MODEL_SCORE: {
        "high": 0.85,
        "moderate": 0.65,
    },
    ConfidenceType.HEURISTIC_CONFIDENCE: {
        "high": 0.80,
        "moderate": 0.60,
    },
}


def classify_confidence_band(
    raw_score: float,
    confidence_type: ConfidenceType,
) -> ConfidenceBand:
    """
    Map a numeric confidence score to a production-grade confidence band,
    using thresholds appropriate to the confidence type.

    For UNAVAILABLE type, always returns INSUFFICIENT.
    """
    if confidence_type == ConfidenceType.UNAVAILABLE:
        return ConfidenceBand.INSUFFICIENT

    thresholds = _BAND_THRESHOLDS.get(confidence_type, _BAND_THRESHOLDS[ConfidenceType.MODEL_SCORE])

    if raw_score >= thresholds["high"]:
        return ConfidenceBand.HIGH
    elif raw_score >= thresholds["moderate"]:
        return ConfidenceBand.MODERATE
    else:
        return ConfidenceBand.INSUFFICIENT

"""
Confidence Calibration and Uncertainty Quantification Framework.

This package provides:
1. Temperature scaling for post-hoc neural network calibration.
2. Reliability diagram generation for visual calibration assessment.
3. Confidence metadata classification (calibrated / model_score / heuristic / unavailable).
4. Production-grade confidence bands ("High confidence", "Moderate confidence", "Insufficient evidence").
5. Evaluation outputs: reliability diagrams, confidence distributions,
   high-confidence error cases, low-confidence correct cases.

Key distinction (documented in docs/CONFIDENCE_GLOSSARY.md):
  - Prediction Probability: raw softmax/sigmoid output from a neural network.
  - Confidence: a calibrated, interpretable measure of certainty.
  - Candidate Skill Estimate: latent ability (theta) from IRT — NOT a probability.
"""
from __future__ import annotations

from .confidence_types import (
    ConfidenceType,
    ConfidenceBand,
    ConfidenceMetadata,
    classify_confidence_band,
)
from .temperature_scaling import TemperatureScaler
from .calibration_metrics import (
    expected_calibration_error,
    reliability_diagram_data,
    confidence_distribution_data,
    high_confidence_errors,
    low_confidence_correct,
    CalibrationReport,
    generate_calibration_report,
)
from .model_confidence_registry import (
    get_confidence_metadata,
    MODEL_CONFIDENCE_REGISTRY,
)

__all__ = [
    "ConfidenceType",
    "ConfidenceBand",
    "ConfidenceMetadata",
    "classify_confidence_band",
    "TemperatureScaler",
    "expected_calibration_error",
    "reliability_diagram_data",
    "confidence_distribution_data",
    "high_confidence_errors",
    "low_confidence_correct",
    "CalibrationReport",
    "generate_calibration_report",
    "get_confidence_metadata",
    "MODEL_CONFIDENCE_REGISTRY",
]

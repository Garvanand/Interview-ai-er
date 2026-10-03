"""
Model Confidence Registry — Per-Model Confidence Type Classification.

For every model in the pipeline, this registry declares:
  - What KIND of confidence the model produces.
  - Whether calibration has been performed.
  - What the numeric value actually MEANS.
  - How to construct the ConfidenceMetadata for inference outputs.

This is the authoritative source for the question:
  "Is this model's confidence a calibrated probability, a raw model score,
   a heuristic signal, or unavailable?"

Key design decisions:
  - We do NOT pretend uncalibrated softmax outputs are probabilities.
  - Each model entry documents exactly what would be needed to upgrade
    from MODEL_SCORE to CALIBRATED_PROBABILITY (validation data, calibration
    technique, etc.).
  - The IRT mastery model is explicitly called out: its theta output is a
    latent ability estimate, NOT a probability or confidence score.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ml.calibration.confidence_types import (
    ConfidenceBand,
    ConfidenceMetadata,
    ConfidenceType,
    classify_confidence_band,
)

logger = logging.getLogger(__name__)


# ── Per-Model Confidence Registry ──────────────────────────────────────────

MODEL_CONFIDENCE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "question-difficulty-v1": {
        "confidence_type": ConfidenceType.MODEL_SCORE,
        "interpretation": (
            "Raw softmax probability from the difficulty classifier "
            "(Ridge Regression or transformer). NOT post-hoc calibrated. "
            "Neural network softmax outputs are known to be overconfident; "
            "treat this as a relative ranking signal, not a calibrated probability."
        ),
        "calibration_status": "uncalibrated",
        "calibration_feasibility": (
            "Feasible. Requires ~500+ labelled questions with known difficulty. "
            "Apply temperature scaling to the logits before softmax. "
            "BAAI/TACO dataset provides ground-truth difficulty labels."
        ),
        "upgrade_path": "temperature_scaling",
        "validation_data_available": True,
        "estimated_validation_size": 2000,
        "tiers": {
            "ml": {
                "confidence_type": ConfidenceType.MODEL_SCORE,
                "note": "Softmax output from trained transformer/Ridge classifier.",
            },
            "pretrained": {
                "confidence_type": ConfidenceType.MODEL_SCORE,
                "note": "Cosine similarity softmax with temperature; not calibrated.",
            },
            "llm": {
                "confidence_type": ConfidenceType.MODEL_SCORE,
                "note": "Gemini self-reported confidence; no calibration guarantee.",
            },
            "deterministic": {
                "confidence_type": ConfidenceType.HEURISTIC_CONFIDENCE,
                "note": "Keyword-match heuristic probability; synthetic, not calibrated.",
            },
        },
    },

    "question-skill-v1": {
        "confidence_type": ConfidenceType.MODEL_SCORE,
        "interpretation": (
            "predict_proba output from CalibratedClassifierCV (SGD + Platt scaling). "
            "The scikit-learn CalibratedClassifierCV applies sigmoid calibration "
            "internally, so these probabilities have SOME calibration — but the "
            "calibration quality depends on the cross-validation fold size. "
            "Treat as a semi-calibrated model score."
        ),
        "calibration_status": "partially_calibrated",
        "calibration_feasibility": (
            "Already partially calibrated via CalibratedClassifierCV. "
            "To fully calibrate: hold out 20% of TACO tags, apply "
            "temperature scaling on the held-out set, and measure ECE."
        ),
        "upgrade_path": "temperature_scaling_on_holdout",
        "validation_data_available": True,
        "estimated_validation_size": 5000,
        "tiers": {
            "ml": {
                "confidence_type": ConfidenceType.MODEL_SCORE,
                "note": "CalibratedClassifierCV predict_proba; partially calibrated.",
            },
            "deterministic": {
                "confidence_type": ConfidenceType.HEURISTIC_CONFIDENCE,
                "note": "Regex keyword match scores; no probabilistic interpretation.",
            },
        },
    },

    "answer-nli-v1": {
        "confidence_type": ConfidenceType.MODEL_SCORE,
        "interpretation": (
            "Mean DeBERTa-v3 entailment probability across concepts, blended "
            "with MiniLM cosine similarity. DeBERTa NLI models are trained on "
            "MNLI/SNLI with cross-entropy loss and produce softmax outputs over "
            "{entailment, contradiction, neutral}. These are NOT calibrated "
            "probabilities — DeBERTa is known to be overconfident on NLI tasks."
        ),
        "calibration_status": "uncalibrated",
        "calibration_feasibility": (
            "Feasible with effort. Requires a labelled concept-coverage dataset "
            "(question → expected_concepts → ground_truth_coverage_status). "
            "Temperature scaling on the entailment logits would improve calibration. "
            "Alternative: build a small internal eval set from past interview sessions."
        ),
        "upgrade_path": "temperature_scaling_on_nli_logits",
        "validation_data_available": False,
        "estimated_validation_size": None,
        "tiers": {
            "ml": {
                "confidence_type": ConfidenceType.MODEL_SCORE,
                "note": "DeBERTa NLI softmax + MiniLM similarity; uncalibrated.",
            },
            "pretrained": {
                "confidence_type": ConfidenceType.MODEL_SCORE,
                "note": "MiniLM cosine similarity; geometric, not probabilistic.",
            },
            "llm": {
                "confidence_type": ConfidenceType.MODEL_SCORE,
                "note": "Gemini self-assessed confidence; no calibration.",
            },
            "deterministic": {
                "confidence_type": ConfidenceType.HEURISTIC_CONFIDENCE,
                "note": "Jaccard + term overlap composite; synthetic confidence.",
            },
        },
    },

    "code-risk-v1": {
        "confidence_type": ConfidenceType.MODEL_SCORE,
        "interpretation": (
            "Distance from decision boundary (|defect_prob - 0.5| * 2). "
            "This is a geometric transformation of the softmax output, not a "
            "calibrated probability. A confidence of 0.9 means the model is "
            "decisively on one side of the boundary, but does NOT mean the "
            "prediction is correct 90% of the time."
        ),
        "calibration_status": "uncalibrated",
        "calibration_feasibility": (
            "Feasible. CodeXGLUE defect detection dataset provides binary "
            "labels (defective/clean). Temperature scaling on the logits "
            "before the boundary-distance transform would calibrate the "
            "underlying probabilities. The confidence formula should then "
            "use calibrated probabilities instead of raw softmax."
        ),
        "upgrade_path": "temperature_scaling_then_boundary_distance",
        "validation_data_available": True,
        "estimated_validation_size": 2500,
        "tiers": {
            "ml": {
                "confidence_type": ConfidenceType.MODEL_SCORE,
                "note": "CodeBERT softmax → boundary distance; uncalibrated.",
            },
            "pretrained": {
                "confidence_type": ConfidenceType.MODEL_SCORE,
                "note": "Base CodeBERT zero-init head; uncalibrated and unreliable.",
            },
            "llm": {
                "confidence_type": ConfidenceType.MODEL_SCORE,
                "note": "Gemini self-assessed defect confidence; no calibration.",
            },
            "deterministic": {
                "confidence_type": ConfidenceType.HEURISTIC_CONFIDENCE,
                "note": "AST heuristic defect score → boundary distance; synthetic.",
            },
        },
    },

    "mastery-v1": {
        "confidence_type": ConfidenceType.UNAVAILABLE,
        "interpretation": (
            "The IRT mastery model produces a latent ability estimate (theta ∈ [-3, +3]) "
            "mapped to a proficiency scale [0, 100]. This is NOT a probability and NOT "
            "a confidence score — it is a point estimate of candidate ability on a "
            "psychometric scale. The 'expected_prob' field is the IRT P(correct) given "
            "theta, which IS a calibrated probability under the 2PL model assumptions, "
            "but it measures item response probability, not prediction confidence."
        ),
        "calibration_status": "not_applicable",
        "calibration_feasibility": (
            "Confidence in the traditional sense is not applicable to IRT ability "
            "estimates. What IS meaningful is the Standard Error of Measurement (SEM), "
            "which quantifies uncertainty in theta. SEM decreases as more items are "
            "administered. Future enhancement: compute and expose SEM alongside theta."
        ),
        "upgrade_path": "standard_error_of_measurement",
        "validation_data_available": True,
        "estimated_validation_size": None,
        "tiers": {
            "ml": {
                "confidence_type": ConfidenceType.UNAVAILABLE,
                "note": (
                    "Theta is an ability estimate, not a confidence. "
                    "P(correct) is a calibrated response probability but "
                    "measures item difficulty match, not prediction certainty."
                ),
            },
        },
    },
}


def get_confidence_metadata(
    model_name: str,
    raw_score: float,
    source_tier: str = "ml",
    calibration_method: Optional[str] = None,
    calibration_dataset_size: Optional[int] = None,
    temperature: Optional[float] = None,
    ece: Optional[float] = None,
) -> ConfidenceMetadata:
    """
    Construct a ConfidenceMetadata for a given model and inference score.

    Looks up the model in MODEL_CONFIDENCE_REGISTRY to determine the
    confidence type, then classifies into a production confidence band.

    Args:
        model_name: Canonical model identifier (e.g. "question-difficulty-v1").
        raw_score: The numeric confidence/probability from the model.
        source_tier: Which tier produced this output ("ml", "pretrained",
                     "deterministic", "llm", "unavailable").
        calibration_method: Override calibration method if known.
        calibration_dataset_size: Size of calibration dataset if known.
        temperature: Learned temperature if temperature scaling was applied.
        ece: ECE on calibration set if measured.

    Returns:
        ConfidenceMetadata with type, band, and interpretation.
    """
    registry_entry = MODEL_CONFIDENCE_REGISTRY.get(model_name, {})

    # Determine confidence type from the tier-specific entry if available
    tiers = registry_entry.get("tiers", {})
    tier_entry = tiers.get(source_tier, {})
    conf_type = tier_entry.get("confidence_type", registry_entry.get(
        "confidence_type", ConfidenceType.MODEL_SCORE
    ))

    # Override with calibration_method if provided
    if calibration_method and calibration_method != "none":
        conf_type = ConfidenceType.CALIBRATED_PROBABILITY

    # Classify into production band
    band = classify_confidence_band(raw_score, conf_type)

    # Build interpretation note
    tier_note = tier_entry.get("note", registry_entry.get("interpretation", ""))
    interpretation = registry_entry.get("interpretation", tier_note)

    return ConfidenceMetadata(
        raw_score=round(raw_score, 4),
        confidence_type=conf_type,
        confidence_band=band,
        calibration_method=calibration_method or registry_entry.get("calibration_status"),
        calibration_dataset_size=calibration_dataset_size,
        temperature=temperature,
        ece_on_calibration_set=ece,
        interpretation_note=interpretation,
    )

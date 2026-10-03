"""
Calibration Evaluation Metrics and Diagnostic Outputs.

Provides all four evaluation outputs required by the confidence framework:
1. Reliability diagram data (predicted confidence vs. observed accuracy per bin).
2. Confidence distribution histogram data.
3. High-confidence error cases (model was confident but wrong).
4. Low-confidence correct cases (model was uncertain but actually right).

Plus the Expected Calibration Error (ECE) and Maximum Calibration Error (MCE).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ── Expected Calibration Error ──────────────────────────────────────────────

def expected_calibration_error(
    confidences: Sequence[float],
    accuracies: Sequence[int],
    num_bins: int = 10,
) -> float:
    """
    Compute the Expected Calibration Error (ECE).

    ECE = sum_{b=1}^{B} (n_b / N) * |acc(b) - conf(b)|

    A perfectly calibrated model has ECE = 0. An ECE > 0.10 typically
    indicates meaningful miscalibration.

    Args:
        confidences: Model's confidence for each prediction (max softmax prob).
        accuracies: Binary array — 1 if prediction was correct, 0 otherwise.
        num_bins: Number of equal-width bins.

    Returns:
        ECE value (float in [0, 1]).
    """
    confs = np.asarray(confidences, dtype=np.float64)
    accs = np.asarray(accuracies, dtype=np.float64)
    n = len(confs)
    if n == 0:
        return 0.0

    bin_boundaries = np.linspace(0.0, 1.0, num_bins + 1)
    ece = 0.0
    for i in range(num_bins):
        mask = (confs >= bin_boundaries[i]) & (confs < bin_boundaries[i + 1])
        bin_count = int(np.sum(mask))
        if bin_count > 0:
            bin_acc = float(np.mean(accs[mask]))
            bin_conf = float(np.mean(confs[mask]))
            ece += (bin_count / n) * abs(bin_acc - bin_conf)

    return round(ece, 6)


def maximum_calibration_error(
    confidences: Sequence[float],
    accuracies: Sequence[int],
    num_bins: int = 10,
) -> float:
    """
    Maximum Calibration Error (MCE) — the worst-case bin deviation.

    Useful for safety-critical applications where you care about the
    single worst-calibrated confidence region.
    """
    confs = np.asarray(confidences, dtype=np.float64)
    accs = np.asarray(accuracies, dtype=np.float64)
    n = len(confs)
    if n == 0:
        return 0.0

    bin_boundaries = np.linspace(0.0, 1.0, num_bins + 1)
    mce = 0.0
    for i in range(num_bins):
        mask = (confs >= bin_boundaries[i]) & (confs < bin_boundaries[i + 1])
        bin_count = int(np.sum(mask))
        if bin_count > 0:
            bin_acc = float(np.mean(accs[mask]))
            bin_conf = float(np.mean(confs[mask]))
            mce = max(mce, abs(bin_acc - bin_conf))

    return round(mce, 6)


# ── Reliability Diagram Data ────────────────────────────────────────────────

def reliability_diagram_data(
    confidences: Sequence[float],
    accuracies: Sequence[int],
    num_bins: int = 10,
) -> Dict[str, Any]:
    """
    Generate data for a reliability diagram (calibration curve).

    A reliability diagram plots mean predicted confidence (x-axis) against
    observed accuracy (y-axis) for each bin. A perfectly calibrated model
    lies on the diagonal y=x.

    Returns:
        {
            "bins": [{"bin_lower": 0.0, "bin_upper": 0.1, "mean_confidence": 0.05,
                       "observed_accuracy": 0.04, "count": 42, "gap": 0.01}, ...],
            "ece": 0.045,
            "mce": 0.12,
            "num_samples": 500,
            "num_bins": 10,
            "perfectly_calibrated_line": [[0.0, 0.0], [1.0, 1.0]],
        }
    """
    confs = np.asarray(confidences, dtype=np.float64)
    accs = np.asarray(accuracies, dtype=np.float64)
    n = len(confs)

    bin_boundaries = np.linspace(0.0, 1.0, num_bins + 1)
    bins = []

    for i in range(num_bins):
        lo = float(bin_boundaries[i])
        hi = float(bin_boundaries[i + 1])
        mask = (confs >= lo) & (confs < hi)
        count = int(np.sum(mask))
        if count > 0:
            mean_conf = round(float(np.mean(confs[mask])), 4)
            obs_acc = round(float(np.mean(accs[mask])), 4)
        else:
            mean_conf = round((lo + hi) / 2, 4)
            obs_acc = None

        bins.append({
            "bin_lower": round(lo, 2),
            "bin_upper": round(hi, 2),
            "mean_confidence": mean_conf,
            "observed_accuracy": obs_acc,
            "count": count,
            "gap": round(abs((obs_acc or mean_conf) - mean_conf), 4),
        })

    return {
        "bins": bins,
        "ece": expected_calibration_error(confidences, accuracies, num_bins),
        "mce": maximum_calibration_error(confidences, accuracies, num_bins),
        "num_samples": n,
        "num_bins": num_bins,
        "perfectly_calibrated_line": [[0.0, 0.0], [1.0, 1.0]],
    }


# ── Confidence Distribution ────────────────────────────────────────────────

def confidence_distribution_data(
    confidences: Sequence[float],
    num_bins: int = 20,
) -> Dict[str, Any]:
    """
    Generate histogram data for the distribution of model confidence scores.

    This helps identify whether the model is:
      - Overconfident (mass near 1.0)
      - Underconfident (mass near 0.5)
      - Well-distributed

    Returns:
        {
            "histogram": [{"bin_lower": 0.0, "bin_upper": 0.05, "count": 12}, ...],
            "mean_confidence": 0.73,
            "median_confidence": 0.78,
            "std_confidence": 0.15,
            "min_confidence": 0.12,
            "max_confidence": 0.99,
            "num_samples": 500,
        }
    """
    confs = np.asarray(confidences, dtype=np.float64)
    n = len(confs)
    if n == 0:
        return {
            "histogram": [],
            "mean_confidence": 0.0,
            "median_confidence": 0.0,
            "std_confidence": 0.0,
            "min_confidence": 0.0,
            "max_confidence": 0.0,
            "num_samples": 0,
        }

    bin_boundaries = np.linspace(0.0, 1.0, num_bins + 1)
    histogram = []
    for i in range(num_bins):
        lo = float(bin_boundaries[i])
        hi = float(bin_boundaries[i + 1])
        count = int(np.sum((confs >= lo) & (confs < hi)))
        histogram.append({
            "bin_lower": round(lo, 3),
            "bin_upper": round(hi, 3),
            "count": count,
        })

    return {
        "histogram": histogram,
        "mean_confidence": round(float(np.mean(confs)), 4),
        "median_confidence": round(float(np.median(confs)), 4),
        "std_confidence": round(float(np.std(confs)), 4),
        "min_confidence": round(float(np.min(confs)), 4),
        "max_confidence": round(float(np.max(confs)), 4),
        "num_samples": n,
    }


# ── High-Confidence Error Cases ────────────────────────────────────────────

def high_confidence_errors(
    confidences: Sequence[float],
    predictions: Sequence[Any],
    actuals: Sequence[Any],
    threshold: float = 0.80,
    max_cases: int = 50,
) -> List[Dict[str, Any]]:
    """
    Find cases where the model was HIGHLY confident but WRONG.

    These are the most dangerous cases — the model misleads the user.
    Monitoring this set over time is critical for trust.

    Args:
        confidences: Model confidence per prediction.
        predictions: Model's predicted labels.
        actuals: Ground-truth labels.
        threshold: Minimum confidence to qualify as "high confidence".
        max_cases: Maximum number of cases to return.

    Returns:
        List of dicts with index, confidence, predicted, actual.
    """
    cases = []
    for i, (conf, pred, actual) in enumerate(zip(confidences, predictions, actuals)):
        if float(conf) >= threshold and pred != actual:
            cases.append({
                "index": i,
                "confidence": round(float(conf), 4),
                "predicted": pred,
                "actual": actual,
            })
    # Sort by descending confidence (most dangerous first)
    cases.sort(key=lambda x: x["confidence"], reverse=True)
    return cases[:max_cases]


# ── Low-Confidence Correct Cases ───────────────────────────────────────────

def low_confidence_correct(
    confidences: Sequence[float],
    predictions: Sequence[Any],
    actuals: Sequence[Any],
    threshold: float = 0.50,
    max_cases: int = 50,
) -> List[Dict[str, Any]]:
    """
    Find cases where the model was UNCERTAIN but actually CORRECT.

    These represent missed opportunity — the model "knew" the right answer
    but lacked the confidence to communicate it clearly. Understanding these
    cases can reveal calibration issues or feature gaps.

    Args:
        confidences: Model confidence per prediction.
        predictions: Model's predicted labels.
        actuals: Ground-truth labels.
        threshold: Maximum confidence to qualify as "low confidence".
        max_cases: Maximum number of cases to return.

    Returns:
        List of dicts with index, confidence, predicted, actual.
    """
    cases = []
    for i, (conf, pred, actual) in enumerate(zip(confidences, predictions, actuals)):
        if float(conf) < threshold and pred == actual:
            cases.append({
                "index": i,
                "confidence": round(float(conf), 4),
                "predicted": pred,
                "actual": actual,
            })
    # Sort by ascending confidence (least confident correct predictions first)
    cases.sort(key=lambda x: x["confidence"])
    return cases[:max_cases]


# ── Calibration Report ─────────────────────────────────────────────────────

@dataclass
class CalibrationReport:
    """
    Complete calibration evaluation report for a single model.
    Contains all four diagnostic outputs.
    """
    model_name: str
    confidence_type: str
    reliability_diagram: Dict[str, Any] = field(default_factory=dict)
    confidence_distribution: Dict[str, Any] = field(default_factory=dict)
    high_confidence_errors: List[Dict[str, Any]] = field(default_factory=list)
    low_confidence_correct: List[Dict[str, Any]] = field(default_factory=list)
    ece: float = 0.0
    mce: float = 0.0
    num_samples: int = 0
    calibration_method: Optional[str] = None
    temperature: Optional[float] = None
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "confidence_type": self.confidence_type,
            "reliability_diagram": self.reliability_diagram,
            "confidence_distribution": self.confidence_distribution,
            "high_confidence_errors": self.high_confidence_errors,
            "low_confidence_correct": self.low_confidence_correct,
            "ece": self.ece,
            "mce": self.mce,
            "num_samples": self.num_samples,
            "calibration_method": self.calibration_method,
            "temperature": self.temperature,
            "summary": self.summary,
        }


def generate_calibration_report(
    model_name: str,
    confidence_type: str,
    confidences: Sequence[float],
    predictions: Sequence[Any],
    actuals: Sequence[Any],
    calibration_method: Optional[str] = None,
    temperature: Optional[float] = None,
    num_bins: int = 10,
) -> CalibrationReport:
    """
    Generate a complete CalibrationReport for a model.

    This is the primary entry point for producing all four diagnostic outputs
    from a set of validation predictions.

    Args:
        model_name: Canonical model identifier.
        confidence_type: One of ConfidenceType values.
        confidences: Model's confidence per prediction.
        predictions: Model's predicted labels.
        actuals: Ground-truth labels.
        calibration_method: How calibration was performed (if any).
        temperature: Learned temperature (if temperature scaling was used).
        num_bins: Number of bins for reliability diagram.

    Returns:
        CalibrationReport with all four diagnostic outputs populated.
    """
    binary_correct = [1 if p == a else 0 for p, a in zip(predictions, actuals)]

    rel_data = reliability_diagram_data(confidences, binary_correct, num_bins)
    conf_dist = confidence_distribution_data(confidences)
    hi_conf_err = high_confidence_errors(confidences, predictions, actuals)
    lo_conf_cor = low_confidence_correct(confidences, predictions, actuals)

    ece_val = rel_data["ece"]
    mce_val = rel_data["mce"]

    # Generate human-readable summary
    n = len(confidences)
    if ece_val < 0.05:
        cal_quality = "well-calibrated"
    elif ece_val < 0.10:
        cal_quality = "reasonably calibrated"
    elif ece_val < 0.20:
        cal_quality = "moderately miscalibrated"
    else:
        cal_quality = "severely miscalibrated"

    summary = (
        f"{model_name}: {cal_quality} (ECE={ece_val:.4f}, MCE={mce_val:.4f}). "
        f"{len(hi_conf_err)} high-confidence errors, "
        f"{len(lo_conf_cor)} low-confidence correct cases "
        f"out of {n} samples."
    )

    return CalibrationReport(
        model_name=model_name,
        confidence_type=confidence_type,
        reliability_diagram=rel_data,
        confidence_distribution=conf_dist,
        high_confidence_errors=hi_conf_err,
        low_confidence_correct=lo_conf_cor,
        ece=ece_val,
        mce=mce_val,
        num_samples=n,
        calibration_method=calibration_method,
        temperature=temperature,
        summary=summary,
    )

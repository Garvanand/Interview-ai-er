"""
Evaluation and benchmark metric utilities for ML capabilities.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence
import numpy as np


def compute_classification_metrics(y_true: Sequence[Any], y_pred: Sequence[Any]) -> Dict[str, float]:
    """Compute accuracy, macro precision, recall, and macro F1 score without external libraries if needed."""
    labels = sorted(list(set(y_true) | set(y_pred)))
    total = len(y_true)
    if total == 0:
        return {"accuracy": 0.0, "macro_f1": 0.0}

    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    acc = correct / total

    precisions = []
    recalls = []
    f1s = []

    for label in labels:
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == label and yp == label)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != label and yp == label)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == label and yp != label)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        precisions.append(prec)
        recalls.append(rec)
        f1s.append(f1)

    return {
        "accuracy": round(acc, 4),
        "macro_precision": round(float(np.mean(precisions)), 4),
        "macro_recall": round(float(np.mean(recalls)), 4),
        "macro_f1": round(float(np.mean(f1s)), 4),
    }


def compute_regression_metrics(y_true: Sequence[float], y_pred: Sequence[float]) -> Dict[str, float]:
    """Compute Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE)."""
    if len(y_true) == 0:
        return {"mae": 0.0, "rmse": 0.0}
    errors = [abs(yt - yp) for yt, yp in zip(y_true, y_pred)]
    sq_errors = [(yt - yp) ** 2 for yt, yp in zip(y_true, y_pred)]
    mae = float(np.mean(errors))
    rmse = math.sqrt(float(np.mean(sq_errors)))
    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4)
    }


def compute_coverage_calibration_error(
    predicted_probs: Sequence[float],
    binary_actuals: Sequence[int],
    num_bins: int = 5
) -> float:
    """Expected Calibration Error (ECE) for NLI concept entailment predictions."""
    if len(predicted_probs) == 0:
        return 0.0

    bins = np.linspace(0.0, 1.0, num_bins + 1)
    ece = 0.0
    total = len(predicted_probs)

    for i in range(num_bins):
        bin_mask = (predicted_probs >= bins[i]) & (predicted_probs < bins[i + 1])
        bin_count = np.sum(bin_mask)
        if bin_count > 0:
            bin_acc = np.mean(np.array(binary_actuals)[bin_mask])
            bin_conf = np.mean(np.array(predicted_probs)[bin_mask])
            ece += (bin_count / total) * abs(bin_acc - bin_conf)

    return round(float(ece), 4)

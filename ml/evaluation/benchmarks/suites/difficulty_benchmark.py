"""
Benchmark Suite A: Question Difficulty Predictor.

Evaluates QuestionDifficultyPredictor across all 4 benchmark sources:
- Public dataset (BAAI/TACO)
- Synthetic fixtures (edge cases, distractor tokens, brevity)
- Interview-specific problems (real system design, coding)
- Manually curated problems (gold standard verified)

Reports:
- Overall & per-source accuracy and macro F1
- Ordinal Mean Absolute Error (MAE)
- Per-class metrics (beginner, intermediate, advanced)
- Latency per sample
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List
import numpy as np

from ml.models.difficulty_predictor import QuestionDifficultyPredictor
from ml.evaluation.benchmarks.sources import (
    load_public_difficulty_samples,
    load_synthetic_difficulty_fixtures,
    load_interview_specific_questions,
    load_curated_difficulty_questions,
)

logger = logging.getLogger(__name__)

ORDINAL_MAP = {"beginner": 0, "intermediate": 1, "advanced": 2}


def run_difficulty_benchmark(predictor: Optional[QuestionDifficultyPredictor] = None) -> Dict[str, Any]:
    """Runs Category A: Question Difficulty benchmark across all sources."""
    model = predictor or QuestionDifficultyPredictor()

    sources = {
        "public_dataset": load_public_difficulty_samples(max_samples=20),
        "synthetic_fixtures": load_synthetic_difficulty_fixtures(),
        "interview_specific": load_interview_specific_questions(),
        "manually_curated": load_curated_difficulty_questions(),
    }

    per_source_results = {}
    all_y_true = []
    all_y_pred = []
    all_latencies = []
    sample_records = []

    for source_name, dataset in sources.items():
        correct = 0
        total = len(dataset)
        source_latencies = []
        source_y_true = []
        source_y_pred = []

        for item in dataset:
            q_id = item["id"]
            text = item["question"]
            expected = item["expected_difficulty"].lower()

            t0 = time.time()
            res = model.predict(text, allow_llm=False)
            latency_ms = (time.time() - t0) * 1000.0

            predicted = res.get("difficulty", "intermediate").lower()
            confidence = res.get("confidence", 0.0)

            is_correct = (predicted == expected)
            if is_correct:
                correct += 1

            source_latencies.append(latency_ms)
            source_y_true.append(expected)
            source_y_pred.append(predicted)

            all_y_true.append(expected)
            all_y_pred.append(predicted)
            all_latencies.append(latency_ms)

            sample_records.append({
                "id": q_id,
                "source": source_name,
                "question": text[:100] + "..." if len(text) > 100 else text,
                "expected": expected,
                "predicted": predicted,
                "confidence": round(confidence, 4),
                "is_correct": is_correct,
                "latency_ms": round(latency_ms, 2),
            })

        acc = correct / total if total > 0 else 0.0
        # Calculate source ordinal MAE
        ord_errors = [abs(ORDINAL_MAP.get(yt, 1) - ORDINAL_MAP.get(yp, 1)) for yt, yp in zip(source_y_true, source_y_pred)]
        source_mae = float(np.mean(ord_errors)) if ord_errors else 0.0

        per_source_results[source_name] = {
            "samples": total,
            "accuracy": round(acc, 4),
            "ordinal_mae": round(source_mae, 4),
            "avg_latency_ms": round(float(np.mean(source_latencies)), 2) if source_latencies else 0.0,
        }

    # Aggregate metrics
    overall_correct = sum(1 for yt, yp in zip(all_y_true, all_y_pred) if yt == yp)
    total_samples = len(all_y_true)
    overall_acc = overall_correct / total_samples if total_samples > 0 else 0.0

    overall_mae = float(np.mean([
        abs(ORDINAL_MAP.get(yt, 1) - ORDINAL_MAP.get(yp, 1))
        for yt, yp in zip(all_y_true, all_y_pred)
    ])) if all_y_true else 0.0

    # Per-class metrics
    classes = ["beginner", "intermediate", "advanced"]
    per_class = {}
    for cls_name in classes:
        tp = sum(1 for yt, yp in zip(all_y_true, all_y_pred) if yt == cls_name and yp == cls_name)
        fp = sum(1 for yt, yp in zip(all_y_true, all_y_pred) if yt != cls_name and yp == cls_name)
        fn = sum(1 for yt, yp in zip(all_y_true, all_y_pred) if yt == cls_name and yp != cls_name)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        per_class[cls_name] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "support": sum(1 for yt in all_y_true if yt == cls_name),
        }

    macro_f1 = float(np.mean([m["f1_score"] for m in per_class.values()]))

    return {
        "category": "A. Question difficulty",
        "model_evaluated": "QuestionDifficultyPredictor",
        "total_samples": total_samples,
        "overall_accuracy": round(overall_acc, 4),
        "overall_macro_f1": round(macro_f1, 4),
        "overall_ordinal_mae": round(overall_mae, 4),
        "avg_latency_ms": round(float(np.mean(all_latencies)), 2) if all_latencies else 0.0,
        "per_source_breakdown": per_source_results,
        "per_class_metrics": per_class,
        "sample_records": sample_records,
    }

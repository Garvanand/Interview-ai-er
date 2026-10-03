"""
Benchmark Suite B: Question Skill Classification.

Evaluates QuestionSkillClassifier across multiple benchmark sources:
- Public dataset (BAAI/TACO)
- Interview-specific problems
- Manually curated problems

Reports:
- Precision, Recall, F1 across multi-label predictions
- Mean Jaccard Similarity (Intersection over Union)
- Exact match ratio
- Per-source breakdown
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Set
import numpy as np

from ml.models.skill_classifier import QuestionSkillClassifier
from ml.evaluation.benchmarks.sources import (
    load_public_skill_samples,
    load_interview_specific_questions,
    load_curated_skill_questions,
)

logger = logging.getLogger(__name__)


def run_skills_benchmark(classifier: Optional[QuestionSkillClassifier] = None) -> Dict[str, Any]:
    """Runs Category B: Question Skills benchmark across all sources."""
    model = classifier or QuestionSkillClassifier()

    sources = {
        "public_dataset": load_public_skill_samples(max_samples=15),
        "interview_specific": load_interview_specific_questions(),
        "manually_curated": load_curated_skill_questions(),
    }

    per_source_results = {}
    all_jaccards = []
    all_precisions = []
    all_recalls = []
    all_f1s = []
    all_exact_matches = []
    sample_records = []

    for source_name, dataset in sources.items():
        src_jaccards = []
        src_exact = 0
        total = len(dataset)

        for item in dataset:
            q_id = item["id"]
            text = item["question"]
            expected_skills = set(s.lower() for s in item.get("expected_skills", []))

            t0 = time.time()
            res = model.predict(text, threshold=0.25, top_k=4)
            latency_ms = (time.time() - t0) * 1000.0

            predicted_skills = set(s.lower() for s in res.get("top_skills", []))
            confidence = res.get("confidence", 0.0)

            # Jaccard Similarity
            union = expected_skills | predicted_skills
            intersection = expected_skills & predicted_skills
            jaccard = len(intersection) / len(union) if union else 1.0
            src_jaccards.append(jaccard)
            all_jaccards.append(jaccard)

            # Precision & Recall for this sample
            p = len(intersection) / len(predicted_skills) if predicted_skills else 0.0
            r = len(intersection) / len(expected_skills) if expected_skills else 0.0
            f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0

            all_precisions.append(p)
            all_recalls.append(r)
            all_f1s.append(f1)

            is_exact = (expected_skills == predicted_skills)
            if is_exact:
                src_exact += 1
                all_exact_matches.append(True)
            else:
                all_exact_matches.append(False)

            sample_records.append({
                "id": q_id,
                "source": source_name,
                "question": text[:90] + "..." if len(text) > 90 else text,
                "expected_skills": sorted(list(expected_skills)),
                "predicted_skills": sorted(list(predicted_skills)),
                "jaccard_similarity": round(jaccard, 3),
                "f1_score": round(f1, 3),
                "confidence": round(confidence, 3),
            })

        per_source_results[source_name] = {
            "samples": total,
            "mean_jaccard_similarity": round(float(np.mean(src_jaccards)), 4) if src_jaccards else 0.0,
            "exact_match_ratio": round(src_exact / total, 4) if total > 0 else 0.0,
        }

    return {
        "category": "B. Question skills",
        "model_evaluated": "QuestionSkillClassifier",
        "total_samples": len(all_jaccards),
        "mean_jaccard_similarity": round(float(np.mean(all_jaccards)), 4) if all_jaccards else 0.0,
        "mean_sample_precision": round(float(np.mean(all_precisions)), 4) if all_precisions else 0.0,
        "mean_sample_recall": round(float(np.mean(all_recalls)), 4) if all_recalls else 0.0,
        "mean_sample_f1": round(float(np.mean(all_f1s)), 4) if all_f1s else 0.0,
        "exact_match_ratio": round(float(np.mean(all_exact_matches)), 4) if all_exact_matches else 0.0,
        "per_source_breakdown": per_source_results,
        "sample_records": sample_records,
    }

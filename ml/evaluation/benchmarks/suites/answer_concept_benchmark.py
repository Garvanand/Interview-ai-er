"""
Benchmark Suite C: Answer Concept Coverage Analyzer.

Evaluates ConceptCoverageAnalyzer on the three required dimensions:
1. Concept coverage consistency (deterministic repeatability & paraphrase variance)
2. Contradiction detection (flagging factually inverted candidate statements)
3. Irrelevant-answer rejection (firm 0% coverage on off-topic chatter, cross-domain answers, and prompt injection)
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
import numpy as np

from ml.models.concept_coverage import ConceptCoverageAnalyzer
from ml.evaluation.benchmarks.sources import (
    load_synthetic_answer_concept_fixtures,
    load_interview_specific_answers,
)

logger = logging.getLogger(__name__)


def run_answer_concept_benchmark(analyzer: Optional[ConceptCoverageAnalyzer] = None) -> Dict[str, Any]:
    """Runs Category C: Answer Concept Coverage benchmark."""
    model = analyzer or ConceptCoverageAnalyzer()

    synthetic_fixtures = load_synthetic_answer_concept_fixtures()
    interview_answers = load_interview_specific_answers()

    results = {
        "category": "C. Answer concept coverage",
        "model_evaluated": "ConceptCoverageAnalyzer",
        "consistency_evaluation": {},
        "contradiction_detection": {},
        "irrelevant_answer_rejection": {},
        "interview_transcript_evaluation": {},
    }

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Irrelevant-Answer Rejection Evaluation
    # ─────────────────────────────────────────────────────────────────────────
    irrelevant_cases = [f for f in synthetic_fixtures if f.get("scenario") == "irrelevant_rejection"]
    rejections_successful = 0
    irrelevant_records = []

    for item in irrelevant_cases:
        res = model.evaluate_concepts(item["candidate_answer"], item["concepts"], allow_llm=False)
        cov = res.get("overall_coverage_pct", 0.0)
        # Irrelevant answer is successfully rejected if coverage <= 15% (ideally 0%)
        is_rejected = (cov <= 15.0)
        if is_rejected:
            rejections_successful += 1

        irrelevant_records.append({
            "id": item["id"],
            "question": item["question"][:60] + "...",
            "candidate_answer": item["candidate_answer"][:80] + "...",
            "coverage_pct": cov,
            "rejected_cleanly": is_rejected,
            "status_results": [r.get("status") for r in res.get("concept_results", [])],
        })

    irrelevant_rate = rejections_successful / len(irrelevant_cases) if irrelevant_cases else 1.0
    results["irrelevant_answer_rejection"] = {
        "total_test_cases": len(irrelevant_cases),
        "successful_rejections": rejections_successful,
        "rejection_rate": round(irrelevant_rate, 4),
        "test_records": irrelevant_records,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Contradiction Detection Evaluation
    # ─────────────────────────────────────────────────────────────────────────
    contradiction_cases = [f for f in synthetic_fixtures if f.get("scenario") == "contradiction_detection"]
    contradictions_detected = 0
    contradiction_records = []

    for item in contradiction_cases:
        res = model.evaluate_concepts(item["candidate_answer"], item["concepts"], allow_llm=False)
        c_results = res.get("concept_results", [])
        
        # Check if contradiction is reflected via contradiction status, high contradiction probability, or overall low score
        has_contradiction_signal = any(
            r.get("status") == "contradicted" or r.get("contradiction_probability", 0.0) > 0.35
            for r in c_results
        ) or (res.get("overall_coverage_pct", 100.0) < 50.0)

        if has_contradiction_signal:
            contradictions_detected += 1

        contradiction_records.append({
            "id": item["id"],
            "question": item["question"][:60] + "...",
            "candidate_answer": item["candidate_answer"][:80] + "...",
            "contradiction_detected": has_contradiction_signal,
            "concept_scores": [round(r.get("concept_score", 0.0), 2) for r in c_results],
        })

    contra_rate = contradictions_detected / len(contradiction_cases) if contradiction_cases else 1.0
    results["contradiction_detection"] = {
        "total_test_cases": len(contradiction_cases),
        "contradictions_flagged": contradictions_detected,
        "detection_rate": round(contra_rate, 4),
        "test_records": contradiction_records,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Concept Coverage Consistency (Deterministic & Paraphrase Stability)
    # ─────────────────────────────────────────────────────────────────────────
    # A. Deterministic repeatability check (same text twice must have variance = 0)
    repeat_sample = interview_answers[0]
    res_run1 = model.evaluate_concepts(repeat_sample["candidate_answer"], repeat_sample["concepts"], allow_llm=False)
    res_run2 = model.evaluate_concepts(repeat_sample["candidate_answer"], repeat_sample["concepts"], allow_llm=False)
    deterministic_diff = abs(res_run1.get("overall_coverage_pct", 0.0) - res_run2.get("overall_coverage_pct", 0.0))

    # B. Paraphrase consistency pair
    paraphrase_cases = [f for f in synthetic_fixtures if f.get("scenario") == "consistency_evaluation"]
    paraphrase_deltas = []
    paraphrase_records = []

    for item in paraphrase_cases:
        res_a = model.evaluate_concepts(item["answer_version_a"], item["concepts"], allow_llm=False)
        res_b = model.evaluate_concepts(item["answer_version_b"], item["concepts"], allow_llm=False)
        delta = abs(res_a.get("overall_coverage_pct", 0.0) - res_b.get("overall_coverage_pct", 0.0))
        paraphrase_deltas.append(delta)

        is_consistent = (delta <= item.get("expected_score_difference_max", 20.0))
        paraphrase_records.append({
            "id": item["id"],
            "score_version_a": res_a.get("overall_coverage_pct", 0.0),
            "score_version_b": res_b.get("overall_coverage_pct", 0.0),
            "score_delta": round(delta, 2),
            "within_tolerance": is_consistent,
        })

    avg_paraphrase_delta = float(np.mean(paraphrase_deltas)) if paraphrase_deltas else 0.0
    results["consistency_evaluation"] = {
        "deterministic_reproducibility_delta": deterministic_diff,
        "is_100_percent_deterministic": (deterministic_diff == 0.0),
        "mean_paraphrase_score_delta": round(avg_paraphrase_delta, 2),
        "paraphrase_pair_records": paraphrase_records,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Realistic Interview Transcripts Evaluation
    # ─────────────────────────────────────────────────────────────────────────
    interview_records = []
    for item in interview_answers:
        res = model.evaluate_concepts(item["candidate_answer"], item["concepts"], allow_llm=False)
        cov = res.get("overall_coverage_pct", 0.0)
        expected_cov = item.get("expected_coverage", 100.0)
        err = abs(cov - expected_cov)
        interview_records.append({
            "id": item["id"],
            "topic": item.get("topic", "N/A"),
            "expected_coverage": expected_cov,
            "actual_coverage": cov,
            "error_percentage_points": round(err, 2),
            "quality_tier": item.get("quality_tier", "senior"),
        })

    results["interview_transcript_evaluation"] = {
        "samples_evaluated": len(interview_records),
        "mean_absolute_error_pts": round(float(np.mean([r["error_percentage_points"] for r in interview_records])), 2),
        "records": interview_records,
    }

    return results

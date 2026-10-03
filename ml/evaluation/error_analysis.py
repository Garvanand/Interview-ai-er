"""
ML Error-Analysis Framework for Interview-ai-er.

Provides categorized failure mode detection, multi-class & multi-label confusion matrices,
per-class precision/recall/F1 metrics, hard-example mining, false positive/negative registries,
and confidence distribution analysis across all five pipeline models:
  1. QuestionDifficultyPredictor (beginner, intermediate, advanced)
  2. QuestionSkillClassifier (multi-label canonical skills)
  3. ConceptCoverageAnalyzer (covered, partially_covered, missing / contradiction)
  4. CodeDefectDetector (clean vs defective / risk bands)
  5. ItemResponseTheoryMasteryModel & BKTModel (ability estimation / knowledge tracing)
"""
from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


# =====================================================================
# 1. Error Category Taxonomy Definitions
# =====================================================================

class DifficultyFailureCategory(str, Enum):
    EASY_AS_MEDIUM = "easy_classified_as_medium"
    MEDIUM_AS_HARD = "medium_classified_as_hard"
    HARD_AS_EASY = "hard_classified_as_easy"
    MEDIUM_AS_EASY = "medium_classified_as_easy"
    HARD_AS_MEDIUM = "hard_classified_as_medium"
    EASY_AS_HARD = "easy_classified_as_hard"
    CORRECT = "correct"


class SkillFailureCategory(str, Enum):
    MISSED_SKILL = "missed_skill"          # False Negative
    INCORRECT_SKILL = "incorrect_skill"    # False Positive
    AMBIGUOUS_TAG = "ambiguous_tag"        # Borderline confidence between top candidate skills
    CORRECT = "correct"


class NLIFailureCategory(str, Enum):
    FALSE_ENTAILMENT = "false_entailment"          # Superficial buzzwords marked as covered
    FALSE_CONTRADICTION = "false_contradiction"    # Valid alternative/nuance marked contradictory
    PARTIAL_COVERAGE_ERRORS = "partial_coverage_errors"  # Inaccurate partial credit attribution
    CORRECT = "correct"


class CodeFailureCategory(str, Enum):
    FALSE_VULNERABILITY = "false_vulnerability"  # Clean code flagged as high risk / defective (FP)
    MISSED_DEFECT = "missed_defect"              # Real bug/defect overlooked (FN)
    CORRECT = "correct"


class MasteryFailureCategory(str, Enum):
    OVERESTIMATION = "overestimation"    # Ability estimated substantially higher than ground truth
    UNDERESTIMATION = "underestimation"  # Ability estimated substantially lower than ground truth
    CORRECT = "accurate_estimate"


# =====================================================================
# 2. Structured Analysis Data Classes
# =====================================================================

@dataclass
class PerClassMetrics:
    label: str
    precision: float
    recall: float
    f1_score: float
    support: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "support": int(self.support),
        }


@dataclass
class ConfusionMatrixResult:
    labels: List[str]
    matrix: List[List[int]]  # matrix[i][j] = true label i, predicted label j
    normalized_matrix: List[List[float]]

    def to_ascii_table(self, title: str = "Confusion Matrix") -> str:
        """Renders formatted ASCII table with row/col labels and counts."""
        col_w = max(12, max(len(str(lbl)) for lbl in self.labels) + 2)
        total_w = col_w * (len(self.labels) + 1) + 2
        lines = []
        lines.append(f"+- {title} " + "-" * max(0, total_w - len(title) - 5) + "+")
        
        # Header
        header = f"| {'True \\ Pred':<{col_w}}" + "".join(f"{str(l):^{col_w}}" for l in self.labels) + " |"
        lines.append(header)
        lines.append("+" + "-" * (total_w - 2) + "+")
        
        # Rows
        for i, row_label in enumerate(self.labels):
            row_str = f"| {str(row_label):<{col_w}}"
            for j in range(len(self.labels)):
                cnt = self.matrix[i][j]
                pct = self.normalized_matrix[i][j] * 100
                cell = f"{cnt} ({pct:.0f}%)" if cnt > 0 else "0 (0%)"
                row_str += f"{cell:^{col_w}}"
            row_str += " |"
            lines.append(row_str)
            
        lines.append("+" + "-" * (total_w - 2) + "+")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "labels": self.labels,
            "raw_matrix": self.matrix,
            "normalized_matrix": [[round(v, 4) for v in row] for row in self.normalized_matrix],
        }


@dataclass
class HardExample:
    example_id: str
    input_snippet: str
    true_label: Any
    predicted_label: Any
    confidence: float
    margin: float
    error_category: str
    root_cause_explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "example_id": self.example_id,
            "input_snippet": self.input_snippet,
            "true_label": self.true_label,
            "predicted_label": self.predicted_label,
            "confidence": round(self.confidence, 4),
            "margin": round(self.margin, 4),
            "error_category": self.error_category,
            "root_cause_explanation": self.root_cause_explanation,
        }


@dataclass
class ConfidenceDistribution:
    bin_edges: List[float]
    overall_counts: List[int]
    correct_counts: List[int]
    error_counts: List[int]
    mean_confidence_overall: float
    mean_confidence_correct: float
    mean_confidence_error: float
    calibration_gap: float  # difference between mean correct and mean error confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bin_edges": [round(b, 2) for b in self.bin_edges],
            "overall_counts": self.overall_counts,
            "correct_counts": self.correct_counts,
            "error_counts": self.error_counts,
            "mean_confidence_overall": round(self.mean_confidence_overall, 4),
            "mean_confidence_correct": round(self.mean_confidence_correct, 4),
            "mean_confidence_error": round(self.mean_confidence_error, 4),
            "calibration_gap": round(self.calibration_gap, 4),
        }


@dataclass
class ModelErrorReport:
    model_name: str
    model_alias: str
    total_samples: int
    accuracy_or_primary_metric: float
    macro_f1: float
    confusion_matrix: ConfusionMatrixResult
    per_class_metrics: Dict[str, PerClassMetrics]
    failure_category_counts: Dict[str, int]
    failure_cases: List[Dict[str, Any]]
    hard_examples: List[HardExample]
    false_positives: List[Dict[str, Any]]
    false_negatives: List[Dict[str, Any]]
    confidence_distribution: ConfidenceDistribution

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_alias": self.model_alias,
            "total_samples": self.total_samples,
            "primary_metric": round(self.accuracy_or_primary_metric, 4),
            "macro_f1": round(self.macro_f1, 4),
            "confusion_matrix": self.confusion_matrix.to_dict(),
            "per_class_metrics": {k: v.to_dict() for k, v in self.per_class_metrics.items()},
            "failure_category_counts": self.failure_category_counts,
            "failure_cases": self.failure_cases,
            "hard_examples": [h.to_dict() for h in self.hard_examples],
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "confidence_distribution": self.confidence_distribution.to_dict(),
        }


# =====================================================================
# 3. Statistical & Metric Calculation Helpers
# =====================================================================

def build_multiclass_confusion_matrix(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str]
) -> ConfusionMatrixResult:
    """Calculates N x N confusion matrix and row-normalized percentages."""
    label_to_idx = {lbl: i for i, lbl in enumerate(labels)}
    n = len(labels)
    matrix = [[0 for _ in range(n)] for _ in range(n)]

    for yt, yp in zip(y_true, y_pred):
        if yt in label_to_idx and yp in label_to_idx:
            matrix[label_to_idx[yt]][label_to_idx[yp]] += 1

    norm_matrix = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        row_sum = sum(matrix[i])
        for j in range(n):
            norm_matrix[i][j] = (matrix[i][j] / row_sum) if row_sum > 0 else 0.0

    return ConfusionMatrixResult(
        labels=list(labels),
        matrix=matrix,
        normalized_matrix=norm_matrix,
    )


def compute_per_class_metrics_from_matrix(
    conf_mat: ConfusionMatrixResult
) -> Dict[str, PerClassMetrics]:
    """Computes precision, recall, F1, and support for each class from confusion matrix."""
    n = len(conf_mat.labels)
    mat = conf_mat.matrix
    results = {}

    total_elements = sum(sum(row) for row in mat)

    for i, label in enumerate(conf_mat.labels):
        tp = mat[i][i]
        fn = sum(mat[i][j] for j in range(n) if j != i)
        fp = sum(mat[j][i] for j in range(n) if j != i)
        support = sum(mat[i])

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        results[label] = PerClassMetrics(
            label=label,
            precision=prec,
            recall=rec,
            f1_score=f1,
            support=support,
        )

    return results


def compute_confidence_distribution_metrics(
    confidences: Sequence[float],
    is_correct: Sequence[bool],
    num_bins: int = 10
) -> ConfidenceDistribution:
    """Builds binned confidence histogram comparing correct vs error predictions."""
    bins = np.linspace(0.0, 1.0, num_bins + 1).tolist()
    overall = [0] * num_bins
    correct = [0] * num_bins
    error = [0] * num_bins

    confs = np.array(confidences) if len(confidences) > 0 else np.array([0.0])
    flags = np.array(is_correct) if len(is_correct) > 0 else np.array([True])

    for c, flag in zip(confs, flags):
        # Clamp to [0.0, 0.9999] to find bin index
        idx = min(int(c * num_bins), num_bins - 1)
        idx = max(0, idx)
        overall[idx] += 1
        if flag:
            correct[idx] += 1
        else:
            error[idx] += 1

    correct_confs = confs[flags] if np.any(flags) else np.array([0.0])
    error_confs = confs[~flags] if np.any(~flags) else np.array([0.0])

    mean_all = float(np.mean(confs)) if len(confs) > 0 else 0.0
    mean_corr = float(np.mean(correct_confs)) if len(correct_confs) > 0 else 0.0
    mean_err = float(np.mean(error_confs)) if len(error_confs) > 0 else 0.0
    gap = mean_corr - mean_err

    return ConfidenceDistribution(
        bin_edges=bins,
        overall_counts=overall,
        correct_counts=correct,
        error_counts=error,
        mean_confidence_overall=mean_all,
        mean_confidence_correct=mean_corr,
        mean_confidence_error=mean_err,
        calibration_gap=gap,
    )


# =====================================================================
# 4. Model-Specific Error Analyzers
# =====================================================================

# ─────────────────────────────────────────────────────────────────────
# A. Question Difficulty Error Analyzer
# ─────────────────────────────────────────────────────────────────────

class DifficultyErrorAnalyzer:
    """
    Error analyzer for QuestionDifficultyPredictor.
    Exposes categorized failure modes:
      - easy_classified_as_medium
      - medium_classified_as_hard
      - hard_classified_as_easy
      - (and additional misclassification pairs)
    """

    DIFFICULTY_LABELS = ["beginner", "intermediate", "advanced"]

    def __init__(self, predictor=None):
        from ml.models.difficulty_predictor import QuestionDifficultyPredictor
        self.predictor = predictor or QuestionDifficultyPredictor()

    def get_benchmark_dataset(self) -> List[Dict[str, Any]]:
        """
        Curated benchmark containing standard interview questions alongside engineered
        edge-cases that trigger lexical, brevity, and complexity misclassifications.
        """
        return [
            # ── Standard Beginner ──
            {
                "id": "diff_beg_01",
                "question": "Write a function to check if a given integer is even or odd.",
                "expected": "beginner",
                "notes": "Classic elementary conditional arithmetic"
            },
            {
                "id": "diff_beg_02",
                "question": "Given an array of integers, return the sum of all elements.",
                "expected": "beginner",
                "notes": "Standard single-pass loop accumulator"
            },
            {
                "id": "diff_beg_03",
                "question": "Find the maximum number in a list of numbers without using max().",
                "expected": "beginner",
                "notes": "Fundamental comparison logic"
            },
            {
                "id": "diff_beg_04",
                "question": "Convert a temperature in Celsius to Fahrenheit.",
                "expected": "beginner",
                "notes": "Direct formula evaluation"
            },
            # ── Easy Classified as Medium (Failure Candidate) ──
            {
                "id": "diff_beg_as_med_01",
                "question": "Implement a basic loop to print numbers from 1 to 100 with O(1) space complexity and analyze its runtime efficiency.",
                "expected": "beginner",
                "notes": "Simple counting loop, but contains technical jargon 'complexity', 'space complexity', 'runtime efficiency'"
            },
            {
                "id": "diff_beg_as_med_02",
                "question": "Given a string of characters, determine if it contains any vowels using a boolean flag and pointer iteration.",
                "expected": "beginner",
                "notes": "Basic string search, but mentions 'pointer iteration' which triggers intermediate heuristics"
            },
            {
                "id": "diff_beg_as_med_03",
                "question": "Reverse a list of integers in place using an index swap technique.",
                "expected": "beginner",
                "notes": "Simple two-index swap; keyword models elevate to intermediate algorithms"
            },

            # ── Standard Intermediate ──
            {
                "id": "diff_int_01",
                "question": "Given a singly linked list, determine if it has a cycle using Floyd's Tortoise and Hare algorithm.",
                "expected": "intermediate",
                "notes": "Canonical LeetCode Medium two-pointer linked list pattern"
            },
            {
                "id": "diff_int_02",
                "question": "Validate whether a binary tree satisfies the Binary Search Tree invariant.",
                "expected": "intermediate",
                "notes": "Standard DFS/BFS range validation"
            },
            {
                "id": "diff_int_03",
                "question": "Group an array of anagrams together using a hash map key of sorted characters.",
                "expected": "intermediate",
                "notes": "Standard hash map + sorting technique"
            },
            {
                "id": "diff_int_04",
                "question": "Implement Breadth-First Search to find the shortest path in an unweighted grid with obstacles.",
                "expected": "intermediate",
                "notes": "Standard queue-based graph traversal"
            },
            # ── Medium Classified as Hard (Failure Candidate) ──
            {
                "id": "diff_med_as_hard_01",
                "question": "Find the length of the longest palindromic substring using dynamic programming or expand around centers with optimal substructure.",
                "expected": "intermediate",
                "notes": "Standard O(N^2) medium, but 'dynamic programming' and 'optimal substructure' trigger advanced models"
            },
            {
                "id": "diff_med_as_hard_02",
                "question": "Implement Dijkstra's shortest path algorithm using a min-heap priority queue on a weighted directed graph.",
                "expected": "intermediate",
                "notes": "Textbook undergraduate graph algorithm, heavily elevated to hard due to 'Dijkstra', 'min-heap priority queue'"
            },
            {
                "id": "diff_med_as_hard_03",
                "question": "Design an LRU Cache with O(1) get and put operations using a doubly linked list and hash map.",
                "expected": "intermediate",
                "notes": "Standard interview classic; 'Design' and 'O(1) double linked list' often cause hard classification"
            },

            # ── Standard Advanced ──
            {
                "id": "diff_adv_01",
                "question": "Design a distributed consensus protocol capable of surviving network partitions using Raft or Paxos with leader election.",
                "expected": "advanced",
                "notes": "High-complexity distributed systems architecture"
            },
            {
                "id": "diff_adv_02",
                "question": "Implement a persistent Red-Black Tree supporting historical version queries in O(log n) time per update.",
                "expected": "advanced",
                "notes": "Advanced persistent data structures"
            },
            {
                "id": "diff_adv_03",
                "question": "Solve the Traveling Salesperson Problem on N cities using dynamic programming with bitmasking in O(n^2 2^n).",
                "expected": "advanced",
                "notes": "NP-hard exponential DP with bitmasking"
            },
            # ── Hard Classified as Easy (Failure Candidate) ──
            {
                "id": "diff_hard_as_easy_01",
                "question": "Nim Game: Given n stones, you take turns removing 1 to 3 stones. Return true if you can win.",
                "expected": "advanced",
                "notes": "Mathematical game theory / invariant proof. Extreme brevity (1 short sentence) tricks models into beginner"
            },
            {
                "id": "diff_hard_as_easy_02",
                "question": "Find the n-th ugly number whose prime factors are limited to 2, 3, and 5.",
                "expected": "advanced",
                "notes": "Multi-pointer min-heap / DP number theory. Brevity and lack of jargon fools bag-of-words into easy"
            },
            {
                "id": "diff_hard_as_easy_03",
                "question": "Stone Game: Alice and Bob take stones from ends. Predict if first player always wins.",
                "expected": "advanced",
                "notes": "Deceptively short minimax dynamic programming / parity proof"
            },
        ]

    def analyze(self, dataset: Optional[List[Dict[str, Any]]] = None) -> ModelErrorReport:
        data = dataset or self.get_benchmark_dataset()

        y_true = []
        y_pred = []
        confidences = []
        is_correct_list = []
        failure_cases = []
        hard_examples = []
        false_positives = []
        false_negatives = []

        cat_counts = {cat.value: 0 for cat in DifficultyFailureCategory}

        for item in data:
            q_id = item.get("id", "unknown")
            text = item["question"]
            expected = item["expected"].lower()

            res = self.predictor.predict(text, allow_llm=False)
            predicted = res.get("difficulty", "intermediate").lower()
            probs = res.get("probabilities", {})
            confidence = res.get("confidence", 0.0)

            # Sort probabilities to measure margin
            prob_values = sorted(probs.values(), reverse=True)
            top_prob = prob_values[0] if len(prob_values) > 0 else confidence
            second_prob = prob_values[1] if len(prob_values) > 1 else 0.0
            margin = top_prob - second_prob

            y_true.append(expected)
            y_pred.append(predicted)
            confidences.append(confidence)

            is_correct = (predicted == expected)
            is_correct_list.append(is_correct)

            # Categorize failure
            category = DifficultyFailureCategory.CORRECT.value
            if not is_correct:
                if expected == "beginner" and predicted == "intermediate":
                    category = DifficultyFailureCategory.EASY_AS_MEDIUM.value
                elif expected == "intermediate" and predicted == "advanced":
                    category = DifficultyFailureCategory.MEDIUM_AS_HARD.value
                elif expected == "advanced" and predicted == "beginner":
                    category = DifficultyFailureCategory.HARD_AS_EASY.value
                elif expected == "intermediate" and predicted == "beginner":
                    category = DifficultyFailureCategory.MEDIUM_AS_EASY.value
                elif expected == "advanced" and predicted == "intermediate":
                    category = DifficultyFailureCategory.HARD_AS_MEDIUM.value
                elif expected == "beginner" and predicted == "advanced":
                    category = DifficultyFailureCategory.EASY_AS_HARD.value

                cat_counts[category] += 1

                err_entry = {
                    "id": q_id,
                    "question": text,
                    "expected": expected,
                    "predicted": predicted,
                    "category": category,
                    "confidence": round(confidence, 4),
                    "probabilities": {k: round(v, 4) for k, v in probs.items()},
                    "notes": item.get("notes", ""),
                }
                failure_cases.append(err_entry)

                # Record false positives/negatives for per-class diagnostics
                false_positives.append({
                    "class": predicted,
                    "true_class": expected,
                    "question": text[:80] + "...",
                    "confidence": confidence,
                    "category": category
                })
                false_negatives.append({
                    "class": expected,
                    "predicted_class": predicted,
                    "question": text[:80] + "...",
                    "confidence": confidence,
                    "category": category
                })

                # Hard example selection: either high confidence error or narrow margin
                hard_examples.append(HardExample(
                    example_id=q_id,
                    input_snippet=text,
                    true_label=expected,
                    predicted_label=predicted,
                    confidence=confidence,
                    margin=margin,
                    error_category=category,
                    root_cause_explanation=(
                        f"Mismatched complexity expectations: {category}. "
                        f"Expected {expected}, predicted {predicted} (prob={top_prob:.2f}, margin={margin:.2f}). "
                        f"Context: {item.get('notes', '')}"
                    )
                ))
            else:
                cat_counts[DifficultyFailureCategory.CORRECT.value] += 1
                # Borderline correct predictions can also be hard examples
                if margin < 0.15 and len(prob_values) > 1:
                    hard_examples.append(HardExample(
                        example_id=q_id,
                        input_snippet=text,
                        true_label=expected,
                        predicted_label=predicted,
                        confidence=confidence,
                        margin=margin,
                        error_category="borderline_correct",
                        root_cause_explanation=f"Correct but low margin ({margin:.2f}) between top classes."
                    ))

        # Confusion matrix
        conf_mat = build_multiclass_confusion_matrix(y_true, y_pred, self.DIFFICULTY_LABELS)
        per_class = compute_per_class_metrics_from_matrix(conf_mat)
        conf_dist = compute_confidence_distribution_metrics(confidences, is_correct_list)

        acc = sum(1 for c in is_correct_list if c) / len(is_correct_list) if is_correct_list else 0.0
        macro_f1 = float(np.mean([m.f1_score for m in per_class.values()]))

        return ModelErrorReport(
            model_name="QuestionDifficultyPredictor",
            model_alias="question-difficulty-v1",
            total_samples=len(data),
            accuracy_or_primary_metric=acc,
            macro_f1=macro_f1,
            confusion_matrix=conf_mat,
            per_class_metrics=per_class,
            failure_category_counts=cat_counts,
            failure_cases=failure_cases,
            hard_examples=hard_examples,
            false_positives=false_positives,
            false_negatives=false_negatives,
            confidence_distribution=conf_dist,
        )


# ─────────────────────────────────────────────────────────────────────
# B. Question Skill Classifier Error Analyzer
# ─────────────────────────────────────────────────────────────────────

class SkillTaggerErrorAnalyzer:
    """
    Error analyzer for QuestionSkillClassifier (Multi-label).
    Exposes categorized failure modes:
      - missed_skill (False Negative)
      - incorrect_skill (False Positive)
      - ambiguous_tag (Low-margin or high-entropy split across skills)
    """

    CORE_SKILLS = [
        "arrays", "hashing", "strings", "trees", "graphs",
        "dynamic_programming", "two_pointers", "sliding_window",
        "binary_search", "heaps", "recursion", "complexity"
    ]

    def __init__(self, classifier=None):
        from ml.models.skill_classifier import QuestionSkillClassifier
        self.classifier = classifier or QuestionSkillClassifier()

    def get_benchmark_dataset(self) -> List[Dict[str, Any]]:
        """
        Benchmark dataset covering unambiguous skill cases, multi-skill combinations,
        and deceptive phrasing where keywords mislead the classifier.
        """
        return [
            # ── Standard Single & Multi-skill ──
            {
                "id": "skill_01",
                "question": "Implement an algorithm to traverse a binary search tree in post-order and level-order.",
                "expected_skills": ["trees", "recursion"],
                "notes": "Unambiguous tree structure"
            },
            {
                "id": "skill_02",
                "question": "Given an array of strings, group anagrams together using character frequency counts in a hash table.",
                "expected_skills": ["strings", "hashing", "arrays"],
                "notes": "Multi-skill hashing and string processing"
            },
            {
                "id": "skill_03",
                "question": "Find the shortest path in a weighted graph using Dijkstra's algorithm with a priority queue.",
                "expected_skills": ["graphs", "heaps"],
                "notes": "Classic graph and heap pairing"
            },
            {
                "id": "skill_04",
                "question": "Find the maximum subarray sum using Kadane's dynamic programming algorithm.",
                "expected_skills": ["dynamic_programming", "arrays"],
                "notes": "1D dynamic programming on arrays"
            },

            # ── Missed Skill (False Negative Candidates) ──
            {
                "id": "skill_missed_01",
                "question": "Given a sorted array of distinct integers, find two numbers that sum up to target without using extra memory.",
                "expected_skills": ["arrays", "two_pointers", "binary_search"],
                "notes": "Often model tags 'arrays' but misses 'two_pointers' or 'binary_search' because explicit pointer words are minimal"
            },
            {
                "id": "skill_missed_02",
                "question": "Find the length of the longest substring without any repeating characters.",
                "expected_skills": ["strings", "sliding_window", "hashing"],
                "notes": "Model frequently detects 'strings' but misses 'sliding_window' without explicit window keyword"
            },
            {
                "id": "skill_missed_03",
                "question": "Find the median of two sorted arrays of different sizes in O(log(min(n, m))) time.",
                "expected_skills": ["arrays", "binary_search", "complexity"],
                "notes": "Requires binary search partition, but model often misses binary_search when array is primary"
            },

            # ── Incorrect Skill (False Positive Candidates) ──
            {
                "id": "skill_inc_01",
                "question": "Explain how garbage collection in the Java Virtual Machine marks and sweeps unreferenced object trees in memory.",
                "expected_skills": ["complexity"],
                "notes": "Mentions 'trees', causing incorrect prediction of data_structures 'trees'"
            },
            {
                "id": "skill_inc_02",
                "question": "Visualize latency distributions by plotting a dependency graph of microservice telemetry metrics.",
                "expected_skills": ["complexity"],
                "notes": "Mentions 'graph' metaphorically / charting, causing incorrect algorithmic 'graphs' tag"
            },
            {
                "id": "skill_inc_03",
                "question": "Implement an API rate limiter using a sliding window counter algorithm stored in Redis.",
                "expected_skills": ["hashing"],
                "notes": "Mentions 'sliding window', which incorrectly triggers algorithm sliding_window rather than systems hashing"
            },

            # ── Ambiguous Tag (Low Margin / Overlapping Boundaries) ──
            {
                "id": "skill_amb_01",
                "question": "Generate all valid subsets of a set of integers without duplicates.",
                "expected_skills": ["backtracking", "recursion"],
                "notes": "Borderline overlap between backtracking, recursion, and dynamic_programming"
            },
            {
                "id": "skill_amb_02",
                "question": "Container With Most Water: Find two lines that together with the x-axis form a container containing the most water.",
                "expected_skills": ["two_pointers", "arrays", "greedy"],
                "notes": "Multi-skill crossover between arrays, two_pointers, and greedy choices"
            },
            {
                "id": "skill_amb_03",
                "question": "Find all bridge edges and articulation vertices in an undirected communication network.",
                "expected_skills": ["graphs", "recursion"],
                "notes": "Tarjan's DFS bridge algorithm: DFS recursion vs graph connectivity ambiguity"
            },
        ]

    def analyze(self, dataset: Optional[List[Dict[str, Any]]] = None) -> ModelErrorReport:
        data = dataset or self.get_benchmark_dataset()

        # Track per-skill binary classifications for confusion matrix
        skill_stats = {s: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for s in self.CORE_SKILLS}
        confidences = []
        is_correct_list = []
        failure_cases = []
        hard_examples = []
        false_positives = []
        false_negatives = []

        cat_counts = {cat.value: 0 for cat in SkillFailureCategory}

        for item in data:
            q_id = item.get("id", "unknown")
            text = item["question"]
            expected_set = set(item.get("expected_skills", []))

            res = self.classifier.predict(text, threshold=0.25, top_k=4)
            pred_skills_dicts = res.get("skills", [])
            pred_set = set(res.get("top_skills", []))
            confidence = res.get("confidence", 0.0)
            confidences.append(confidence)

            # Check margin between top 1 and top 2 predictions
            top_scores = [s.get("confidence", 0.0) for s in pred_skills_dicts]
            top_scores.sort(reverse=True)
            margin = (top_scores[0] - top_scores[1]) if len(top_scores) > 1 else top_scores[0] if top_scores else 0.0

            # Compute set intersection
            tp_set = expected_set & pred_set
            fp_set = pred_set - expected_set
            fn_set = expected_set - pred_set

            # Fully correct multi-label definition: Jaccard similarity >= 0.5 and no gross false positives
            is_perfect = (len(fp_set) == 0 and len(fn_set) == 0)
            is_acceptable = (len(tp_set) > 0 and len(fp_set) <= 1)
            is_correct_list.append(is_acceptable)

            # Update per-skill matrix
            for s in self.CORE_SKILLS:
                in_true = s in expected_set
                in_pred = s in pred_set
                if in_true and in_pred:
                    skill_stats[s]["tp"] += 1
                elif not in_true and in_pred:
                    skill_stats[s]["fp"] += 1
                elif in_true and not in_pred:
                    skill_stats[s]["fn"] += 1
                else:
                    skill_stats[s]["tn"] += 1

            # Categorize failures
            item_categories = []
            if len(fn_set) > 0:
                cat_counts[SkillFailureCategory.MISSED_SKILL.value] += 1
                item_categories.append(SkillFailureCategory.MISSED_SKILL.value)
                for fn_s in fn_set:
                    false_negatives.append({
                        "id": q_id,
                        "skill": fn_s,
                        "question": text[:80] + "...",
                        "predicted_skills": list(pred_set),
                        "reason": f"Expected skill '{fn_s}' was omitted."
                    })

            if len(fp_set) > 0:
                cat_counts[SkillFailureCategory.INCORRECT_SKILL.value] += 1
                item_categories.append(SkillFailureCategory.INCORRECT_SKILL.value)
                for fp_s in fp_set:
                    false_positives.append({
                        "id": q_id,
                        "skill": fp_s,
                        "question": text[:80] + "...",
                        "expected_skills": list(expected_set),
                        "reason": f"Predicted skill '{fp_s}' was not in ground truth."
                    })

            # Check ambiguous tag
            if margin < 0.12 and len(top_scores) > 1:
                cat_counts[SkillFailureCategory.AMBIGUOUS_TAG.value] += 1
                item_categories.append(SkillFailureCategory.AMBIGUOUS_TAG.value)

            if is_perfect:
                cat_counts[SkillFailureCategory.CORRECT.value] += 1

            if item_categories:
                failure_cases.append({
                    "id": q_id,
                    "question": text,
                    "expected_skills": list(expected_set),
                    "predicted_skills": list(pred_set),
                    "categories": item_categories,
                    "confidence": round(confidence, 4),
                    "margin": round(margin, 4),
                    "notes": item.get("notes", ""),
                })
                hard_examples.append(HardExample(
                    example_id=q_id,
                    input_snippet=text,
                    true_label=list(expected_set),
                    predicted_label=list(pred_set),
                    confidence=confidence,
                    margin=margin,
                    error_category="; ".join(item_categories),
                    root_cause_explanation=(
                        f"Multi-label mismatch. Missed: {list(fn_set)}; Extra: {list(fp_set)}. "
                        f"Margin={margin:.2f}. Notes: {item.get('notes', '')}"
                    )
                ))

        # Build Per-Class Metrics across skills
        per_class = {}
        for s in self.CORE_SKILLS:
            st = skill_stats[s]
            tp, fp, fn = st["tp"], st["fp"], st["fn"]
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
            supp = tp + fn
            per_class[s] = PerClassMetrics(
                label=s,
                precision=prec,
                recall=rec,
                f1_score=f1,
                support=supp,
            )

        # Macro confusion matrix representing aggregate TP/FP/FN/TN
        agg_tp = sum(skill_stats[s]["tp"] for s in self.CORE_SKILLS)
        agg_fp = sum(skill_stats[s]["fp"] for s in self.CORE_SKILLS)
        agg_fn = sum(skill_stats[s]["fn"] for s in self.CORE_SKILLS)
        agg_tn = sum(skill_stats[s]["tn"] for s in self.CORE_SKILLS)

        matrix = [
            [agg_tp, agg_fn],
            [agg_fp, agg_tn],
        ]
        norm_matrix = [
            [agg_tp / (agg_tp + agg_fn) if (agg_tp + agg_fn) > 0 else 0.0,
             agg_fn / (agg_tp + agg_fn) if (agg_tp + agg_fn) > 0 else 0.0],
            [agg_fp / (agg_fp + agg_tn) if (agg_fp + agg_tn) > 0 else 0.0,
             agg_tn / (agg_fp + agg_tn) if (agg_fp + agg_tn) > 0 else 0.0],
        ]
        conf_mat = ConfusionMatrixResult(
            labels=["Skill_Present", "Skill_Absent"],
            matrix=matrix,
            normalized_matrix=norm_matrix,
        )

        conf_dist = compute_confidence_distribution_metrics(confidences, is_correct_list)
        macro_f1 = float(np.mean([m.f1_score for m in per_class.values()]))
        acc = sum(1 for c in is_correct_list if c) / len(is_correct_list) if is_correct_list else 0.0

        return ModelErrorReport(
            model_name="QuestionSkillClassifier",
            model_alias="question-skill-v1",
            total_samples=len(data),
            accuracy_or_primary_metric=acc,
            macro_f1=macro_f1,
            confusion_matrix=conf_mat,
            per_class_metrics=per_class,
            failure_category_counts=cat_counts,
            failure_cases=failure_cases,
            hard_examples=hard_examples,
            false_positives=false_positives,
            false_negatives=false_negatives,
            confidence_distribution=conf_dist,
        )


# ─────────────────────────────────────────────────────────────────────
# C. NLI Answer Concept Coverage Error Analyzer
# ─────────────────────────────────────────────────────────────────────

class NLIAnswerAnalyzerErrorAnalyzer:
    """
    Error analyzer for ConceptCoverageAnalyzer (DeBERTa-v3 NLI + MiniLM).
    Exposes categorized failure modes:
      - false_entailment (Buzzwords / circular statements erroneously marked covered)
      - false_contradiction (Valid alternative phrasings or caveats flagged as contradiction)
      - partial_coverage_errors (Incomplete definition misgraded as complete or zero)
    """

    COVERAGE_CLASSES = ["covered", "partially_covered", "missing"]

    def __init__(self, analyzer=None):
        from ml.models.concept_coverage import ConceptCoverageAnalyzer
        self.analyzer = analyzer or ConceptCoverageAnalyzer()

    def get_benchmark_dataset(self) -> List[Dict[str, Any]]:
        """
        Benchmark containing genuine explanations, superficial buzzword circularity,
        and subtle engineering caveats.
        """
        return [
            # ── Standard Correct Coverage ──
            {
                "id": "nli_good_01",
                "question": "What is the role of a replica set in MongoDB?",
                "concepts": ["High availability", "Data redundancy", "Automatic failover"],
                "answer": "A replica set in MongoDB provides high availability and data redundancy by maintaining multiple copies of data on different nodes with automatic failover.",
                "expected_status": {"High availability": "covered", "Data redundancy": "covered", "Automatic failover": "covered"},
                "expected_overall": 100.0,
                "notes": "Clear, complete technical explanation"
            },
            {
                "id": "nli_good_02",
                "question": "How does virtual memory protect processes?",
                "concepts": ["Address space isolation", "Page tables", "Hardware translation"],
                "answer": "It isolates process address spaces so one process cannot access another's memory.",
                "expected_status": {"Address space isolation": "covered", "Page tables": "missing", "Hardware translation": "missing"},
                "expected_overall": 33.3,
                "notes": "Accurate partial explanation with clear missing items"
            },

            # ── False Entailment (Superficial buzzwords / repetition) ──
            {
                "id": "nli_false_ent_01",
                "question": "Explain how database indexing accelerates query execution.",
                "concepts": ["B-Tree balanced search", "Disk block I/O reduction"],
                "answer": "Database indexing accelerates queries by indexing the table and using an index for fast execution without scanning everything.",
                "expected_status": {"B-Tree balanced search": "missing", "Disk block I/O reduction": "missing"},
                "expected_overall": 0.0,
                "failure_type": NLIFailureCategory.FALSE_ENTAILMENT.value,
                "notes": "Pure tautology. Never explains B-Trees or disk I/O, but lexical overlap can trigger false entailment."
            },
            {
                "id": "nli_false_ent_02",
                "question": "How does TLS/HTTPS provide confidentiality?",
                "concepts": ["Asymmetric key exchange", "Symmetric session encryption"],
                "answer": "HTTPS is confidential because it encrypts the communication securely across the network so nobody can intercept it.",
                "expected_status": {"Asymmetric key exchange": "missing", "Symmetric session encryption": "missing"},
                "expected_overall": 0.0,
                "failure_type": NLIFailureCategory.FALSE_ENTAILMENT.value,
                "notes": "Restates the word 'encrypts securely' without mentioning asymmetric handshake or symmetric session cipher."
            },

            # ── False Contradiction (Valid nuance or negation phrasing) ──
            {
                "id": "nli_false_contra_01",
                "question": "What is the average time complexity of Quicksort?",
                "concepts": ["O(n log n) expected time", "Pivot partition"],
                "answer": "Quicksort runs in expected O(n log n) time on average; however, if you choose a bad pivot on an already sorted list, it will not achieve O(n log n) and instead degrade to O(n^2).",
                "expected_status": {"O(n log n) expected time": "covered", "Pivot partition": "covered"},
                "expected_overall": 100.0,
                "failure_type": NLIFailureCategory.FALSE_CONTRADICTION.value,
                "notes": "Phrasing 'it will not achieve O(n log n) and instead degrade' contains negation that NLI can confuse for contradiction."
            },
            {
                "id": "nli_false_contra_02",
                "question": "How do HTTP/2 connections operate differently from HTTP/1.1?",
                "concepts": ["Single persistent TCP connection", "Binary stream multiplexing"],
                "answer": "Unlike HTTP/1.1 where browsers opened 6 separate TCP connections, HTTP/2 does not open multiple TCP sockets per origin; it multiplexes streams over one TCP pipe.",
                "expected_status": {"Single persistent TCP connection": "covered", "Binary stream multiplexing": "covered"},
                "expected_overall": 100.0,
                "failure_type": NLIFailureCategory.FALSE_CONTRADICTION.value,
                "notes": "'does not open multiple TCP sockets' is a negative assertion that models frequently classify as contradiction."
            },

            # ── Partial Coverage Errors (Drift / Attribution failures) ──
            {
                "id": "nli_partial_01",
                "question": "Explain the ACID properties of relational databases.",
                "concepts": ["Atomicity", "Consistency", "Isolation", "Durability"],
                "answer": "Atomicity means the transaction happens completely or aborts. Consistency guarantees integrity constraints hold.",
                "expected_status": {"Atomicity": "covered", "Consistency": "covered", "Isolation": "missing", "Durability": "missing"},
                "expected_overall": 50.0,
                "failure_type": NLIFailureCategory.PARTIAL_COVERAGE_ERRORS.value,
                "notes": "Explains 2 of 4 concepts; models sometimes inflate coverage to 75% or conflate consistency with durability."
            },
            {
                "id": "nli_partial_02",
                "question": "What are the core components of Kubernetes architecture?",
                "concepts": ["Kubelet agent", "Control Plane API Server", "etcd state store", "Kube-proxy network routing"],
                "answer": "Kubernetes has an API server in the control plane that schedules pods, and kubelet runs as an agent on each node.",
                "expected_status": {"Kubelet agent": "covered", "Control Plane API Server": "covered", "etcd state store": "missing", "Kube-proxy network routing": "missing"},
                "expected_overall": 50.0,
                "failure_type": NLIFailureCategory.PARTIAL_COVERAGE_ERRORS.value,
                "notes": "Covers control plane and kubelet; etcd and kube-proxy are completely omitted."
            },
        ]

    def analyze(self, dataset: Optional[List[Dict[str, Any]]] = None) -> ModelErrorReport:
        data = dataset or self.get_benchmark_dataset()

        y_true_concept_status = []
        y_pred_concept_status = []
        confidences = []
        is_correct_list = []
        failure_cases = []
        hard_examples = []
        false_positives = []
        false_negatives = []

        cat_counts = {cat.value: 0 for cat in NLIFailureCategory}

        for item in data:
            q_id = item.get("id", "unknown")
            answer = item["answer"]
            concepts = item["concepts"]
            expected_status = item["expected_status"]

            res = self.analyzer.evaluate_concepts(answer, concepts, allow_llm=False)
            concept_results = res.get("concept_results", [])
            overall_pct = res.get("overall_coverage_pct", 0.0)
            confidence = res.get("confidence", 0.0)
            confidences.append(confidence)

            # Map predicted statuses
            pred_map = {cr["concept"]: cr.get("status", "missing") for cr in concept_results}

            case_has_error = False
            item_categories = []

            for c in concepts:
                exp_st = expected_status.get(c, "missing")
                pred_st = pred_map.get(c, "missing")

                # Normalize statuses into 3 classes: covered, partially_covered, missing
                if pred_st in ("covered", "entailment"):
                    p_norm = "covered"
                elif pred_st in ("partial", "partially_covered"):
                    p_norm = "partially_covered"
                elif pred_st in ("contradicted", "contradiction"):
                    p_norm = "contradiction"
                else:
                    p_norm = "missing"

                e_norm = exp_st if exp_st in self.COVERAGE_CLASSES else "missing"

                y_true_concept_status.append(e_norm)
                y_pred_concept_status.append(p_norm if p_norm != "contradiction" else "missing")

                if e_norm != p_norm:
                    case_has_error = True
                    # Check failure type
                    if e_norm == "missing" and p_norm in ("covered", "partially_covered"):
                        cat = NLIFailureCategory.FALSE_ENTAILMENT.value
                        cat_counts[cat] += 1
                        item_categories.append(cat)
                        false_positives.append({
                            "id": q_id,
                            "concept": c,
                            "expected": e_norm,
                            "predicted": p_norm,
                            "answer_snippet": answer[:70] + "...",
                            "category": cat
                        })
                    elif pred_st in ("contradicted", "contradiction") and e_norm != "contradiction":
                        cat = NLIFailureCategory.FALSE_CONTRADICTION.value
                        cat_counts[cat] += 1
                        item_categories.append(cat)
                        false_negatives.append({
                            "id": q_id,
                            "concept": c,
                            "expected": e_norm,
                            "predicted": "contradiction",
                            "answer_snippet": answer[:70] + "...",
                            "category": cat
                        })
                    elif e_norm != p_norm:
                        cat = NLIFailureCategory.PARTIAL_COVERAGE_ERRORS.value
                        cat_counts[cat] += 1
                        item_categories.append(cat)

            is_correct = not case_has_error
            is_correct_list.append(is_correct)

            if not is_correct:
                failure_cases.append({
                    "id": q_id,
                    "question": item["question"],
                    "answer": answer,
                    "expected_overall": item["expected_overall"],
                    "actual_overall": overall_pct,
                    "categories": list(set(item_categories)),
                    "concept_details": concept_results,
                    "confidence": round(confidence, 4),
                    "notes": item.get("notes", ""),
                })
                hard_examples.append(HardExample(
                    example_id=q_id,
                    input_snippet=f"Q: {item['question']} | Ans: {answer}",
                    true_label=expected_status,
                    predicted_label=pred_map,
                    confidence=confidence,
                    margin=abs(overall_pct - item["expected_overall"]) / 100.0,
                    error_category="; ".join(set(item_categories)),
                    root_cause_explanation=(
                        f"NLI grading discrepancy. Expected {item['expected_overall']}%, got {overall_pct}%. "
                        f"Categories: {set(item_categories)}. Notes: {item.get('notes', '')}"
                    )
                ))
            else:
                cat_counts[NLIFailureCategory.CORRECT.value] += 1

        # Build confusion matrix across concept statuses
        conf_mat = build_multiclass_confusion_matrix(
            y_true_concept_status,
            y_pred_concept_status,
            self.COVERAGE_CLASSES
        )
        per_class = compute_per_class_metrics_from_matrix(conf_mat)
        conf_dist = compute_confidence_distribution_metrics(confidences, is_correct_list)

        acc = sum(1 for c in is_correct_list if c) / len(is_correct_list) if is_correct_list else 0.0
        macro_f1 = float(np.mean([m.f1_score for m in per_class.values()]))

        return ModelErrorReport(
            model_name="ConceptCoverageAnalyzer",
            model_alias="answer-nli-v1",
            total_samples=len(data),
            accuracy_or_primary_metric=acc,
            macro_f1=macro_f1,
            confusion_matrix=conf_mat,
            per_class_metrics=per_class,
            failure_category_counts=cat_counts,
            failure_cases=failure_cases,
            hard_examples=hard_examples,
            false_positives=false_positives,
            false_negatives=false_negatives,
            confidence_distribution=conf_dist,
        )


# ─────────────────────────────────────────────────────────────────────
# D. Code Defect & Risk Error Analyzer
# ─────────────────────────────────────────────────────────────────────

class CodeDefectErrorAnalyzer:
    """
    Error analyzer for CodeDefectDetector.
    Exposes categorized failure modes:
      - false_vulnerability (Clean/safe code flagged as defective/high-risk, FP)
      - missed_defect (Real runtime bug/vulnerability overlooked, FN)
    """

    DEFECT_LABELS = ["clean", "defective"]

    def __init__(self, detector=None):
        from ml.models.defect_detector import CodeDefectDetector
        self.detector = detector or CodeDefectDetector()

    def get_benchmark_dataset(self) -> List[Dict[str, Any]]:
        """
        Benchmark code samples containing clean idiomatic code, intentional defensive checks,
        and subtle defects (off-by-one, mutable defaults, unhandled exceptions).
        """
        return [
            # ── Standard Clean Code ──
            {
                "id": "code_clean_01",
                "code": "def add_numbers(a: int, b: int) -> int:\n    return a + b",
                "expected": "clean",
                "notes": "Pure basic arithmetic"
            },
            {
                "id": "code_clean_02",
                "code": "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1",
                "expected": "clean",
                "notes": "Standard correct binary search"
            },

            # ── False Vulnerability Candidates (Clean code falsely flagged) ──
            {
                "id": "code_false_vuln_01",
                "code": "def safe_divide(numerator: float, denominator: float) -> float:\n    if denominator == 0:\n        raise ValueError('Denominator cannot be zero')\n    return numerator / denominator",
                "expected": "clean",
                "failure_type": CodeFailureCategory.FALSE_VULNERABILITY.value,
                "notes": "Guarded division. Contains 'raise ValueError' and '/' which naive tokenizers flag as high risk"
            },
            {
                "id": "code_false_vuln_02",
                "code": "def get_first_item(items: list):\n    return items[0] if items else None",
                "expected": "clean",
                "failure_type": CodeFailureCategory.FALSE_VULNERABILITY.value,
                "notes": "Defensive list indexing with ternary check. Substring 'items[0]' triggers false positive"
            },
            {
                "id": "code_false_vuln_03",
                "code": "def read_configuration(filepath: str) -> str:\n    with open(filepath, 'r', encoding='utf-8') as f:\n        return f.read()",
                "expected": "clean",
                "failure_type": CodeFailureCategory.FALSE_VULNERABILITY.value,
                "notes": "Idiomatic safe context manager. File I/O triggers defect heuristics"
            },

            # ── Standard Obvious Defect ──
            {
                "id": "code_defect_01",
                "code": "def divide(a, b):\n    return a / b",
                "expected": "defective",
                "notes": "Missing zero-division check"
            },
            {
                "id": "code_defect_02",
                "code": "def fetch_element(lst, idx):\n    return lst[idx]",
                "expected": "defective",
                "notes": "Missing bounds check"
            },

            # ── Missed Defect Candidates (Real bugs overlooked) ──
            {
                "id": "code_missed_01",
                "code": "def print_pairs(arr):\n    for i in range(len(arr)):\n        print(arr[i], arr[i + 1])",
                "expected": "defective",
                "failure_type": CodeFailureCategory.MISSED_DEFECT.value,
                "notes": "Off-by-one error: arr[i + 1] causes IndexError on last iteration. Often missed by AST heuristics"
            },
            {
                "id": "code_missed_02",
                "code": "def append_to_cache(item, cache=[]):\n    cache.append(item)\n    return cache",
                "expected": "defective",
                "failure_type": CodeFailureCategory.MISSED_DEFECT.value,
                "notes": "Mutable default argument creates shared persistent state across calls."
            },
            {
                "id": "code_missed_03",
                "code": "def write_log(filename, message):\n    f = open(filename, 'a')\n    f.write(message + '\\n')\n    # f is never closed, leading to file descriptor leak",
                "expected": "defective",
                "failure_type": CodeFailureCategory.MISSED_DEFECT.value,
                "notes": "Resource leak: file handle left unclosed."
            },
        ]

    def analyze(self, dataset: Optional[List[Dict[str, Any]]] = None) -> ModelErrorReport:
        data = dataset or self.get_benchmark_dataset()

        y_true = []
        y_pred = []
        confidences = []
        is_correct_list = []
        failure_cases = []
        hard_examples = []
        false_positives = []
        false_negatives = []

        cat_counts = {cat.value: 0 for cat in CodeFailureCategory}

        for item in data:
            q_id = item.get("id", "unknown")
            code = item["code"]
            expected = item["expected"].lower()

            res = self.detector.analyze_code(code, allow_llm=False)
            prob = res.get("defect_probability", 0.0)
            confidence = res.get("confidence", 0.0)
            confidences.append(confidence)

            # Binary threshold: prob >= 0.40 implies defective
            predicted = "defective" if prob >= 0.40 else "clean"

            margin = abs(prob - 0.40)
            y_true.append(expected)
            y_pred.append(predicted)

            is_correct = (predicted == expected)
            is_correct_list.append(is_correct)

            category = CodeFailureCategory.CORRECT.value
            if not is_correct:
                if expected == "clean" and predicted == "defective":
                    category = CodeFailureCategory.FALSE_VULNERABILITY.value
                    cat_counts[category] += 1
                    false_positives.append({
                        "id": q_id,
                        "code": code,
                        "defect_prob": round(prob, 4),
                        "confidence": round(confidence, 4),
                        "notes": item.get("notes", ""),
                    })
                elif expected == "defective" and predicted == "clean":
                    category = CodeFailureCategory.MISSED_DEFECT.value
                    cat_counts[category] += 1
                    false_negatives.append({
                        "id": q_id,
                        "code": code,
                        "defect_prob": round(prob, 4),
                        "confidence": round(confidence, 4),
                        "notes": item.get("notes", ""),
                    })

                failure_cases.append({
                    "id": q_id,
                    "code": code,
                    "expected": expected,
                    "predicted": predicted,
                    "defect_probability": round(prob, 4),
                    "confidence": round(confidence, 4),
                    "category": category,
                    "notes": item.get("notes", ""),
                })

                hard_examples.append(HardExample(
                    example_id=q_id,
                    input_snippet=code.split("\n")[0] + " ...",
                    true_label=expected,
                    predicted_label=predicted,
                    confidence=confidence,
                    margin=margin,
                    error_category=category,
                    root_cause_explanation=(
                        f"Code risk mismatch ({category}). Expected {expected}, got {predicted} "
                        f"(prob={prob:.2f}). Reason: {item.get('notes', '')}"
                    )
                ))
            else:
                cat_counts[CodeFailureCategory.CORRECT.value] += 1

        conf_mat = build_multiclass_confusion_matrix(y_true, y_pred, self.DEFECT_LABELS)
        per_class = compute_per_class_metrics_from_matrix(conf_mat)
        conf_dist = compute_confidence_distribution_metrics(confidences, is_correct_list)

        acc = sum(1 for c in is_correct_list if c) / len(is_correct_list) if is_correct_list else 0.0
        macro_f1 = float(np.mean([m.f1_score for m in per_class.values()]))

        return ModelErrorReport(
            model_name="CodeDefectDetector",
            model_alias="code-risk-v1",
            total_samples=len(data),
            accuracy_or_primary_metric=acc,
            macro_f1=macro_f1,
            confusion_matrix=conf_mat,
            per_class_metrics=per_class,
            failure_category_counts=cat_counts,
            failure_cases=failure_cases,
            hard_examples=hard_examples,
            false_positives=false_positives,
            false_negatives=false_negatives,
            confidence_distribution=conf_dist,
        )


# ─────────────────────────────────────────────────────────────────────
# E. Candidate Mastery Model (IRT / BKT) Error Analyzer
# ─────────────────────────────────────────────────────────────────────

class MasteryErrorAnalyzer:
    """
    Error analyzer for ItemResponseTheoryMasteryModel.
    Exposes categorized failure modes:
      - overestimation (Inflated ability θ estimate after lucky guess or easy item streak)
      - underestimation (Severely depressed ability θ after isolated careless slip)
    """

    TIER_LABELS = ["beginner", "intermediate", "advanced"]

    def __init__(self, irt_model=None):
        from ml.models.skill_mastery import ItemResponseTheoryMasteryModel
        self.model = irt_model or ItemResponseTheoryMasteryModel()

    def _theta_to_tier(self, theta: float) -> str:
        if theta < -0.5:
            return "beginner"
        elif theta <= 0.8:
            return "intermediate"
        else:
            return "advanced"

    def get_benchmark_simulation_trajectories(self) -> List[Dict[str, Any]]:
        """
        Candidate interview interaction sequences representing true skill profiles,
        lucky guess anomalies, and single-slip recovery profiles.
        """
        return [
            # ── Consistent Beginner ──
            {
                "id": "mastery_true_beg_01",
                "candidate_profile": "Novice Candidate",
                "true_theta": -1.5,
                "true_tier": "beginner",
                "interactions": [
                    {"difficulty": "beginner", "score": 85.0},
                    {"difficulty": "beginner", "score": 70.0},
                    {"difficulty": "intermediate", "score": 20.0},
                    {"difficulty": "beginner", "score": 80.0},
                ],
                "notes": "Consistent beginner performance"
            },
            # ── Consistent Intermediate ──
            {
                "id": "mastery_true_int_01",
                "candidate_profile": "Mid-Level Engineer",
                "true_theta": 0.2,
                "true_tier": "intermediate",
                "interactions": [
                    {"difficulty": "beginner", "score": 100.0},
                    {"difficulty": "intermediate", "score": 80.0},
                    {"difficulty": "intermediate", "score": 75.0},
                    {"difficulty": "advanced", "score": 40.0},
                ],
                "notes": "Standard mid-level candidate mastery"
            },
            # ── Consistent Advanced ──
            {
                "id": "mastery_true_adv_01",
                "candidate_profile": "Staff Architect",
                "true_theta": 1.8,
                "true_tier": "advanced",
                "interactions": [
                    {"difficulty": "intermediate", "score": 100.0},
                    {"difficulty": "advanced", "score": 90.0},
                    {"difficulty": "advanced", "score": 95.0},
                    {"difficulty": "advanced", "score": 85.0},
                ],
                "notes": "Senior engineer handling complex distributed systems"
            },

            # ── Overestimation Candidate (Lucky Guess / Small Sample Inflation) ──
            {
                "id": "mastery_overest_01",
                "candidate_profile": "Lucky Novice",
                "true_theta": -1.2,
                "true_tier": "beginner",
                "interactions": [
                    {"difficulty": "beginner", "score": 90.0},
                    {"difficulty": "advanced", "score": 100.0},  # Lucky guess on advanced MCQ
                ],
                "expected_failure": MasteryFailureCategory.OVERESTIMATION.value,
                "notes": "Lucky guess on item 2 creates huge positive gradient step, jumping theta into intermediate/advanced"
            },
            {
                "id": "mastery_overest_02",
                "candidate_profile": "Easy Item Streak",
                "true_theta": -0.8,
                "true_tier": "beginner",
                "interactions": [
                    {"difficulty": "beginner", "score": 100.0},
                    {"difficulty": "beginner", "score": 100.0},
                    {"difficulty": "beginner", "score": 100.0},
                ],
                "expected_failure": MasteryFailureCategory.OVERESTIMATION.value,
                "notes": "Streak of very easy questions causes ability estimate to escalate past beginner ceiling"
            },

            # ── Underestimation Candidate (Careless Slip / Cold-Start Drag) ──
            {
                "id": "mastery_underest_01",
                "candidate_profile": "Careless Senior",
                "true_theta": 1.6,
                "true_tier": "advanced",
                "interactions": [
                    {"difficulty": "beginner", "score": 0.0},   # Syntax slip on trivial warmup
                    {"difficulty": "intermediate", "score": 95.0},
                ],
                "expected_failure": MasteryFailureCategory.UNDERESTIMATION.value,
                "notes": "First-question syntax slip severely depresses theta; slow recovery under fixed learning rate"
            },
            {
                "id": "mastery_underest_02",
                "candidate_profile": "Hesitant Mid-Level",
                "true_theta": 0.4,
                "true_tier": "intermediate",
                "interactions": [
                    {"difficulty": "beginner", "score": 40.0},  # Time pressure on question 1
                    {"difficulty": "intermediate", "score": 60.0},
                ],
                "expected_failure": MasteryFailureCategory.UNDERESTIMATION.value,
                "notes": "Initial time penalty traps candidate in beginner tier longer than justified"
            },
        ]

    def analyze(self, dataset: Optional[List[Dict[str, Any]]] = None) -> ModelErrorReport:
        trajectories = dataset or self.get_benchmark_simulation_trajectories()

        y_true_tiers = []
        y_pred_tiers = []
        confidences = []
        is_correct_list = []
        failure_cases = []
        hard_examples = []
        false_positives = []
        false_negatives = []

        cat_counts = {cat.value: 0 for cat in MasteryFailureCategory}

        for traj in trajectories:
            t_id = traj.get("id", "unknown")
            true_theta = traj["true_theta"]
            true_tier = traj["true_tier"]

            # Run 2PL IRT update through interactions
            theta = 0.0  # Cold start prior
            trajectory_history = []

            for step in traj["interactions"]:
                diff = step["difficulty"]
                score = step["score"]
                res = self.model.update_ability(theta, score, diff)
                theta = float(res.get("updated_theta", res.get("new_theta", theta)))
                prof = float(res.get("estimated_proficiency", res.get("proficiency_100", 50.0)))
                trajectory_history.append({
                    "difficulty": diff,
                    "score": score,
                    "resulting_theta": round(theta, 3),
                    "proficiency": prof
                })

            final_tier = self._theta_to_tier(theta)
            y_true_tiers.append(true_tier)
            y_pred_tiers.append(final_tier)

            # In IRT, uncertainty decreases with items administered: proxy confidence = 1.0 - 1/(1+len)
            simulated_conf = 1.0 - (1.0 / (len(traj["interactions"]) + 1))
            confidences.append(simulated_conf)

            theta_error = theta - true_theta
            is_tier_match = (final_tier == true_tier)
            is_correct_list.append(is_tier_match)

            category = MasteryFailureCategory.CORRECT.value
            if theta_error > 0.60:
                category = MasteryFailureCategory.OVERESTIMATION.value
                cat_counts[category] += 1
                false_positives.append({
                    "id": t_id,
                    "profile": traj["candidate_profile"],
                    "true_theta": true_theta,
                    "estimated_theta": round(theta, 3),
                    "error": round(theta_error, 3),
                    "category": category
                })
            elif theta_error < -0.60:
                category = MasteryFailureCategory.UNDERESTIMATION.value
                cat_counts[category] += 1
                false_negatives.append({
                    "id": t_id,
                    "profile": traj["candidate_profile"],
                    "true_theta": true_theta,
                    "estimated_theta": round(theta, 3),
                    "error": round(theta_error, 3),
                    "category": category
                })
            else:
                cat_counts[MasteryFailureCategory.CORRECT.value] += 1

            if not is_tier_match or category != MasteryFailureCategory.CORRECT.value:
                failure_cases.append({
                    "id": t_id,
                    "profile": traj["candidate_profile"],
                    "true_theta": true_theta,
                    "true_tier": true_tier,
                    "estimated_theta": round(theta, 3),
                    "estimated_tier": final_tier,
                    "theta_error": round(theta_error, 3),
                    "category": category,
                    "interactions": trajectory_history,
                    "notes": traj.get("notes", ""),
                })
                hard_examples.append(HardExample(
                    example_id=t_id,
                    input_snippet=f"Profile: {traj['candidate_profile']} ({len(traj['interactions'])} items)",
                    true_label=f"{true_tier} (θ={true_theta:.2f})",
                    predicted_label=f"{final_tier} (θ={theta:.2f})",
                    confidence=simulated_conf,
                    margin=abs(theta_error),
                    error_category=category,
                    root_cause_explanation=(
                        f"Mastery estimation error ({category}). True θ={true_theta:.2f}, Est θ={theta:.2f} "
                        f"(Δ={theta_error:+.2f}). Notes: {traj.get('notes', '')}"
                    )
                ))

        conf_mat = build_multiclass_confusion_matrix(y_true_tiers, y_pred_tiers, self.TIER_LABELS)
        per_class = compute_per_class_metrics_from_matrix(conf_mat)
        conf_dist = compute_confidence_distribution_metrics(confidences, is_correct_list)

        acc = sum(1 for c in is_correct_list if c) / len(is_correct_list) if is_correct_list else 0.0
        macro_f1 = float(np.mean([m.f1_score for m in per_class.values()]))

        return ModelErrorReport(
            model_name="ItemResponseTheoryMasteryModel",
            model_alias="mastery-v1",
            total_samples=len(trajectories),
            accuracy_or_primary_metric=acc,
            macro_f1=macro_f1,
            confusion_matrix=conf_mat,
            per_class_metrics=per_class,
            failure_category_counts=cat_counts,
            failure_cases=failure_cases,
            hard_examples=hard_examples,
            false_positives=false_positives,
            false_negatives=false_negatives,
            confidence_distribution=conf_dist,
        )


# =====================================================================
# 5. Global Suite Execution & Report Export
# =====================================================================

def run_all_model_error_analyses(
    output_dir: str = "reports/error_analysis"
) -> Dict[str, ModelErrorReport]:
    """
    Executes full error-analysis suite across all 5 models and saves reports.
    """
    os.makedirs(output_dir, exist_ok=True)
    results = {}

    analyzers = [
        ("difficulty", DifficultyErrorAnalyzer()),
        ("skill_tagger", SkillTaggerErrorAnalyzer()),
        ("nli_analyzer", NLIAnswerAnalyzerErrorAnalyzer()),
        ("code_defect", CodeDefectErrorAnalyzer()),
        ("mastery", MasteryErrorAnalyzer()),
    ]

    summary_manifest = {
        "timestamp": "2026-10-03T22:00:00Z",
        "models_analyzed": len(analyzers),
        "reports": {},
    }

    for key, analyzer in analyzers:
        logger.info("Executing error analysis for %s...", analyzer.__class__.__name__)
        report = analyzer.analyze()
        results[key] = report

        # Export individual JSON report
        model_json_path = os.path.join(output_dir, f"{key}_error_report.json")
        with open(model_json_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)

        summary_manifest["reports"][key] = {
            "model_name": report.model_name,
            "model_alias": report.model_alias,
            "samples": report.total_samples,
            "primary_metric": report.accuracy_or_primary_metric,
            "macro_f1": report.macro_f1,
            "failure_counts": report.failure_category_counts,
            "hard_examples_count": len(report.hard_examples),
            "report_path": model_json_path,
        }

    # Export overall summary manifest
    summary_path = os.path.join(output_dir, "error_analysis_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_manifest, f, indent=2)

    return results

"""
Reproducible Offline Training Pipeline — Question Skill/Topic Tagger.

Usage:
    python -m ml.training.train_skill_tagger
    python -m ml.training.train_skill_tagger --config ml/configs/question_skill.yaml
    python -m ml.training.train_skill_tagger --config ml/configs/question_skill.yaml --dry-run

Every training run records:
    dataset identifier & version, dataset hash, preprocessing version,
    random seed, model base, hyperparameters, training duration,
    validation metrics, test metrics, artifact hash.
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, hamming_loss, precision_score, recall_score
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer

from ml.datasets.taco_loader import (
    CANONICAL_SKILLS,
    TACODatasetLoader,
    map_to_canonical_skills,
)
from ml.preprocessing.data_pipeline import (
    check_data_leakage,
    clean_text,
    compute_dataset_hash,
    stratified_split,
)
from ml.training.pipeline import (
    TrainingMetadata,
    compute_artifact_hash,
    generate_training_report,
    load_training_config,
    set_reproducibility_seed,
)

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = "ml/configs/question_skill.yaml"


# ─────────────────────────────────────────────────────────────────────────────
# Canonical Interview Augmentation Samples
# ─────────────────────────────────────────────────────────────────────────────

INTERVIEW_AUGMENTATION_SAMPLES: List[Tuple[str, List[str]]] = [
    ("Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.", ["arrays", "hashing", "two_pointers", "data_structures", "algorithms"]),
    ("Given an integer array nums, return all the triplets [nums[i], nums[j], nums[k]] such that they sum to zero using two pointers.", ["arrays", "two_pointers", "sorting", "algorithms"]),
    ("Given a sorted array of distinct integers and a target value, return the index if the target is found using binary search.", ["arrays", "binary_search", "search", "algorithms", "complexity"]),
    ("Given a string s, find the length of the longest substring without repeating characters using a sliding window and hash map.", ["strings", "sliding_window", "hashing", "two_pointers", "data_structures", "algorithms"]),
    ("Given two strings s and t of lengths m and n respectively, return the minimum window substring of s such that every character in t is included.", ["strings", "sliding_window", "hashing", "two_pointers", "algorithms"]),
    ("Given the head of a singly linked list, reverse the list and return the reversed list.", ["linked_lists", "two_pointers", "data_structures", "algorithms"]),
    ("Given head, the head of a linked list, determine if the linked list has a cycle in it using Floyd's cycle-finding two pointers.", ["linked_lists", "two_pointers", "data_structures", "algorithms"]),
    ("Given the root of a binary tree, return its maximum depth using recursion and depth-first search.", ["trees", "recursion", "search", "data_structures", "algorithms"]),
    ("Given the root of a binary tree, return the level order traversal of its nodes' values using a breadth-first search queue.", ["trees", "queues", "search", "data_structures", "algorithms"]),
    ("Given an integer array nums and an integer k, return the kth largest element in the array using a min-heap priority queue.", ["heaps", "queues", "sorting", "arrays", "data_structures", "algorithms"]),
    ("Implement a first in first out (FIFO) queue using only two stacks.", ["stacks", "queues", "data_structures"]),
    ("Design a stack that supports push, pop, top, and retrieving the minimum element in constant O(1) time complexity.", ["stacks", "complexity", "data_structures", "algorithms"]),
    ("There are a total of numCourses courses you have to take. Find if it is possible to finish all courses using topological sort and cycle detection.", ["graphs", "search", "queues", "recursion", "data_structures", "algorithms"]),
    ("Given an m x n 2D binary grid which represents a map of land and water, return the number of islands using depth-first search.", ["graphs", "search", "recursion", "arrays", "algorithms"]),
    ("Given an integer array coins and an integer amount, return the fewest number of coins needed using bottom-up dynamic programming.", ["dynamic_programming", "arrays", "complexity", "algorithms"]),
    ("Given two strings text1 and text2, return the length of their longest common subsequence using a 2D dynamic programming table.", ["dynamic_programming", "strings", "complexity", "algorithms"]),
    ("Given an array of intervals, return the minimum number of intervals to remove to make the rest non-overlapping using a greedy choice.", ["greedy", "sorting", "arrays", "algorithms"]),
    ("Given an integer array nums of unique elements, return all possible subsets using recursive backtracking.", ["backtracking", "recursion", "arrays", "algorithms"]),
    ("Given a sorted array of integers nums and an integer target, search in O(log n) runtime using binary search.", ["binary_search", "search", "arrays", "complexity", "algorithms"]),
    ("Given a string containing just parentheses and brackets, determine if the input string is valid using a stack.", ["stacks", "strings", "data_structures", "algorithms"]),
    ("Merge k sorted linked lists and return one sorted list using a min-heap priority queue.", ["heaps", "linked_lists", "queues", "sorting", "data_structures", "algorithms"]),
    ("Given an array of integers temperatures, return an array answer such that answer[i] is the number of days until warmer temperature using a monotonic stack.", ["stacks", "arrays", "data_structures", "algorithms"]),
    ("Serialize and deserialize a binary tree using pre-order traversal and queue reconstruction.", ["trees", "queues", "strings", "recursion", "data_structures"]),
    ("The n-queens puzzle: place n queens on an n x n chessboard such that no two queens attack each other using backtracking.", ["backtracking", "recursion", "arrays", "algorithms"]),
    ("Given a directed graph, determine strongly connected components using Tarjan's algorithm.", ["graphs", "search", "recursion", "algorithms"]),
]


# ─────────────────────────────────────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────────────────────────────────────

def load_skill_data(config: Dict[str, Any]) -> Tuple[List[str], List[List[str]]]:
    """
    Load question texts and multi-label skill annotations from TACO dataset.
    Falls back to augmentation seeds when TACO is unavailable.
    """
    dataset_cfg = config.get("dataset", {})
    preproc_cfg = config.get("preprocessing", {}).get("text_cleaning", {})
    aug_cfg = dataset_cfg.get("augmentation", {})
    sources = dataset_cfg.get("sources", [])

    texts: List[str] = []
    labels: List[List[str]] = []

    for source in sources:
        name = source.get("name", "")
        max_samples = source.get("max_samples", 2500)

        if "TACO" in name:
            try:
                loader = TACODatasetLoader()
                count = 0
                for sample in loader.load_samples(limit=max_samples):
                    if sample.question_text and sample.canonical_skills:
                        cleaned = clean_text(
                            sample.question_text,
                            strip_html=preproc_cfg.get("strip_html", True),
                            lowercase=preproc_cfg.get("lowercase", False),
                            min_length_chars=preproc_cfg.get("min_length_chars", 10),
                        )
                        if cleaned:
                            texts.append(cleaned)
                            labels.append(sample.canonical_skills)
                            count += 1
                logger.info("Loaded %d genuine samples from %s", count, name)
            except Exception as e:
                logger.warning("Failed to load %s: %s", name, e)

    # Interview seed augmentation
    if aug_cfg.get("interview_seeds", True) or aug_cfg.get("enabled", True):
        replication = aug_cfg.get("replication_factor", 4)
        aug_count = 0
        for _ in range(replication):
            for text, skills in INTERVIEW_AUGMENTATION_SAMPLES:
                cleaned = clean_text(text, min_length_chars=5)
                if cleaned:
                    texts.append(cleaned)
                    labels.append(skills)
                    aug_count += 1
        logger.info("Added %d augmentation samples (%dx replication of %d seeds).",
                     aug_count, replication, len(INTERVIEW_AUGMENTATION_SAMPLES))

    if not texts:
        raise RuntimeError("No training data available. Cannot proceed with training.")

    logger.info("Total skill tagger dataset: %d samples across %d canonical skills", len(texts), len(CANONICAL_SKILLS))
    return texts, labels


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_multilabel(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_probs: np.ndarray,
    skill_names: List[str],
) -> Dict[str, Any]:
    """Compute all multi-label classification metrics on actual predictions."""
    micro_f1 = float(f1_score(y_true, y_pred, average="micro", zero_division=0))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    micro_p = float(precision_score(y_true, y_pred, average="micro", zero_division=0))
    macro_p = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    micro_r = float(recall_score(y_true, y_pred, average="micro", zero_division=0))
    macro_r = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    h_loss = float(hamming_loss(y_true, y_pred))

    per_label_f1 = f1_score(y_true, y_pred, average=None, zero_division=0)
    per_label_p = precision_score(y_true, y_pred, average=None, zero_division=0)
    per_label_r = recall_score(y_true, y_pred, average=None, zero_division=0)

    per_class = {}
    for i, skill in enumerate(skill_names):
        support = int(np.sum(y_true[:, i]))
        per_class[skill] = {
            "precision": round(float(per_label_p[i]), 4),
            "recall": round(float(per_label_r[i]), 4),
            "f1": round(float(per_label_f1[i]), 4),
            "support": support,
        }

    return {
        "micro_f1": round(micro_f1, 4),
        "macro_f1": round(macro_f1, 4),
        "precision": {"micro": round(micro_p, 4), "macro": round(macro_p, 4)},
        "recall": {"micro": round(micro_r, 4), "macro": round(macro_r, 4)},
        "hamming_loss": round(h_loss, 4),
        "per_class": per_class,
    }


def apply_threshold_with_fallback(
    y_probs: np.ndarray,
    threshold: float,
    min_predictions: int = 1,
) -> np.ndarray:
    """Apply prediction threshold, ensuring at least min_predictions per sample."""
    y_pred = (y_probs >= threshold).astype(int)
    for i in range(len(y_pred)):
        if np.sum(y_pred[i]) < min_predictions:
            best_indices = np.argsort(y_probs[i])[-min_predictions:]
            y_pred[i, best_indices] = 1
    return y_pred


# ─────────────────────────────────────────────────────────────────────────────
# Main Training Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_training(config_path: str, *, dry_run: bool = False) -> Dict[str, Any]:
    """
    Execute the full reproducible training pipeline for question skill tagging.

    Steps:
        1. Load config
        2. Set reproducibility seed
        3. Load and preprocess data
        4. Binarize multi-labels
        5. Stratified split into train/val/test
        6. Data leakage check
        7. Train TF-IDF + OneVsRest classifier
        8. Evaluate on validation set
        9. Evaluate on held-out test set
        10. Save artifact with hash
        11. Save metadata
        12. Generate report from actual metrics
    """
    # 1. Load config
    config = load_training_config(config_path)
    model_cfg = config.get("model", {})
    split_cfg = config.get("split", {})
    hp_cfg = config.get("hyperparameters", {})
    artifact_cfg = config.get("artifacts", {})
    class_names = model_cfg.get("classes", CANONICAL_SKILLS)

    # 2. Reproducibility
    seed = config.get("reproducibility", {}).get("random_seed", 42)
    set_reproducibility_seed(seed)

    # Initialize metadata
    metadata = TrainingMetadata(config)
    metadata.start_timer()

    # 3. Load and preprocess data
    logger.info("=" * 70)
    logger.info("TRAINING PIPELINE: %s v%s", model_cfg.get("name"), model_cfg.get("version"))
    logger.info("=" * 70)

    texts, raw_labels = load_skill_data(config)
    metadata.dataset_hash = compute_dataset_hash(texts, raw_labels)
    logger.info("Dataset hash: %s", metadata.dataset_hash)

    if dry_run:
        logger.info("[DRY RUN] Would train on %d samples. Exiting.", len(texts))
        return {"status": "dry_run", "samples": len(texts), "dataset_hash": metadata.dataset_hash}

    # 4. Binarize multi-labels
    mlb = MultiLabelBinarizer(classes=class_names)
    Y = mlb.fit_transform(raw_labels)

    # 5. Split
    splits = stratified_split(
        texts, Y,
        test_size=split_cfg.get("test_size", 0.20),
        val_size=split_cfg.get("validation_size", 0.10),
        random_seed=seed,
        is_multilabel=True,
    )
    metadata.split_sizes = {
        "train": len(splits["train_texts"]),
        "val": len(splits["val_texts"]),
        "test": len(splits["test_texts"]),
    }

    # 6. Data leakage check
    check_data_leakage(
        splits["train_texts"],
        splits["test_texts"],
        val_texts=splits["val_texts"],
    )

    # 7. Train TF-IDF + OneVsRest
    vec_params = hp_cfg.get("vectorizer", {})
    clf_params = hp_cfg.get("classifier", {})
    threshold = hp_cfg.get("prediction_threshold", 0.30)
    min_preds = hp_cfg.get("min_predictions_per_sample", 1)

    logger.info("Fitting TF-IDF vectorizer (%d features)...", vec_params.get("max_features", 6000))
    ngram_range = tuple(vec_params.get("ngram_range", [1, 2]))
    vectorizer = TfidfVectorizer(
        max_features=vec_params.get("max_features", 6000),
        ngram_range=ngram_range,
        stop_words=vec_params.get("stop_words", "english"),
        sublinear_tf=vec_params.get("sublinear_tf", True),
    )

    X_train = vectorizer.fit_transform(splits["train_texts"])
    X_val = vectorizer.transform(splits["val_texts"])
    X_test = vectorizer.transform(splits["test_texts"])

    y_train = splits["train_labels"]
    y_val = splits["val_labels"]
    y_test = splits["test_labels"]

    logger.info("Training OneVsRestClassifier (C=%s, max_iter=%s) on %d samples...",
                clf_params.get("C", 2.0), clf_params.get("max_iter", 1000), X_train.shape[0])

    base_lr = LogisticRegression(
        C=clf_params.get("C", 2.0),
        max_iter=clf_params.get("max_iter", 1000),
        class_weight=clf_params.get("class_weight", "balanced"),
        solver=clf_params.get("solver", "lbfgs"),
        random_state=seed,
    )
    classifier = OneVsRestClassifier(base_lr, n_jobs=1)

    train_start = time.time()
    classifier.fit(X_train, y_train)
    train_seconds = round(time.time() - train_start, 2)
    logger.info("Training completed in %.2fs", train_seconds)

    # 8. Evaluate on validation set
    y_val_probs = classifier.predict_proba(X_val)
    y_val_pred = apply_threshold_with_fallback(y_val_probs, threshold, min_preds)
    val_metrics = evaluate_multilabel(y_val, y_val_pred, y_val_probs, class_names)
    metadata.validation_metrics = val_metrics
    logger.info("VALIDATION — Micro F1: %.4f, Macro F1: %.4f, Hamming: %.4f",
                val_metrics["micro_f1"], val_metrics["macro_f1"], val_metrics["hamming_loss"])

    # 9. Evaluate on held-out test set
    y_test_probs = classifier.predict_proba(X_test)
    y_test_pred = apply_threshold_with_fallback(y_test_probs, threshold, min_preds)
    test_metrics = evaluate_multilabel(y_test, y_test_pred, y_test_probs, class_names)
    metadata.test_metrics = test_metrics
    logger.info("TEST — Micro F1: %.4f, Macro F1: %.4f, Hamming: %.4f",
                test_metrics["micro_f1"], test_metrics["macro_f1"], test_metrics["hamming_loss"])

    # 10. Save artifact
    output_dir = Path(artifact_cfg.get("output_dir", "ml/artifacts/skill_tagger"))
    output_dir.mkdir(parents=True, exist_ok=True)

    weights_filename = artifact_cfg.get("weights_filename", "skill_classifier.joblib")
    artifact_path = output_dir / weights_filename

    artifact_bundle = {
        "model_version": model_cfg.get("version", "1.0.0"),
        "model_type": model_cfg.get("base", "TF-IDF + OneVsRest(LogisticRegression)"),
        "vectorizer": vectorizer,
        "classifier": classifier,
        "canonical_skills": class_names,
        "threshold": threshold,
        "seed": seed,
        "dataset_hash": metadata.dataset_hash,
        "trained_samples": len(splits["train_texts"]),
    }
    joblib.dump(artifact_bundle, artifact_path)
    metadata.artifact_path = str(artifact_path)
    metadata.artifact_hash = compute_artifact_hash(str(artifact_path))
    logger.info("Artifact saved: %s (hash: %s)", artifact_path, metadata.artifact_hash)

    # Copy to legacy path
    legacy_path = artifact_cfg.get("legacy_weights_path")
    if legacy_path:
        legacy = Path(legacy_path)
        legacy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(artifact_path, legacy)
        logger.info("Legacy artifact copy: %s", legacy)

    # 11. Save metadata
    metadata.stop_timer()
    metadata_path = output_dir / artifact_cfg.get("metadata_filename", "training_metadata.json")
    metadata.save(str(metadata_path))

    # 12. Generate report from ACTUAL metrics
    report_path = "reports/skill_model_report.md"
    generate_training_report(
        metadata,
        report_path,
        per_class_metrics=test_metrics.get("per_class"),
        class_names=class_names,
        additional_sections=_make_skill_report_extra(test_metrics, class_names),
    )

    logger.info("=" * 70)
    logger.info("PIPELINE COMPLETE: %s", model_cfg.get("name"))
    logger.info("  Artifact: %s", artifact_path)
    logger.info("  Artifact Hash: %s", metadata.artifact_hash)
    logger.info("  Test Micro F1: %.4f", test_metrics["micro_f1"])
    logger.info("  Test Macro F1: %.4f", test_metrics["macro_f1"])
    logger.info("  Report: %s", report_path)
    logger.info("=" * 70)

    return metadata.to_dict()


def _make_skill_report_extra(test_metrics: Dict[str, Any], class_names: List[str]) -> str:
    """Generate additional report sections specific to skill tagging."""
    lines = []
    lines.append("## Label Coverage Summary\n")

    per_class = test_metrics.get("per_class", {})
    strong = [s for s in class_names if per_class.get(s, {}).get("f1", 0) >= 0.5]
    weak = [s for s in class_names if 0.0 < per_class.get(s, {}).get("f1", 0) < 0.5]
    zero = [s for s in class_names if per_class.get(s, {}).get("f1", 0) == 0.0]

    if strong:
        lines.append(f"**Strong labels** (F1 ≥ 0.50): {', '.join(f'`{s}`' for s in strong)}\n")
    if weak:
        lines.append(f"**Weak labels** (0 < F1 < 0.50): {', '.join(f'`{s}`' for s in weak)}\n")
    if zero:
        lines.append(f"**Zero-support labels** (F1 = 0.00): {', '.join(f'`{s}`' for s in zero)}\n")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Reproducible training pipeline for Question Skill/Topic Tagger."
    )
    parser.add_argument(
        "--config", type=str, default=DEFAULT_CONFIG,
        help=f"Path to YAML training config (default: {DEFAULT_CONFIG})"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Load data and validate config without training."
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    run_training(args.config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

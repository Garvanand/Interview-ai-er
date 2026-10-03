"""
Reproducible Offline Training Pipeline — Question Difficulty Predictor.

Usage:
    python -m ml.training.train_difficulty
    python -m ml.training.train_difficulty --config ml/configs/question_difficulty.yaml
    python -m ml.training.train_difficulty --config ml/configs/question_difficulty.yaml --dry-run

Every training run records:
    dataset identifier & version, dataset hash, preprocessing version,
    random seed, model base, hyperparameters, training duration,
    validation metrics, test metrics, artifact hash.
"""
from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from ml.datasets.taco_loader import TACODatasetLoader
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

DEFAULT_CONFIG = "ml/configs/question_difficulty.yaml"

# ─────────────────────────────────────────────────────────────────────────────
# Synthetic Bootstrap Data (used when online datasets are unavailable)
# ─────────────────────────────────────────────────────────────────────────────
BOOTSTRAP_SAMPLES: List[Tuple[str, str]] = [
    ("Write a function to return the sum of two integers.", "beginner"),
    ("Write a program to check if a string is a palindrome.", "beginner"),
    ("What is the time complexity of bubble sort?", "beginner"),
    ("Write a simple function to add two numbers.", "beginner"),
    ("Reverse a string in place.", "beginner"),
    ("Write a function to return the nth Fibonacci number.", "beginner"),
    ("Write a script to read a file and count word frequencies.", "beginner"),
    ("Write a simple HTML page with a button.", "beginner"),
    ("Implement a function to reverse a singly linked list in place.", "intermediate"),
    ("Given an array of integers, find the maximum subarray sum using Kadane's algorithm.", "intermediate"),
    ("Implement a binary search tree with insert and search operations.", "intermediate"),
    ("Check if a linked list has a cycle using Floyd's tortoise and hare algorithm.", "intermediate"),
    ("Given an array, find the maximum contiguous subarray sum.", "intermediate"),
    ("Implement a trie for prefix matching.", "intermediate"),
    ("Implement Dijkstra's shortest path algorithm for a weighted graph.", "intermediate"),
    ("Create a React component that fetches data from an API and renders results.", "intermediate"),
    ("Find the longest common subsequence of two strings using dynamic programming.", "intermediate"),
    ("Design an LRU Cache with O(1) get and put operations using doubly linked list and hash map.", "advanced"),
    ("Solve the traveling salesman problem using dynamic programming with bitmasking in O(N^2 2^N).", "advanced"),
    ("Design a concurrent hash map with fine-grained locking for multithreaded access.", "advanced"),
    ("Implement a distributed consensus algorithm like Paxos.", "advanced"),
    ("Explain how the Raft consensus algorithm handles leader election and log replication.", "advanced"),
    ("Implement a lock-free queue using compare-and-swap atomic operations.", "advanced"),
    ("Find the median of two sorted arrays in O(log(min(m,n))) time.", "advanced"),
    ("Design a scalable microservices architecture for a ride-sharing application.", "advanced"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────────────────────────────────────

def load_difficulty_data(config: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Load question texts and difficulty labels from configured dataset sources.
    Falls back to synthetic bootstrap data when online datasets are unavailable.
    """
    dataset_cfg = config.get("dataset", {})
    preproc_cfg = config.get("preprocessing", {}).get("text_cleaning", {})
    sources = dataset_cfg.get("sources", [])

    texts: List[str] = []
    labels: List[str] = []

    for source in sources:
        name = source.get("name", "")
        max_samples = source.get("max_samples", 1000)

        if "TACO" in name:
            try:
                loader = TACODatasetLoader(split="train", streaming=True)
                for sample in loader.load_samples(limit=max_samples):
                    if sample.question_text and sample.difficulty_normalized:
                        cleaned = clean_text(
                            sample.question_text,
                            strip_html=preproc_cfg.get("strip_html", True),
                            lowercase=preproc_cfg.get("lowercase", False),
                            min_length_chars=preproc_cfg.get("min_length_chars", 10),
                        )
                        if cleaned:
                            texts.append(cleaned)
                            labels.append(sample.difficulty_normalized)
                logger.info("Loaded %d samples from %s", len(texts), name)
            except Exception as e:
                logger.warning("Failed to load %s: %s", name, e)

        elif "apps" in name.lower():
            try:
                from ml.datasets.apps_loader import APPSDatasetLoader
                loader = APPSDatasetLoader(split="train", streaming=True)
                count_before = len(texts)
                for sample in loader.load_samples(limit=max_samples):
                    if sample.question_text and sample.difficulty_normalized:
                        cleaned = clean_text(
                            sample.question_text,
                            strip_html=preproc_cfg.get("strip_html", True),
                            lowercase=preproc_cfg.get("lowercase", False),
                            min_length_chars=preproc_cfg.get("min_length_chars", 10),
                        )
                        if cleaned:
                            texts.append(cleaned)
                            labels.append(sample.difficulty_normalized)
                logger.info("Loaded %d samples from %s", len(texts) - count_before, name)
            except Exception as e:
                logger.warning("Failed to load %s: %s", name, e)

    # Bootstrap fallback
    if not texts:
        logger.warning("No samples from online datasets. Using synthetic bootstrap data.")
        aug_cfg = dataset_cfg.get("augmentation", {})
        replication = aug_cfg.get("bootstrap_replication_factor", 2)
        for _ in range(replication):
            for text, label in BOOTSTRAP_SAMPLES:
                cleaned = clean_text(text, min_length_chars=5)
                if cleaned:
                    texts.append(cleaned)
                    labels.append(label)

    logger.info("Total difficulty dataset: %d samples", len(texts))
    return texts, labels


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_predictions(
    y_true: List[str],
    y_pred: List[str],
    class_names: List[str],
) -> Dict[str, Any]:
    """Compute classification metrics on actual predictions."""
    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))
    macro_p = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    macro_r = float(recall_score(y_true, y_pred, average="macro", zero_division=0))

    per_class_p = precision_score(y_true, y_pred, average=None, labels=class_names, zero_division=0)
    per_class_r = recall_score(y_true, y_pred, average=None, labels=class_names, zero_division=0)
    per_class_f1 = f1_score(y_true, y_pred, average=None, labels=class_names, zero_division=0)

    cm = confusion_matrix(y_true, y_pred, labels=class_names).tolist()

    per_class = {}
    for i, cls in enumerate(class_names):
        support = sum(1 for yt in y_true if yt == cls)
        per_class[cls] = {
            "precision": round(float(per_class_p[i]), 4),
            "recall": round(float(per_class_r[i]), 4),
            "f1": round(float(per_class_f1[i]), 4),
            "support": support,
        }

    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "per_class": per_class,
        "confusion_matrix": cm,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main Training Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_training(config_path: str, *, dry_run: bool = False) -> Dict[str, Any]:
    """
    Execute the full reproducible training pipeline for question difficulty.

    Steps:
        1. Load config
        2. Set reproducibility seed
        3. Load and preprocess data
        4. Stratified split into train/val/test
        5. Data leakage check
        6. Train classifier
        7. Evaluate on validation set
        8. Evaluate on held-out test set
        9. Save artifact with hash
        10. Save metadata
        11. Generate report from actual metrics
    """
    # 1. Load config
    config = load_training_config(config_path)
    model_cfg = config.get("model", {})
    split_cfg = config.get("split", {})
    hp_cfg = config.get("hyperparameters", {})
    artifact_cfg = config.get("artifacts", {})
    class_names = model_cfg.get("classes", ["beginner", "intermediate", "advanced"])

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

    texts, labels = load_difficulty_data(config)
    metadata.dataset_hash = compute_dataset_hash(texts, labels)
    logger.info("Dataset hash: %s", metadata.dataset_hash)

    if dry_run:
        logger.info("[DRY RUN] Would train on %d samples. Exiting.", len(texts))
        return {"status": "dry_run", "samples": len(texts), "dataset_hash": metadata.dataset_hash}

    # 4. Stratified split
    splits = stratified_split(
        texts, labels,
        test_size=split_cfg.get("test_size", 0.20),
        val_size=split_cfg.get("validation_size", 0.10),
        random_seed=seed,
        is_multilabel=False,
    )
    metadata.split_sizes = {
        "train": len(splits["train_texts"]),
        "val": len(splits["val_texts"]),
        "test": len(splits["test_texts"]),
    }

    # 5. Data leakage check — aborts if >5% leakage
    check_data_leakage(
        splits["train_texts"],
        splits["test_texts"],
        val_texts=splits["val_texts"],
    )

    # 6. Train classifier
    classical_hp = hp_cfg.get("classical", hp_cfg)
    vec_params = classical_hp.get("vectorizer", {})
    clf_params = classical_hp.get("classifier", {})

    logger.info("Fitting TF-IDF vectorizer (%d features)...", vec_params.get("max_features", 5000))
    ngram_range = tuple(vec_params.get("ngram_range", [1, 2]))
    vectorizer = TfidfVectorizer(
        max_features=vec_params.get("max_features", 5000),
        ngram_range=ngram_range,
        stop_words=vec_params.get("stop_words", "english"),
        sublinear_tf=vec_params.get("sublinear_tf", True),
    )

    X_train = vectorizer.fit_transform(splits["train_texts"])
    X_val = vectorizer.transform(splits["val_texts"])
    X_test = vectorizer.transform(splits["test_texts"])

    logger.info("Training LogisticRegression (C=%s, max_iter=%s)...",
                clf_params.get("C", 1.0), clf_params.get("max_iter", 1000))
    classifier = LogisticRegression(
        C=clf_params.get("C", 1.0),
        max_iter=clf_params.get("max_iter", 1000),
        class_weight=clf_params.get("class_weight", "balanced"),
        solver=clf_params.get("solver", "lbfgs"),
        multi_class=clf_params.get("multi_class", "multinomial"),
        random_state=seed,
    )

    train_start = time.time()
    classifier.fit(X_train, splits["train_labels"])
    train_seconds = round(time.time() - train_start, 2)
    logger.info("Training completed in %.2fs", train_seconds)

    # 7. Evaluate on validation set
    y_val_pred = classifier.predict(X_val).tolist()
    val_metrics = evaluate_predictions(splits["val_labels"], y_val_pred, class_names)
    metadata.validation_metrics = val_metrics
    logger.info("VALIDATION — Accuracy: %.4f, Macro F1: %.4f", val_metrics["accuracy"], val_metrics["macro_f1"])

    # 8. Evaluate on held-out test set
    y_test_pred = classifier.predict(X_test).tolist()
    test_metrics = evaluate_predictions(splits["test_labels"], y_test_pred, class_names)
    metadata.test_metrics = test_metrics
    logger.info("TEST — Accuracy: %.4f, Macro F1: %.4f", test_metrics["accuracy"], test_metrics["macro_f1"])

    # 9. Save artifact
    output_dir = Path(artifact_cfg.get("output_dir", "ml/artifacts/difficulty"))
    output_dir.mkdir(parents=True, exist_ok=True)

    weights_filename = artifact_cfg.get("weights_filename", "difficulty_model.joblib")
    artifact_path = output_dir / weights_filename

    artifact_bundle = {
        "model_version": model_cfg.get("version", "1.0.0"),
        "model_type": model_cfg.get("base", "TF-IDF + LogisticRegression"),
        "vectorizer": vectorizer,
        "classifier": classifier,
        "classes": class_names,
        "seed": seed,
        "dataset_hash": metadata.dataset_hash,
        "trained_samples": len(splits["train_texts"]),
    }
    joblib.dump(artifact_bundle, artifact_path)
    metadata.artifact_path = str(artifact_path)
    metadata.artifact_hash = compute_artifact_hash(str(artifact_path))
    logger.info("Artifact saved: %s (hash: %s)", artifact_path, metadata.artifact_hash)

    # Copy to legacy path if configured
    legacy_path = artifact_cfg.get("legacy_weights_path")
    if legacy_path:
        legacy = Path(legacy_path)
        legacy.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(artifact_path, legacy)
        logger.info("Legacy artifact copy: %s", legacy)

    # 10. Save metadata
    metadata.stop_timer()
    metadata_path = output_dir / artifact_cfg.get("metadata_filename", "training_metadata.json")
    metadata.save(str(metadata_path))

    # 11. Generate report from ACTUAL metrics
    report_path = "reports/difficulty_model_report.md"
    generate_training_report(
        metadata,
        report_path,
        per_class_metrics=test_metrics.get("per_class"),
        confusion_matrix=test_metrics.get("confusion_matrix"),
        class_names=class_names,
    )

    logger.info("=" * 70)
    logger.info("PIPELINE COMPLETE: %s", model_cfg.get("name"))
    logger.info("  Artifact: %s", artifact_path)
    logger.info("  Artifact Hash: %s", metadata.artifact_hash)
    logger.info("  Test Accuracy: %.4f", test_metrics["accuracy"])
    logger.info("  Test Macro F1: %.4f", test_metrics["macro_f1"])
    logger.info("  Report: %s", report_path)
    logger.info("=" * 70)

    return metadata.to_dict()


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Reproducible training pipeline for Question Difficulty Predictor."
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

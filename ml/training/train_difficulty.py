"""
Training pipeline for Question Difficulty Prediction.
Trains a classifier on TACO and APPS problem statements using sentence embeddings.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
import numpy as np

from ml.datasets.taco_loader import TACODatasetLoader
from ml.datasets.apps_loader import APPSDatasetLoader
from ml.features.text_embeddings import TextEmbeddingExtractor

logger = logging.getLogger(__name__)


def train_difficulty_model(output_path: str, max_samples: int = 2000):
    """Train Ridge/LogisticRegression difficulty model and serialize with joblib."""
    logger.info("Initializing dataset loaders for difficulty training...")
    taco = TACODatasetLoader(split="train", streaming=True)
    apps = APPSDatasetLoader(split="train", streaming=True)
    embedder = TextEmbeddingExtractor()

    texts = []
    labels = []

    # Ingest TACO
    for sample in taco.load_samples(limit=max_samples // 2):
        if sample.question_text and sample.difficulty_normalized:
            texts.append(sample.question_text)
            labels.append(sample.difficulty_normalized)

    # Ingest APPS
    for sample in apps.load_samples(limit=max_samples // 2):
        if sample.question_text and sample.difficulty_normalized:
            texts.append(sample.question_text)
            labels.append(sample.difficulty_normalized)

    if not texts:
        logger.warning("No samples loaded from online datasets. Using synthetic bootstrap data for calibration.")
        texts = [
            "Write a function to return the sum of two integers.",
            "Implement a function to reverse a singly linked list in place.",
            "Design an LRU Cache with O(1) get and put operations using doubly linked list and hash map.",
            "Given an array of integers, find the maximum subarray sum using Kadane's algorithm.",
            "Solve the traveling salesman problem using dynamic programming with bitmasking in O(N^2 2^N).",
            "Write a program to check if a string is a palindrome.",
        ]
        labels = ["beginner", "intermediate", "intermediate", "intermediate", "advanced", "beginner"]

    logger.info("Extracting embeddings for %d training samples...", len(texts))
    X = embedder.encode(texts)
    y = np.array(labels)

    try:
        from sklearn.linear_model import LogisticRegression
        import joblib

        clf = LogisticRegression(max_iter=1000, class_weight="balanced")
        clf.fit(X, y)

        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(clf, out_file)
        logger.info("Model successfully trained and saved to %s", out_file)
    except ImportError:
        logger.error("scikit-learn and joblib required for training. Install `pip install scikit-learn joblib`.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default="ml/models/weights/difficulty_model.joblib")
    parser.add_argument("--samples", type=int, default=1000)
    args = parser.parse_args()
    train_difficulty_model(args.output, args.samples)

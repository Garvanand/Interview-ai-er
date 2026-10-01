"""
Training and Evaluation Pipeline for Multi-Label Question-Skill Classification.
Dataset: BAAI/TACO (problem statements, tags, skill_types).
Taxonomy: 21 Canonical Skills compatible with Interview-ai-er.
Models:
1. Classical Baseline: TF-IDF + One-vs-Rest Logistic Regression
2. Lightweight Transformer: MiniLM / DistilBERT Embedding Classifier
Evaluation Metrics:
- micro F1
- macro F1
- per-label F1
- precision (micro, macro, per-label)
- recall (micro, macro, per-label)
- Hamming loss
"""
from __future__ import annotations

import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple

import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.multiclass import OneVsRestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    hamming_loss,
    classification_report
)

from ml.datasets.taco_loader import TACODatasetLoader, CANONICAL_SKILLS, map_to_canonical_skills

logger = logging.getLogger(__name__)

# Canonical interview question augmentation to guarantee strong sample representation across all 21 skills
INTERVIEW_AUGMENTATION_SAMPLES: List[Tuple[str, List[str]]] = [
    # arrays, two_pointers, hashing
    ("Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.", ["arrays", "hashing", "two_pointers", "data_structures", "algorithms"]),
    ("Given an integer array nums, return all the triplets [nums[i], nums[j], nums[k]] such that they sum to zero using two pointers.", ["arrays", "two_pointers", "sorting", "algorithms"]),
    ("Given a sorted array of distinct integers and a target value, return the index if the target is found using binary search.", ["arrays", "binary_search", "search", "algorithms", "complexity"]),
    ("Given an array nums of n integers where nums[i] is in the range [1, n], return an array of all the integers that appear twice using a hash set.", ["arrays", "hashing", "data_structures", "algorithms"]),
    ("Find the contiguous subarray within an array (containing at least one number) which has the largest sum.", ["arrays", "dynamic_programming", "algorithms"]),
    
    # strings, sliding_window, hashing
    ("Given a string s, find the length of the longest substring without repeating characters using a sliding window and hash map.", ["strings", "sliding_window", "hashing", "two_pointers", "data_structures", "algorithms"]),
    ("Given two strings s and t of lengths m and n respectively, return the minimum window substring of s such that every character in t is included.", ["strings", "sliding_window", "hashing", "two_pointers", "algorithms"]),
    ("Given two strings s and p, return an array of all the start indices of p's anagrams in s using a sliding window of fixed size.", ["strings", "sliding_window", "hashing", "arrays", "algorithms"]),
    ("Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid using a stack.", ["strings", "stacks", "data_structures", "algorithms"]),
    ("Given a string s, return the longest palindromic substring in s using dynamic programming or expand around center.", ["strings", "dynamic_programming", "two_pointers", "algorithms"]),
    
    # linked_lists, two_pointers
    ("Given the head of a singly linked list, reverse the list and return the reversed list.", ["linked_lists", "two_pointers", "data_structures", "algorithms"]),
    ("Given head, the head of a linked list, determine if the linked list has a cycle in it using Floyd's cycle-finding two pointers.", ["linked_lists", "two_pointers", "data_structures", "algorithms"]),
    ("Merge two sorted linked lists and return it as a sorted list by splicing together the nodes of the first two lists.", ["linked_lists", "sorting", "recursion", "data_structures", "algorithms"]),
    ("Given the head of a linked list, remove the nth node from the end of the list and return its head using fast and slow pointers.", ["linked_lists", "two_pointers", "data_structures", "algorithms"]),
    ("You are given the head of a singly linked-list. The list can be represented as L0 -> L1 -> … -> Ln-1 -> Ln. Reorder the list.", ["linked_lists", "two_pointers", "data_structures", "algorithms"]),
    
    # trees, recursion, search, queues
    ("Given the root of a binary tree, return its maximum depth using recursion and depth-first search.", ["trees", "recursion", "search", "data_structures", "algorithms"]),
    ("Given the root of a binary tree, return the level order traversal of its nodes' values using a breadth-first search queue.", ["trees", "queues", "search", "data_structures", "algorithms"]),
    ("Given the root of a binary search tree and an integer val, find the node in the BST that the node's value equals val.", ["trees", "binary_search", "search", "data_structures", "algorithms"]),
    ("Given the root of a binary tree, invert the tree, and return its root recursively.", ["trees", "recursion", "data_structures", "algorithms"]),
    ("Given a binary tree, find the lowest common ancestor (LCA) of two given nodes in the tree.", ["trees", "recursion", "search", "data_structures", "algorithms"]),
    ("Serialize and deserialize a binary tree using pre-order traversal and queue reconstruction.", ["trees", "queues", "strings", "recursion", "data_structures"]),
    
    # heaps, queues, sorting
    ("Given an integer array nums and an integer k, return the kth largest element in the array using a min-heap priority queue.", ["heaps", "queues", "sorting", "arrays", "data_structures", "algorithms"]),
    ("Merge k sorted linked lists and return it as one sorted list using a min-heap priority queue to compare heads.", ["heaps", "linked_lists", "queues", "sorting", "data_structures", "algorithms"]),
    ("Find the median from a continuous data stream of integers using two heaps (a max-heap for lower half and min-heap for upper half).", ["heaps", "queues", "data_structures", "algorithms", "complexity"]),
    ("Given an array of points where points[i] = [xi, yi] and an integer k, return the k closest points to the origin using a max-heap.", ["heaps", "sorting", "arrays", "data_structures", "algorithms"]),
    ("Given an array of meeting time intervals consisting of start and end times, find the minimum number of conference rooms required using a priority queue.", ["heaps", "greedy", "sorting", "arrays", "data_structures", "algorithms"]),
    
    # stacks, queues
    ("Implement a first in first out (FIFO) queue using only two stacks. The implemented queue should support push, peek, pop, and empty.", ["stacks", "queues", "data_structures"]),
    ("Design a stack that supports push, pop, top, and retrieving the minimum element in constant O(1) time complexity.", ["stacks", "complexity", "data_structures", "algorithms"]),
    ("Given an array of integers temperatures represents daily temperatures, return an array answer such that answer[i] is the number of days until a warmer temperature using a monotonic stack.", ["stacks", "arrays", "data_structures", "algorithms"]),
    ("Evaluate the value of an arithmetic expression in Reverse Polish Notation using a stack to push operands and pop operators.", ["stacks", "strings", "arrays", "data_structures", "algorithms"]),
    ("Design a circular queue data structure supporting enQueue, deQueue, Front, Rear, isEmpty, and isFull without resizing.", ["queues", "arrays", "data_structures"]),
    ("Given a string containing just parentheses and brackets, determine if the input string is valid using a stack.", ["stacks", "strings", "data_structures", "algorithms"]),
    ("Given an array of integers, find the next greater element for each element using a monotonic stack data structure.", ["stacks", "arrays", "data_structures", "algorithms"]),
    ("Design a min stack that supports push, pop, top, and retrieving minimum element in constant time.", ["stacks", "data_structures", "complexity"]),
    ("Simplify the given absolute path for a Unix-style file system using a stack.", ["stacks", "strings", "data_structures", "algorithms"]),
    ("Given an array of integers heights representing the histogram's bar height, find the area of the largest rectangle in the histogram using a monotonic stack.", ["stacks", "arrays", "data_structures", "algorithms"]),

    
    # graphs, search, recursion
    ("There are a total of numCourses courses you have to take, labeled from 0 to numCourses - 1. Find if it is possible to finish all courses using topological sort and BFS/DFS cycle detection.", ["graphs", "search", "queues", "recursion", "data_structures", "algorithms"]),
    ("Given an m x n 2D binary grid grid which represents a map of '1's (land) and '0's (water), return the number of islands using depth-first search.", ["graphs", "search", "recursion", "arrays", "algorithms"]),
    ("You are given an array of network travel times edges. Find the minimum time to reach all nodes from source node k using Dijkstra's shortest path algorithm.", ["graphs", "heaps", "search", "algorithms", "complexity"]),
    ("Given two words, beginWord and endWord, and a dictionary wordList, return the number of words in the shortest transformation sequence using bidirectional BFS.", ["graphs", "search", "queues", "hashing", "strings", "algorithms"]),
    ("Given a directed graph, determine if the graph contains any strongly connected components using Tarjan's or Kosaraju's algorithm.", ["graphs", "search", "recursion", "algorithms"]),
    
    # dynamic_programming, greedy, complexity
    ("Given an integer array coins and an integer amount, return the fewest number of coins needed to make up that amount using bottom-up dynamic programming.", ["dynamic_programming", "arrays", "complexity", "algorithms"]),
    ("Given two strings text1 and text2, return the length of their longest common subsequence using a 2D dynamic programming table.", ["dynamic_programming", "strings", "complexity", "algorithms"]),
    ("You are given an array of prices where prices[i] is the price of a given stock on the ith day. Maximize profit with at most two transactions using dynamic programming.", ["dynamic_programming", "arrays", "algorithms"]),
    ("Given an integer array nums, return the length of the longest strictly increasing subsequence in O(n log n) time complexity using DP with binary search.", ["dynamic_programming", "binary_search", "arrays", "complexity", "algorithms"]),
    ("Given an array of intervals where intervals[i] = [starti, endi], return the minimum number of intervals you need to remove to make the rest non-overlapping using a greedy choice.", ["greedy", "sorting", "arrays", "algorithms"]),
    ("You are given an integer array nums. You are initially positioned at the first index, and each element represents your maximum jump length. Return true if you can reach the last index greedily.", ["greedy", "dynamic_programming", "arrays", "algorithms"]),
    
    # backtracking, recursion
    ("Given an integer array nums of unique elements, return all possible subsets (the power set) using recursive backtracking.", ["backtracking", "recursion", "arrays", "algorithms"]),
    ("Given an array nums of distinct integers, return all the possible permutations using backtracking.", ["backtracking", "recursion", "arrays", "algorithms"]),
    ("Given a collection of candidate numbers and a target number, find all unique combinations in candidates where the candidate numbers sum to target using backtracking.", ["backtracking", "recursion", "sorting", "arrays", "algorithms"]),
    ("The n-queens puzzle is the problem of placing n queens on an n x n chessboard such that no two queens attack each other. Return all distinct solutions using backtracking.", ["backtracking", "recursion", "arrays", "algorithms"]),
    ("Given an m x n grid of characters board and a string word, return true if word exists in the grid using DFS backtracking and pruning.", ["backtracking", "recursion", "search", "arrays", "strings", "algorithms"]),
    
    # binary_search, complexity
    ("Given a sorted array of integers nums and an integer target, write a function to search target in nums in O(log n) runtime complexity.", ["binary_search", "search", "arrays", "complexity", "algorithms"]),
    ("Suppose an array of length n sorted in ascending order is rotated between 1 and n times. Find the minimum element in O(log n) time using binary search.", ["binary_search", "search", "arrays", "complexity", "algorithms"]),
    ("Given an array of integers citations, compute the researcher's h-index in O(log n) time using binary search on the sorted citations.", ["binary_search", "sorting", "arrays", "complexity", "algorithms"]),
    ("You are given an m x n integer matrix matrix with the properties that integers in each row are sorted and first integer of each row is greater than last of previous. Search in O(log(m*n)).", ["binary_search", "search", "arrays", "complexity", "algorithms"]),
]


def load_dataset(max_samples: int = 2500) -> Tuple[List[str], List[List[str]]]:
    """
    Loads samples from TACO via TACODatasetLoader, applies the mapping layer,
    and blends in canonical interview templates for comprehensive class coverage.
    """
    loader = TACODatasetLoader()
    texts: List[str] = []
    labels: List[List[str]] = []

    count = 0
    for sample in loader.load_samples(limit=max_samples):
        if sample.question_text and sample.canonical_skills:
            texts.append(sample.question_text)
            labels.append(sample.canonical_skills)
            count += 1

    logger.info("Loaded %d genuine samples from TACO dataset.", count)

    # Augment with interview seeds (replicated 4x to ensure rich support for rarer classes)
    for _ in range(4):
        for text, skills in INTERVIEW_AUGMENTATION_SAMPLES:
            texts.append(text)
            labels.append(skills)

    logger.info("Total samples prepared for training: %d across %d canonical skills.", len(texts), len(CANONICAL_SKILLS))
    return texts, labels


def evaluate_multilabel_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_probs: np.ndarray,
    skill_names: List[str]
) -> Dict[str, Any]:
    """Computes all required multi-label evaluation metrics."""
    micro_f1 = float(f1_score(y_true, y_pred, average="micro", zero_division=0))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    
    micro_precision = float(precision_score(y_true, y_pred, average="micro", zero_division=0))
    macro_precision = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    
    micro_recall = float(recall_score(y_true, y_pred, average="micro", zero_division=0))
    macro_recall = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    
    h_loss = float(hamming_loss(y_true, y_pred))

    # Per-label metrics
    per_label_f1 = f1_score(y_true, y_pred, average=None, zero_division=0)
    per_label_p = precision_score(y_true, y_pred, average=None, zero_division=0)
    per_label_r = recall_score(y_true, y_pred, average=None, zero_division=0)

    per_label_stats = {}
    for i, skill in enumerate(skill_names):
        support = int(np.sum(y_true[:, i]))
        per_label_stats[skill] = {
            "f1": round(float(per_label_f1[i]), 4),
            "precision": round(float(per_label_p[i]), 4),
            "recall": round(float(per_label_r[i]), 4),
            "support": support
        }

    return {
        "micro_f1": round(micro_f1, 4),
        "macro_f1": round(macro_f1, 4),
        "precision": {
            "micro": round(micro_precision, 4),
            "macro": round(macro_precision, 4),
        },
        "recall": {
            "micro": round(micro_recall, 4),
            "macro": round(macro_recall, 4),
        },
        "hamming_loss": round(h_loss, 4),
        "per_label": per_label_stats,
    }


def train_classical_model(
    X_train_texts: List[str],
    y_train: np.ndarray,
    X_test_texts: List[str],
    y_test: np.ndarray,
    skill_names: List[str],
    threshold: float = 0.30
) -> Tuple[Any, Any, Dict[str, Any]]:
    """
    Trains TF-IDF + One-vs-Rest Logistic Regression classifier.
    Returns (vectorizer, classifier, evaluation_metrics).
    """
    logger.info("Fitting TF-IDF Vectorizer...")
    vectorizer = TfidfVectorizer(
        max_features=6000,
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True
    )
    X_train_vec = vectorizer.fit_transform(X_train_texts)
    X_test_vec = vectorizer.transform(X_test_texts)

    logger.info("Training OneVsRestClassifier (LogisticRegression) on %d samples...", X_train_vec.shape[0])
    base_lr = LogisticRegression(C=2.0, max_iter=1000, class_weight="balanced", random_state=42)
    classifier = OneVsRestClassifier(base_lr, n_jobs=1)
    classifier.fit(X_train_vec, y_train)

    logger.info("Evaluating Classical Model on %d test samples...", X_test_vec.shape[0])
    y_probs = classifier.predict_proba(X_test_vec)
    y_pred = (y_probs >= threshold).astype(int)

    # Ensure at least 1 prediction per sample
    for i in range(len(y_pred)):
        if np.sum(y_pred[i]) == 0:
            best_idx = int(np.argmax(y_probs[i]))
            y_pred[i, best_idx] = 1

    metrics = evaluate_multilabel_predictions(y_test, y_pred, y_probs, skill_names)
    metrics["model_type"] = "TF-IDF + OneVsRest(LogisticRegression)"
    metrics["threshold"] = threshold
    return vectorizer, classifier, metrics


def evaluate_lightweight_transformer_option(
    X_train_texts: List[str],
    y_train: np.ndarray,
    X_test_texts: List[str],
    y_test: np.ndarray,
    skill_names: List[str],
    threshold: float = 0.30
) -> Dict[str, Any]:
    """
    Evaluates a lightweight transformer encoder (sentence-transformers / MiniLM / DistilBERT)
    representation against the test set for comparative evaluation.
    """
    logger.info("Evaluating lightweight transformer option...")
    try:
        from ml.features.text_embeddings import TextEmbeddingExtractor
        extractor = TextEmbeddingExtractor()
        
        # Subsample for fast evaluation if large
        eval_size = min(300, len(X_train_texts))
        test_eval_size = min(150, len(X_test_texts))
        
        logger.info("Extracting transformer embeddings for %d train / %d test samples...", eval_size, test_eval_size)
        X_train_emb = extractor.encode(X_train_texts[:eval_size])
        X_test_emb = extractor.encode(X_test_texts[:test_eval_size])
        
        sub_y_train = y_train[:eval_size]
        sub_y_test = y_test[:test_eval_size]

        clf = OneVsRestClassifier(LogisticRegression(C=1.5, max_iter=500, class_weight="balanced", random_state=42))
        clf.fit(X_train_emb, sub_y_train)
        
        y_probs = clf.predict_proba(X_test_emb)
        y_pred = (y_probs >= threshold).astype(int)
        for i in range(len(y_pred)):
            if np.sum(y_pred[i]) == 0:
                y_pred[i, int(np.argmax(y_probs[i]))] = 1

        metrics = evaluate_multilabel_predictions(sub_y_test, y_pred, y_probs, skill_names)
        metrics["model_type"] = "Lightweight Transformer (all-MiniLM-L6-v2) + OVR Head"
        metrics["threshold"] = threshold
        metrics["evaluated_samples"] = test_eval_size
        return metrics
    except Exception as e:
        logger.warning("Could not complete transformer evaluation: %s. Returning fallback comparison.", e)
        return {
            "model_type": "Lightweight Transformer (all-MiniLM-L6-v2)",
            "error": str(e),
            "status": "skipped_due_to_environment"
        }


def run_pipeline(
    output_model_path: str = "ml/models/weights/skill_classifier.joblib",
    output_eval_path: str = "ml/models/weights/skill_evaluation.json",
    max_samples: int = 2500,
    random_state: int = 42
) -> Dict[str, Any]:
    """Executes the full dataset loading, mapping, training, evaluation, and artifact saving pipeline."""
    start_time = time.time()
    logger.info("Starting Multi-Label Question-Skill Classification Training Pipeline...")

    # 1. Load data
    texts, raw_labels = load_dataset(max_samples=max_samples)

    # 2. Fit MultiLabelBinarizer
    mlb = MultiLabelBinarizer(classes=CANONICAL_SKILLS)
    Y = mlb.fit_transform(raw_labels)

    # 3. Train / Test Split (80 / 20)
    X_train_texts, X_test_texts, y_train, y_test = train_test_split(
        texts, Y, test_size=0.2, random_state=random_state
    )
    logger.info("Split dataset: Train=%d, Test=%d", len(X_train_texts), len(X_test_texts))

    # 4. Train Classical Model (TF-IDF + OneVsRest)
    vectorizer, classifier, classical_metrics = train_classical_model(
        X_train_texts, y_train, X_test_texts, y_test, CANONICAL_SKILLS, threshold=0.30
    )

    # 5. Evaluate Lightweight Transformer Option
    transformer_metrics = evaluate_lightweight_transformer_option(
        X_train_texts, y_train, X_test_texts, y_test, CANONICAL_SKILLS, threshold=0.30
    )

    elapsed_time = round(time.time() - start_time, 2)
    logger.info("Training completed in %s seconds.", elapsed_time)
    logger.info("Classical Model - Micro F1: %s, Macro F1: %s, Hamming Loss: %s",
                classical_metrics["micro_f1"], classical_metrics["macro_f1"], classical_metrics["hamming_loss"])

    # 6. Save model weights
    out_model = Path(output_model_path)
    out_model.parent.mkdir(parents=True, exist_ok=True)
    
    artifact = {
        "model_version": "1.0.0",
        "model_type": "TF-IDF + OneVsRest(LogisticRegression)",
        "vectorizer": vectorizer,
        "classifier": classifier,
        "canonical_skills": CANONICAL_SKILLS,
        "threshold": 0.35,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "trained_samples": len(X_train_texts),
    }
    joblib.dump(artifact, out_model)
    logger.info("Model weights saved to %s", out_model)

    # 7. Save evaluation report
    eval_report = {
        "task": "Question Skill/Topic Multi-label Classification",
        "dataset": "BAAI/TACO",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed_time,
        "taxonomy": CANONICAL_SKILLS,
        "classical_baseline": classical_metrics,
        "transformer_option": transformer_metrics,
        "sample_counts": {
            "total": len(texts),
            "train": len(X_train_texts),
            "test": len(X_test_texts),
        }
    }

    out_eval = Path(output_eval_path)
    out_eval.parent.mkdir(parents=True, exist_ok=True)
    with open(out_eval, "w", encoding="utf-8") as f:
        json.dump(eval_report, f, indent=2)
    logger.info("Evaluation report saved to %s", out_eval)

    # 8. Generate Documentation Report
    docs_report_path = Path("docs/SKILL_CLASSIFIER_EVALUATION.md")
    docs_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(docs_report_path, "w", encoding="utf-8") as f:
        f.write("# TACO Multi-Label Question-Skill Classifier Evaluation Report\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"**Dataset:** BAAI/TACO (Problem statements, tags, skill_types)\n")
        f.write(f"**Total Samples:** {len(texts)} (Train: {len(X_train_texts)}, Test: {len(X_test_texts)})\n\n")
        
        f.write("## 1. Executive Summary\n\n")
        f.write(f"| Metric | TF-IDF + One-vs-Rest (Production) | Lightweight Transformer |\n")
        f.write(f"| :--- | :--- | :--- |\n")
        f.write(f"| **Micro F1** | **{classical_metrics['micro_f1']:.4f}** | {transformer_metrics.get('micro_f1', 'N/A')} |\n")
        f.write(f"| **Macro F1** | **{classical_metrics['macro_f1']:.4f}** | {transformer_metrics.get('macro_f1', 'N/A')} |\n")
        f.write(f"| **Micro Precision** | {classical_metrics['precision']['micro']:.4f} | {transformer_metrics.get('precision', {}).get('micro', 'N/A')} |\n")
        f.write(f"| **Macro Precision** | {classical_metrics['precision']['macro']:.4f} | {transformer_metrics.get('precision', {}).get('macro', 'N/A')} |\n")
        f.write(f"| **Micro Recall** | {classical_metrics['recall']['micro']:.4f} | {transformer_metrics.get('recall', {}).get('micro', 'N/A')} |\n")
        f.write(f"| **Macro Recall** | {classical_metrics['recall']['macro']:.4f} | {transformer_metrics.get('recall', {}).get('macro', 'N/A')} |\n")
        f.write(f"| **Hamming Loss** | **{classical_metrics['hamming_loss']:.4f}** | {transformer_metrics.get('hamming_loss', 'N/A')} |\n\n")

        f.write("## 2. Per-Label Breakdown (Canonical Taxonomy)\n\n")
        f.write("| Canonical Skill | Precision | Recall | F1 Score | Test Support |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for skill in CANONICAL_SKILLS:
            st = classical_metrics["per_label"].get(skill, {})
            f.write(f"| `{skill}` | {st.get('precision', 0.0):.4f} | {st.get('recall', 0.0):.4f} | {st.get('f1', 0.0):.4f} | {st.get('support', 0)} |\n")
        
        f.write("\n## 3. Taxonomy Mapping Layer\n\n")
        f.write("The mapping layer converts raw competitive programming tags from TACO (`'Dynamic programming'`, `'Segment trees revisited'`, `'Range queries'`, `'Spanning trees'`, etc.) and problem text signals into the 21 canonical skills for Interview-ai-er.\n")
        f.write("This prevents raw competitive programming tag pollution while preserving algorithmic semantics.\n")

    logger.info("Markdown documentation saved to %s", docs_report_path)
    return eval_report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    run_pipeline()

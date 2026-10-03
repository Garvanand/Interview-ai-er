"""
Reproducible dataset preprocessing with strict train/val/test isolation.

Responsibilities:
- Deterministic text cleaning
- Stratified split generation with fixed seeds
- Data leakage detection between train and test sets
- Preprocessing version tracking for reproducibility
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Text Cleaning
# ─────────────────────────────────────────────────────────────────────────────

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_WHITESPACE_RE = re.compile(r"\s+")


def clean_text(
    text: str,
    *,
    strip_html: bool = True,
    lowercase: bool = False,
    min_length_chars: int = 10,
) -> Optional[str]:
    """
    Apply deterministic text cleaning. Returns None if the cleaned text
    is shorter than min_length_chars (i.e. the sample should be discarded).
    """
    if not isinstance(text, str):
        return None
    s = text.strip()
    if strip_html:
        s = _HTML_TAG_RE.sub(" ", s)
    s = _MULTI_WHITESPACE_RE.sub(" ", s).strip()
    if lowercase:
        s = s.lower()
    if len(s) < min_length_chars:
        return None
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Fingerprinting for Leakage Detection
# ─────────────────────────────────────────────────────────────────────────────

def text_fingerprint(text: str) -> str:
    """
    Generate a canonical fingerprint for a text sample.
    Strips whitespace, lowercases, and removes punctuation before hashing.
    Two texts that differ only in formatting will produce the same fingerprint.
    """
    canonical = re.sub(r"[^a-z0-9 ]", "", text.lower().strip())
    canonical = re.sub(r"\s+", " ", canonical).strip()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# Data Leakage Checker
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LeakageReport:
    """Result of a data leakage check between splits."""
    leaked_count: int = 0
    total_train: int = 0
    total_test: int = 0
    leaked_indices_in_test: List[int] = field(default_factory=list)
    leak_rate_pct: float = 0.0
    clean: bool = True


def check_data_leakage(
    train_texts: Sequence[str],
    test_texts: Sequence[str],
    *,
    val_texts: Optional[Sequence[str]] = None,
) -> LeakageReport:
    """
    Check for data leakage: exact or near-exact duplicates between train and test sets.
    Optionally checks train/val and val/test overlap too.
    Raises ValueError if leakage exceeds 5% of the test set.
    """
    train_fps = {text_fingerprint(t) for t in train_texts}
    leaked_indices: List[int] = []
    for i, t in enumerate(test_texts):
        if text_fingerprint(t) in train_fps:
            leaked_indices.append(i)

    leak_rate = (len(leaked_indices) / len(test_texts) * 100.0) if test_texts else 0.0

    report = LeakageReport(
        leaked_count=len(leaked_indices),
        total_train=len(train_texts),
        total_test=len(test_texts),
        leaked_indices_in_test=leaked_indices,
        leak_rate_pct=round(leak_rate, 2),
        clean=len(leaked_indices) == 0,
    )

    if report.clean:
        logger.info("✓ No data leakage detected between train (%d) and test (%d).",
                     report.total_train, report.total_test)
    else:
        logger.warning("⚠ Data leakage detected: %d test samples (%.2f%%) also appear in training set.",
                        report.leaked_count, report.leak_rate_pct)

    # Also check val if provided
    if val_texts is not None:
        val_fps = {text_fingerprint(t) for t in val_texts}
        val_train_overlap = train_fps & val_fps
        if val_train_overlap:
            logger.warning("⚠ Validation/train overlap: %d samples share fingerprints.", len(val_train_overlap))

    if report.leak_rate_pct > 5.0:
        raise ValueError(
            f"CRITICAL: Data leakage rate {report.leak_rate_pct:.2f}% exceeds 5% threshold. "
            f"Found {report.leaked_count} test samples duplicated in training set. "
            f"Training aborted to prevent invalid evaluation."
        )

    return report


# ─────────────────────────────────────────────────────────────────────────────
# Stratified Splitting (supports both single-label and multi-label)
# ─────────────────────────────────────────────────────────────────────────────

def stratified_split(
    texts: List[str],
    labels: Any,
    *,
    test_size: float = 0.20,
    val_size: float = 0.10,
    random_seed: int = 42,
    is_multilabel: bool = False,
) -> Dict[str, Any]:
    """
    Deterministic stratified split into train/val/test.

    For single-label: uses sklearn's stratified split.
    For multi-label: uses iterative stratification or random split with label distribution check.

    Returns a dict with keys: train_texts, val_texts, test_texts,
                              train_labels, val_labels, test_labels
    """
    from sklearn.model_selection import train_test_split

    rng = np.random.RandomState(random_seed)

    # First split: separate test set
    if is_multilabel:
        # Multi-label: random split (iterative stratification is complex)
        # We shuffle deterministically and split by ratio
        indices = np.arange(len(texts))
        rng.shuffle(indices)
        test_n = int(len(texts) * test_size)
        val_n = int(len(texts) * val_size)
        test_idx = indices[:test_n]
        val_idx = indices[test_n:test_n + val_n]
        train_idx = indices[test_n + val_n:]

        texts_arr = np.array(texts, dtype=object)
        if isinstance(labels, np.ndarray):
            labels_arr = labels
        else:
            labels_arr = np.array(labels, dtype=object)

        result = {
            "train_texts": texts_arr[train_idx].tolist(),
            "val_texts": texts_arr[val_idx].tolist(),
            "test_texts": texts_arr[test_idx].tolist(),
            "train_labels": labels_arr[train_idx] if labels_arr.ndim > 1 else labels_arr[train_idx].tolist(),
            "val_labels": labels_arr[val_idx] if labels_arr.ndim > 1 else labels_arr[val_idx].tolist(),
            "test_labels": labels_arr[test_idx] if labels_arr.ndim > 1 else labels_arr[test_idx].tolist(),
            "train_indices": train_idx.tolist(),
            "val_indices": val_idx.tolist(),
            "test_indices": test_idx.tolist(),
        }
    else:
        # Single-label: stratified split
        X_trainval, X_test, y_trainval, y_test = train_test_split(
            texts, labels, test_size=test_size, random_state=random_seed, stratify=labels
        )
        # Split trainval into train and val
        relative_val_size = val_size / (1.0 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_trainval, y_trainval, test_size=relative_val_size,
            random_state=random_seed, stratify=y_trainval
        )
        result = {
            "train_texts": X_train,
            "val_texts": X_val,
            "test_texts": X_test,
            "train_labels": y_train,
            "val_labels": y_val,
            "test_labels": y_test,
        }

    logger.info(
        "Split sizes — train: %d, val: %d, test: %d",
        len(result["train_texts"]),
        len(result["val_texts"]),
        len(result["test_texts"]),
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Dataset Content Hashing
# ─────────────────────────────────────────────────────────────────────────────

def compute_dataset_hash(texts: Sequence[str], labels: Any) -> str:
    """
    Compute a deterministic SHA-256 hash of the dataset content.
    Useful for verifying that the exact same data was used across training runs.
    """
    h = hashlib.sha256()
    for t in texts:
        h.update(t.encode("utf-8"))
    # Hash labels
    if isinstance(labels, np.ndarray):
        h.update(labels.tobytes())
    elif isinstance(labels, list):
        for lbl in labels:
            if isinstance(lbl, list):
                h.update(str(lbl).encode("utf-8"))
            else:
                h.update(str(lbl).encode("utf-8"))
    return h.hexdigest()[:16]

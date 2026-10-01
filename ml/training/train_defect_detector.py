"""
Fine-tuning pipeline for Code Defect/Vulnerability Detection.
Category: FINE-TUNED BY US.
Base: microsoft/codebert-base
Dataset: CodeXGLUE Defect Detection (Devign benchmark)
License: Computational Use of Data Agreement (C-UDA) — non-commercial research only.

This pipeline:
1. Downloads the CodeXGLUE defect detection dataset from HuggingFace
2. Tokenizes code using CodeBERT's tokenizer
3. Fine-tunes a binary classification head on top of frozen/unfrozen CodeBERT
4. Evaluates with accuracy, precision, recall, F1, ROC-AUC, confusion matrix
5. Saves the model, tokenizer, and evaluation report

The resulting model outputs a defect_probability, risk_band, and confidence —
used as an ADDITIONAL code-risk signal, NOT as proof of code incorrectness.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Suppress soxr/numpy2 incompatibility (non-critical for text-only fine-tuning)
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
try:
    import numpy as np
except Exception:
    warnings.warn("NumPy import issue detected — attempting workaround")
    import numpy as np

logger = logging.getLogger(__name__)

# ─── Constants ─────────────────────────────────────────────────────
MODEL_NAME = "microsoft/codebert-base"
DATASET_ID = "google/code_x_glue_cc_defect_detection"
MODEL_VERSION = "codebert_defect_v1.0"
MAX_SEQ_LENGTH = 512
DEFAULT_OUTPUT_DIR = "ml/models/weights/codebert_defect"


# ─── Torch Dataset wrapper ────────────────────────────────────────
class CodeDefectDataset:
    """PyTorch-compatible dataset for code defect detection."""

    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        import torch
        item = {k: torch.tensor(v[idx]) for k, v in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx], dtype=torch.long)
        return item

    def __len__(self):
        return len(self.labels)


# ─── Metrics computation ──────────────────────────────────────────
def compute_metrics(eval_pred) -> Dict[str, float]:
    """Compute accuracy, precision, recall, F1, and ROC-AUC."""
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    logits, labels = eval_pred
    # Softmax to get probabilities
    probs = np.exp(logits) / np.exp(logits).sum(axis=-1, keepdims=True)
    predictions = np.argmax(logits, axis=-1)

    acc = accuracy_score(labels, predictions)
    prec = precision_score(labels, predictions, zero_division=0)
    rec = recall_score(labels, predictions, zero_division=0)
    f1 = f1_score(labels, predictions, zero_division=0)

    try:
        roc = roc_auc_score(labels, probs[:, 1])
    except Exception:
        roc = 0.0

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": round(roc, 4),
    }


# ─── Full evaluation report ───────────────────────────────────────
def generate_evaluation_report(
    trainer, test_dataset, labels: List[int], output_dir: Path
) -> Dict[str, Any]:
    """Generate comprehensive evaluation report with confusion matrix."""
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    logger.info("Generating evaluation report on test set...")
    predictions = trainer.predict(test_dataset)
    logits = predictions.predictions
    probs = np.exp(logits) / np.exp(logits).sum(axis=-1, keepdims=True)
    pred_labels = np.argmax(logits, axis=-1)

    acc = accuracy_score(labels, pred_labels)
    prec = precision_score(labels, pred_labels, zero_division=0)
    rec = recall_score(labels, pred_labels, zero_division=0)
    f1 = f1_score(labels, pred_labels, zero_division=0)
    try:
        roc = roc_auc_score(labels, probs[:, 1])
    except Exception:
        roc = 0.0

    cm = confusion_matrix(labels, pred_labels).tolist()
    cls_report = classification_report(
        labels, pred_labels, target_names=["clean", "defective"], output_dict=True
    )

    report = {
        "model_version": MODEL_VERSION,
        "base_model": MODEL_NAME,
        "dataset": DATASET_ID,
        "dataset_license": "Computational Use of Data Agreement (C-UDA)",
        "evaluation_split": "test",
        "metrics": {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "roc_auc": round(roc, 4),
        },
        "confusion_matrix": {
            "labels": ["clean", "defective"],
            "matrix": cm,
            "description": "[[TN, FP], [FN, TP]]",
        },
        "per_class_report": {
            k: {
                "precision": round(v.get("precision", 0), 4),
                "recall": round(v.get("recall", 0), 4),
                "f1-score": round(v.get("f1-score", 0), 4),
                "support": v.get("support", 0),
            }
            for k, v in cls_report.items()
            if k in ("clean", "defective")
        },
        "total_test_samples": len(labels),
        "label_distribution": {
            "clean": int(sum(1 for l in labels if l == 0)),
            "defective": int(sum(1 for l in labels if l == 1)),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    report_path = output_dir / "defect_evaluation.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("Evaluation report saved to %s", report_path)

    return report


# ─── Main training pipeline ───────────────────────────────────────
def fine_tune_codebert_defect_model(
    output_dir: str = DEFAULT_OUTPUT_DIR,
    epochs: int = 3,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    max_train_samples: int = 0,
    max_eval_samples: int = 0,
    warmup_ratio: float = 0.1,
    weight_decay: float = 0.01,
    freeze_encoder_layers: int = 0,
) -> Dict[str, Any]:
    """
    Fine-tunes CodeBERT classification head on CodeXGLUE defect detection.

    Args:
        output_dir: Where to save the model, tokenizer, and reports.
        epochs: Number of training epochs.
        batch_size: Per-device batch size.
        learning_rate: AdamW learning rate.
        max_train_samples: Limit training samples (0 = all).
        max_eval_samples: Limit evaluation samples (0 = all).
        warmup_ratio: Fraction of training steps for LR warmup.
        weight_decay: L2 regularization weight.
        freeze_encoder_layers: Number of encoder layers to freeze (0 = train all).

    Returns:
        Evaluation report dict.
    """
    import torch

    # Workaround: Mock soxr if it crashes on numpy 2.x (not needed for text fine-tuning)
    try:
        import soxr  # noqa: F401
    except (ImportError, Exception):
        import types
        sys.modules["soxr"] = types.ModuleType("soxr")

    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
        EarlyStoppingCallback,
    )
    from datasets import load_dataset

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Device: %s | PyTorch: %s", device, torch.__version__)

    # ── Step 1: Load dataset ──
    logger.info("Loading CodeXGLUE defect detection dataset...")
    raw_dataset = load_dataset(DATASET_ID)

    train_data = raw_dataset["train"]
    val_data = raw_dataset["validation"]
    test_data = raw_dataset["test"]

    logger.info(
        "Dataset sizes — train: %d, validation: %d, test: %d",
        len(train_data), len(val_data), len(test_data),
    )

    # ── Step 2: Subsample if requested ──
    if max_train_samples > 0 and max_train_samples < len(train_data):
        train_data = train_data.shuffle(seed=42).select(range(max_train_samples))
        logger.info("Subsampled training set to %d samples", len(train_data))
    if max_eval_samples > 0 and max_eval_samples < len(val_data):
        val_data = val_data.shuffle(seed=42).select(range(max_eval_samples))
    if max_eval_samples > 0 and max_eval_samples < len(test_data):
        test_data = test_data.shuffle(seed=42).select(range(max_eval_samples))

    # ── Step 3: Inspect class distribution ──
    train_labels = [item["target"] for item in train_data]
    val_labels = [item["target"] for item in val_data]
    test_labels = [item["target"] for item in test_data]

    n_pos_train = sum(train_labels)
    n_neg_train = len(train_labels) - n_pos_train
    logger.info(
        "Training class distribution — clean: %d, defective: %d (%.1f%% defective)",
        n_neg_train, n_pos_train, 100.0 * n_pos_train / len(train_labels),
    )

    # ── Step 4: Tokenize ──
    logger.info("Loading CodeBERT tokenizer: %s", MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    def tokenize_batch(dataset_split):
        texts = list(dataset_split["func"])
        return tokenizer(
            texts,
            padding="max_length",
            truncation=True,
            max_length=MAX_SEQ_LENGTH,
        )

    logger.info("Tokenizing datasets...")
    train_encodings = tokenize_batch(train_data)
    val_encodings = tokenize_batch(val_data)
    test_encodings = tokenize_batch(test_data)

    train_dataset = CodeDefectDataset(train_encodings, train_labels)
    val_dataset = CodeDefectDataset(val_encodings, val_labels)
    test_dataset = CodeDefectDataset(test_encodings, test_labels)

    # ── Step 5: Load model ──
    logger.info("Loading CodeBERT model with binary classification head...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2,
        id2label={0: "clean", 1: "defective"},
        label2id={"clean": 0, "defective": 1},
    )

    # Optionally freeze lower encoder layers
    if freeze_encoder_layers > 0:
        for i, layer in enumerate(model.roberta.encoder.layer):
            if i < freeze_encoder_layers:
                for param in layer.parameters():
                    param.requires_grad = False
        logger.info("Froze first %d encoder layers", freeze_encoder_layers)

    model.to(device)

    total_params = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(
        "Model parameters — total: %s, trainable: %s (%.1f%%)",
        f"{total_params:,}", f"{trainable:,}", 100.0 * trainable / total_params,
    )

    # ── Step 6: Training configuration ──
    training_args = TrainingArguments(
        output_dir=str(out_path / "checkpoints"),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size * 2,
        learning_rate=learning_rate,
        warmup_steps=max(1, int(warmup_ratio * (len(train_dataset) // max(1, batch_size)) * epochs)),
        weight_decay=weight_decay,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        logging_steps=50,
        save_total_limit=2,
        fp16=(device == "cuda"),
        report_to="none",
        seed=42,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    # ── Step 7: Train ──
    t0 = time.time()
    logger.info("Starting fine-tuning for %d epochs...", epochs)
    train_result = trainer.train()
    train_time = time.time() - t0
    logger.info(
        "Training complete in %.1f seconds (%.1f min). Loss: %.4f",
        train_time, train_time / 60, train_result.training_loss,
    )

    # ── Step 8: Save model & tokenizer ──
    logger.info("Saving model and tokenizer to %s", out_path)
    trainer.save_model(str(out_path))
    tokenizer.save_pretrained(str(out_path))

    # Save training metadata
    train_metadata = {
        "model_version": MODEL_VERSION,
        "base_model": MODEL_NAME,
        "dataset": DATASET_ID,
        "dataset_license": "Computational Use of Data Agreement (C-UDA)",
        "training_samples": len(train_dataset),
        "validation_samples": len(val_dataset),
        "test_samples": len(test_dataset),
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "warmup_ratio": warmup_ratio,
        "weight_decay": weight_decay,
        "max_seq_length": MAX_SEQ_LENGTH,
        "frozen_layers": freeze_encoder_layers,
        "total_params": total_params,
        "trainable_params": trainable,
        "training_loss": round(train_result.training_loss, 4),
        "training_time_seconds": round(train_time, 1),
        "device": device,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(out_path / "training_metadata.json", "w") as f:
        json.dump(train_metadata, f, indent=2)

    # ── Step 9: Evaluate on test set ──
    report = generate_evaluation_report(trainer, test_dataset, test_labels, out_path)

    logger.info("═══ EVALUATION RESULTS ═══")
    for metric, value in report["metrics"].items():
        logger.info("  %s: %.4f", metric, value)
    logger.info("Confusion Matrix: %s", report["confusion_matrix"]["matrix"])

    return report


# ─── CLI entry point ──────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Fine-tune CodeBERT on CodeXGLUE defect detection"
    )
    parser.add_argument(
        "--output_dir", type=str, default=DEFAULT_OUTPUT_DIR,
        help="Directory to save model artifacts",
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--learning_rate", type=float, default=2e-5)
    parser.add_argument(
        "--max_train_samples", type=int, default=0,
        help="Limit training samples (0 = all)",
    )
    parser.add_argument(
        "--max_eval_samples", type=int, default=0,
        help="Limit evaluation samples (0 = all)",
    )
    parser.add_argument(
        "--freeze_layers", type=int, default=0,
        help="Freeze the first N encoder layers",
    )

    args = parser.parse_args()

    fine_tune_codebert_defect_model(
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        max_train_samples=args.max_train_samples,
        max_eval_samples=args.max_eval_samples,
        freeze_encoder_layers=args.freeze_layers,
    )

"""
Base Training Pipeline Framework.

Provides the common infrastructure for all training pipelines:
- YAML configuration loading
- Reproducibility enforcement (seed, deterministic ops)
- Training metadata collection (dataset hash, preprocessing version, timing)
- Artifact hashing and storage
- Markdown report generation from actual metrics
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Config Loading
# ─────────────────────────────────────────────────────────────────────────────

def load_training_config(config_path: str) -> Dict[str, Any]:
    """Load a YAML training configuration file."""
    try:
        import yaml
    except ImportError:
        raise ImportError("PyYAML is required for config-driven training. Install: pip install pyyaml")

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Training config not found: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger.info("Loaded training config from %s", config_path)
    return config


# ─────────────────────────────────────────────────────────────────────────────
# Reproducibility
# ─────────────────────────────────────────────────────────────────────────────

def set_reproducibility_seed(seed: int):
    """Set random seeds for Python, NumPy, and optionally PyTorch."""
    import random
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)

    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except (ImportError, OSError):
        # torch may not be installed, or its DLLs may fail to load on some platforms
        pass

    logger.info("Reproducibility seed set to %d", seed)


# ─────────────────────────────────────────────────────────────────────────────
# Artifact Hashing
# ─────────────────────────────────────────────────────────────────────────────

def compute_artifact_hash(filepath: str) -> str:
    """Compute SHA-256 hash of a serialized artifact file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Training Metadata
# ─────────────────────────────────────────────────────────────────────────────

class TrainingMetadata:
    """
    Collects and serializes all metadata for a training run.
    Every training run produces a metadata JSON with:
    - dataset_identifier, dataset_version, dataset_hash
    - preprocessing_version
    - random_seed
    - model_base, model_name, model_version
    - hyperparameters
    - training_duration_seconds
    - validation_metrics
    - test_metrics
    - artifact_hash
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.training_duration_seconds: float = 0.0
        self.dataset_hash: str = ""
        self.split_sizes: Dict[str, int] = {}
        self.validation_metrics: Dict[str, Any] = {}
        self.test_metrics: Dict[str, Any] = {}
        self.artifact_hash: str = ""
        self.artifact_path: str = ""
        self._start_time: float = 0.0

    def start_timer(self):
        self._start_time = time.time()
        self.started_at = datetime.now(timezone.utc).isoformat()

    def stop_timer(self):
        self.training_duration_seconds = round(time.time() - self._start_time, 2)
        self.finished_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        model_cfg = self.config.get("model", {})
        dataset_cfg = self.config.get("dataset", {})
        preproc_cfg = self.config.get("preprocessing", {})
        repro_cfg = self.config.get("reproducibility", {})
        hp_cfg = self.config.get("hyperparameters", {})

        return {
            "run_id": f"{model_cfg.get('name', 'unknown')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            "model": {
                "name": model_cfg.get("name"),
                "task": model_cfg.get("task"),
                "version": model_cfg.get("version"),
                "base": model_cfg.get("base"),
            },
            "dataset": {
                "identifier": dataset_cfg.get("identifier"),
                "version": dataset_cfg.get("version"),
                "hash": self.dataset_hash,
            },
            "preprocessing_version": preproc_cfg.get("version"),
            "random_seed": repro_cfg.get("random_seed", 42),
            "hyperparameters": hp_cfg,
            "split_sizes": self.split_sizes,
            "training_duration_seconds": self.training_duration_seconds,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "validation_metrics": self.validation_metrics,
            "test_metrics": self.test_metrics,
            "artifact_path": self.artifact_path,
            "artifact_hash": self.artifact_hash,
            "environment": {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "hostname": platform.node(),
            },
        }

    def save(self, output_path: str):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        logger.info("Training metadata saved to %s", output_path)


# ─────────────────────────────────────────────────────────────────────────────
# Report Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_training_report(
    metadata: TrainingMetadata,
    output_path: str,
    *,
    per_class_metrics: Optional[Dict[str, Dict[str, float]]] = None,
    confusion_matrix: Optional[List[List[int]]] = None,
    class_names: Optional[List[str]] = None,
    additional_sections: Optional[str] = None,
):
    """
    Generate a Markdown training report from actual computed metrics.
    This function must only be called AFTER training and evaluation have completed
    and real metrics are available — it never invents metrics.
    """
    meta = metadata.to_dict()
    model_info = meta.get("model", {})
    dataset_info = meta.get("dataset", {})
    split_info = meta.get("split_sizes", {})
    val_metrics = meta.get("validation_metrics", {})
    test_metrics = meta.get("test_metrics", {})
    hp = meta.get("hyperparameters", {})

    lines: List[str] = []
    lines.append(f"# Training Report: {model_info.get('name', 'Unknown Model')}\n")
    lines.append(f"**Generated:** {meta.get('finished_at', 'N/A')}  ")
    lines.append(f"**Model Version:** {model_info.get('version', 'N/A')}  ")
    lines.append(f"**Task:** {model_info.get('task', 'N/A')}  ")
    lines.append(f"**Base Architecture:** {model_info.get('base', 'N/A')}\n")

    # Reproducibility
    lines.append("## Reproducibility\n")
    lines.append(f"| Parameter | Value |")
    lines.append(f"| :--- | :--- |")
    lines.append(f"| Random Seed | `{meta.get('random_seed', 'N/A')}` |")
    lines.append(f"| Dataset Hash | `{dataset_info.get('hash', 'N/A')}` |")
    lines.append(f"| Preprocessing Version | `{meta.get('preprocessing_version', 'N/A')}` |")
    lines.append(f"| Artifact Hash | `{meta.get('artifact_hash', 'N/A')}` |")
    lines.append(f"| Training Duration | `{meta.get('training_duration_seconds', 0):.2f}s` |")
    lines.append(f"| Python | `{meta.get('environment', {}).get('python_version', 'N/A')}` |")
    lines.append(f"| Platform | `{meta.get('environment', {}).get('platform', 'N/A')}` |\n")

    # Dataset
    lines.append("## Dataset\n")
    lines.append(f"| Property | Value |")
    lines.append(f"| :--- | :--- |")
    lines.append(f"| Identifier | {dataset_info.get('identifier', 'N/A')} |")
    lines.append(f"| Version | {dataset_info.get('version', 'N/A')} |")
    lines.append(f"| Train Samples | {split_info.get('train', 'N/A')} |")
    lines.append(f"| Validation Samples | {split_info.get('val', 'N/A')} |")
    lines.append(f"| Test Samples | {split_info.get('test', 'N/A')} |\n")

    # Hyperparameters
    lines.append("## Hyperparameters\n")
    lines.append("```json")
    lines.append(json.dumps(hp, indent=2, default=str))
    lines.append("```\n")

    # Validation Metrics
    if val_metrics:
        lines.append("## Validation Metrics\n")
        lines.append(f"| Metric | Value |")
        lines.append(f"| :--- | :--- |")
        for k, v in _flatten_metrics(val_metrics).items():
            lines.append(f"| {k} | {_fmt_metric(v)} |")
        lines.append("")

    # Test Metrics
    if test_metrics:
        lines.append("## Test Metrics\n")
        lines.append(f"| Metric | Value |")
        lines.append(f"| :--- | :--- |")
        for k, v in _flatten_metrics(test_metrics).items():
            lines.append(f"| {k} | {_fmt_metric(v)} |")
        lines.append("")

    # Per-class breakdown
    if per_class_metrics and class_names:
        lines.append("## Per-Class Breakdown\n")
        header_keys = list(next(iter(per_class_metrics.values())).keys()) if per_class_metrics else []
        header_line = "| Class | " + " | ".join(k.capitalize() for k in header_keys) + " |"
        sep_line = "| :--- | " + " | ".join(":---" for _ in header_keys) + " |"
        lines.append(header_line)
        lines.append(sep_line)
        for cls in class_names:
            cls_m = per_class_metrics.get(cls, {})
            vals = " | ".join(_fmt_metric(cls_m.get(k, 0.0)) for k in header_keys)
            lines.append(f"| `{cls}` | {vals} |")
        lines.append("")

    # Confusion matrix
    if confusion_matrix and class_names:
        lines.append("## Confusion Matrix\n")
        header = "| | " + " | ".join(f"`{c}`" for c in class_names) + " |"
        sep = "| :--- | " + " | ".join(":---:" for _ in class_names) + " |"
        lines.append(header)
        lines.append(sep)
        for i, row in enumerate(confusion_matrix):
            vals = " | ".join(str(v) for v in row)
            lines.append(f"| **`{class_names[i]}`** | {vals} |")
        lines.append("")

    # Additional sections
    if additional_sections:
        lines.append(additional_sections)

    # Write
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("Training report written to %s", output_path)


def _flatten_metrics(metrics: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """Flatten nested metric dicts for tabular rendering."""
    flat: Dict[str, Any] = {}
    for k, v in metrics.items():
        key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        if isinstance(v, dict):
            flat.update(_flatten_metrics(v, key))
        elif isinstance(v, (list, np.ndarray)):
            continue  # skip arrays in summary table
        else:
            flat[key] = v
    return flat


def _fmt_metric(v: Any) -> str:
    """Format a metric value for display."""
    if isinstance(v, float):
        if abs(v) < 1.0:
            return f"{v:.4f}"
        return f"{v:.2f}"
    return str(v)

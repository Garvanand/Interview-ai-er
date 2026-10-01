"""
CodeXGLUE Defect Detection Dataset Loader.
Source: Microsoft CodeXGLUE / Devign Benchmark
https://github.com/microsoft/CodeXGLUE/tree/main/Code-Code/Defect-detection

Dataset identifier: code_x_glue_cc_defect_detection (HuggingFace Hub)
License: Computational Use of Data Agreement (C-UDA) — non-commercial research.

Used for:
- Code Defect & Vulnerability Risk Detection (CodeBERT Fine-Tuning)

Fields used:
- func: source code function (C/C++/mixed)
- target: 0 = non-defective, 1 = defective/vulnerable
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Generator, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DefectSample:
    """A single code defect detection sample."""
    sample_id: str
    code_text: str
    is_vulnerable: bool  # 1 = defective/vulnerable, 0 = benign
    language: str = "c_cpp"


class CodeXGLUEDefectLoader:
    """
    Streams and normalizes CodeXGLUE Defect Detection samples from HuggingFace Hub.

    The dataset contains ~27K C/C++ functions labeled as defective (1) or clean (0),
    sourced from the Devign benchmark (Zhou et al., 2019).
    """

    DATASET_ID = "google/code_x_glue_cc_defect_detection"
    VALID_SPLITS = ("train", "validation", "test")

    def __init__(self, split: str = "train"):
        if split not in self.VALID_SPLITS:
            raise ValueError(f"Invalid split '{split}'. Must be one of {self.VALID_SPLITS}")
        self.split = split
        self._dataset = None

    def _load_raw_dataset(self):
        """Load the raw HuggingFace dataset (cached after first download)."""
        if self._dataset is not None:
            return
        from datasets import load_dataset
        logger.info(
            "Loading CodeXGLUE defect detection dataset (split=%s) from HuggingFace Hub...",
            self.split,
        )
        self._dataset = load_dataset(self.DATASET_ID, split=self.split)
        logger.info(
            "Loaded %d samples from split '%s'", len(self._dataset), self.split
        )

    def load_samples(
        self, limit: Optional[int] = None
    ) -> Generator[DefectSample, None, None]:
        """Yield normalized defect detection samples."""
        try:
            self._load_raw_dataset()
        except ImportError:
            logger.warning(
                "HuggingFace `datasets` not installed. "
                "CodeXGLUEDefectLoader requires `pip install datasets`."
            )
            return
        except Exception as e:
            logger.error("Failed to load CodeXGLUE defect dataset: %s", e)
            return

        count = 0
        for item in self._dataset:
            if limit is not None and count >= limit:
                break

            code = item.get("func", "")
            target = item.get("target", 0)

            # Skip empty/very short samples
            if len(code.strip()) < 10:
                continue

            yield DefectSample(
                sample_id=str(item.get("id", count)),
                code_text=code,
                is_vulnerable=bool(target),
                language="c_cpp",
            )
            count += 1

    def get_class_distribution(self, limit: Optional[int] = None) -> Dict[str, int]:
        """Return the label distribution for the loaded split."""
        counts = {"defective": 0, "clean": 0}
        for sample in self.load_samples(limit=limit):
            if sample.is_vulnerable:
                counts["defective"] += 1
            else:
                counts["clean"] += 1
        return counts

    def load_as_texts_and_labels(
        self, limit: Optional[int] = None
    ) -> Tuple[List[str], List[int]]:
        """
        Load dataset as parallel lists of (code_text, label).
        Useful for batch tokenization and training.
        """
        texts = []
        labels = []
        for sample in self.load_samples(limit=limit):
            texts.append(sample.code_text)
            labels.append(1 if sample.is_vulnerable else 0)
        return texts, labels

"""
APPS (Automated Programming Progress Standard) Dataset Loader.
Source: codeparrot/apps (Hugging Face)
https://huggingface.co/datasets/codeparrot/apps

Used for:
- Question Difficulty Prediction
- Canonical Code Verification Reference Solutions
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Generator, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

APPS_DIFFICULTY_MAP = {
    "introductory": "beginner",
    "interview": "intermediate",
    "competition": "advanced",
}

@dataclass
class APPSSample:
    problem_id: int
    question_text: str
    difficulty_raw: str
    difficulty_normalized: str
    solutions_count: int
    solutions: List[str]


class APPSDatasetLoader:
    """Streams and parses codeparrot/apps dataset samples."""

    def __init__(self, split: str = "train", streaming: bool = True):
        self.split = split
        self.streaming = streaming

    def load_samples(self, limit: Optional[int] = None) -> Generator[APPSSample, None, None]:
        """Yield normalized APPS samples."""
        try:
            from datasets import load_dataset
            logger.info("Loading codeparrot/apps dataset (split=%s, streaming=%s)", self.split, self.streaming)
            dataset = load_dataset("codeparrot/apps", split=self.split, streaming=self.streaming)

            count = 0
            for item in dataset:
                if limit and count >= limit:
                    break

                raw_diff = str(item.get("difficulty", "interview")).lower()
                norm_diff = APPS_DIFFICULTY_MAP.get(raw_diff, "intermediate")

                solutions_raw = item.get("solutions") or "[]"
                solutions = []
                if isinstance(solutions_raw, str):
                    try:
                        solutions = json.loads(solutions_raw)
                    except Exception:
                        solutions = []
                elif isinstance(solutions_raw, list):
                    solutions = solutions_raw

                yield APPSSample(
                    problem_id=item.get("problem_id", count),
                    question_text=item.get("question", ""),
                    difficulty_raw=raw_diff,
                    difficulty_normalized=norm_diff,
                    solutions_count=len(solutions),
                    solutions=solutions[:3],
                )
                count += 1
        except ImportError:
            logger.warning("HuggingFace `datasets` not installed. APPSDatasetLoader requires `pip install datasets`.")
            return
        except Exception as e:
            logger.error("Failed to stream APPS dataset: %s", e)
            return

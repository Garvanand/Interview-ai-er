"""
EdNet (Educational Data Network) Interaction Dataset Loader.
Source: mgor/EDNet (Hugging Face)
https://huggingface.co/datasets/mgor/EDNet

Used for:
- Candidate Skill / Mastery Modeling (IRT & Knowledge Tracing)
"""
from __future__ import annotations

import logging
from typing import Generator, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class LearnerInteraction:
    user_id: str
    question_id: str
    is_correct: bool
    elapsed_time_ms: int
    timestamp: Optional[str] = None


class EdNetDatasetLoader:
    """Streams and parses EdNet interaction logs for IRT/BKT parameter estimation."""

    def __init__(self, split: str = "train", streaming: bool = True):
        self.split = split
        self.streaming = streaming

    def load_samples(self, limit: Optional[int] = None) -> Generator[LearnerInteraction, None, None]:
        """Yield normalized learner interaction records."""
        try:
            from datasets import load_dataset
            logger.info("Loading EdNet dataset (split=%s, streaming=%s)", self.split, self.streaming)
            dataset = load_dataset("mgor/EDNet", split=self.split, streaming=self.streaming)

            count = 0
            for item in dataset:
                if limit and count >= limit:
                    break

                yield LearnerInteraction(
                    user_id=str(item.get("user_id", "")),
                    question_id=str(item.get("question_id", "")),
                    is_correct=bool(item.get("user_answer") == item.get("correct_answer", 1)),
                    elapsed_time_ms=int(item.get("elapsed_time", 0)),
                    timestamp=str(item.get("timestamp", "")),
                )
                count += 1
        except ImportError:
            logger.warning("HuggingFace `datasets` not installed. EdNetDatasetLoader requires `pip install datasets`.")
            return
        except Exception as e:
            logger.error("Failed to stream EdNet dataset: %s", e)
            return

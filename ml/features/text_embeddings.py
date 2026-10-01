"""
Text embeddings and vector representations using all-MiniLM-L6-v2.
Model: sentence-transformers/all-MiniLM-L6-v2 (PRETRAINED)
https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

Used for:
- Semantic Answer Similarity
- Feature vectors for Question Difficulty & Skill Classification
"""
from __future__ import annotations

import logging
import math
from typing import List, Optional, Union
import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def compute_cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Compute cosine similarity between two 1D or 2D vectors."""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


import hashlib
import os

class TextEmbeddingExtractor:
    """Extracts dense sentence embeddings using sentence-transformers or deterministic fallback."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        device: str = "cpu",
        enable_transformer: Optional[bool] = None,
    ):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._fallback_mode = False
        if enable_transformer is not None:
            self.enable_transformer = enable_transformer
        else:
            self.enable_transformer = os.environ.get("USE_TRANSFORMER_EMBEDDINGS", "1").lower() in ("1", "true")

    def _load_model(self):
        if self._model is not None or self._fallback_mode:
            return
        if not self.enable_transformer:
            self._fallback_mode = True
            return

        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading SentenceTransformer model: %s on %s", self.model_name, self.device)
            self._model = SentenceTransformer(self.model_name, device=self.device)
        except Exception as e:
            logger.warning(
                "Failed to load SentenceTransformer (%s). Falling back to deterministic pseudo-embedding. Error: %s",
                self.model_name,
                e
            )
            self._fallback_mode = True

    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """Encode text or list of texts into embedding vectors (384 dimensions for all-MiniLM-L6-v2)."""
        is_single = isinstance(texts, str)
        text_list = [texts] if is_single else list(texts)

        self._load_model()

        if self._model is not None and not self._fallback_mode:
            embeddings = self._model.encode(text_list, normalize_embeddings=normalize, show_progress_bar=False)
            return embeddings[0] if is_single else np.array(embeddings)

        # DETERMINISTIC FALLBACK: Normalized character/word MD5 hash vector (384 dimensions)
        dim = 384
        vectors = []
        for t in text_list:
            v = np.zeros(dim, dtype=np.float32)
            words = t.lower().split()
            for w in words:
                # Use md5 for stable hash across processes
                idx = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16) % dim
                v[idx] += 1.0
            norm = np.linalg.norm(v)
            if norm > 0 and normalize:
                v = v / norm
            vectors.append(v)

        return vectors[0] if is_single else np.array(vectors)

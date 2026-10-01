"""
Feature extraction, vector embedding, and representation transformations.
"""
from __future__ import annotations

from .text_embeddings import TextEmbeddingExtractor, compute_cosine_similarity
from .code_features import extract_code_lexical_features

__all__ = [
    "TextEmbeddingExtractor",
    "compute_cosine_similarity",
    "extract_code_lexical_features",
]

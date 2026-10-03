"""
Semantic question retrieval package.
"""
from ml.models.semantic_retriever import (
    SemanticQuestionRetriever,
    ScoredQuestionMatch,
    DuplicateDetectionResult,
    EXACT_DUPLICATE_THRESHOLD,
    NEAR_DUPLICATE_THRESHOLD,
    RELATED_QUESTION_THRESHOLD,
    UNRELATED_THRESHOLD,
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_VERSION,
    EMBEDDING_DIM,
)

__all__ = [
    "SemanticQuestionRetriever",
    "ScoredQuestionMatch",
    "DuplicateDetectionResult",
    "EXACT_DUPLICATE_THRESHOLD",
    "NEAR_DUPLICATE_THRESHOLD",
    "RELATED_QUESTION_THRESHOLD",
    "UNRELATED_THRESHOLD",
    "DEFAULT_EMBEDDING_MODEL",
    "EMBEDDING_VERSION",
    "EMBEDDING_DIM",
]

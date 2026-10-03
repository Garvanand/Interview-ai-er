"""
CLI script to generate MiniLM embeddings for the entire canonical question corpus.
Stores embeddings in PostgreSQL / Supabase and local cache.
Run with:
  python -m ml.retrieval.index_corpus
"""
from __future__ import annotations

import logging
import sys
from ml.models.semantic_retriever import (
    SemanticQuestionRetriever,
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_VERSION,
    EMBEDDING_DIM
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    logger.info("Initializing Semantic Question Retriever with %s (v%s)...", DEFAULT_EMBEDDING_MODEL, EMBEDDING_VERSION)
    retriever = SemanticQuestionRetriever(auto_index_catalog=False)
    
    logger.info("Generating embeddings for all catalog questions...")
    total_indexed = retriever.index_canonical_corpus(persist=True)
    
    logger.info("Successfully generated embeddings for %d questions (dimension: %d).", total_indexed, EMBEDDING_DIM)
    
    # Quick sanity check
    sample_query = "Two sum hash map index lookup"
    logger.info("Running test similarity search for query: '%s'...", sample_query)
    results = retriever.similarity_search(sample_query, top_k=3)
    for i, res in enumerate(results, 1):
        logger.info("  [%d] %s (sim=%.4f, class=%s) - %s", i, res.question_id, res.similarity, res.classification, res.title)

    logger.info("Corpus indexing completed successfully.")


if __name__ == "__main__":
    main()

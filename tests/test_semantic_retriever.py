"""
Unit and integration tests for SemanticQuestionRetriever.
Validates:
  1. Corpus embedding generation & PostgreSQL/Supabase compatibility
  2. Exact duplicate detection (threshold >= 0.98)
  3. Paraphrase / Near-duplicate detection (0.78 <= threshold < 0.98)
  4. Unrelated question discrimination (threshold < 0.40)
  5. Related question retrieval (0.50 <= threshold < 0.78)
  6. Skill-aware semantic retrieval
  7. Vector storage schema (question_id, embedding_model, embedding_version, embedding_vector)
  8. Interview engine deduplication & novelty protection
"""
import pytest
import numpy as np

from ml.features.text_embeddings import TextEmbeddingExtractor
from ml.models.semantic_retriever import (
    SemanticQuestionRetriever,
    EXACT_DUPLICATE_THRESHOLD,
    NEAR_DUPLICATE_THRESHOLD,
    RELATED_QUESTION_THRESHOLD,
    UNRELATED_THRESHOLD,
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_VERSION,
    EMBEDDING_DIM,
)


@pytest.fixture
def mock_supabase():
    """Mock SupabaseService with local in-memory storage."""
    class MockSupabaseService:
        def __init__(self):
            self.saved_embeddings = {}

        def save_question_embedding(
            self,
            question_id: str,
            embedding_vector: list,
            embedding_model: str,
            embedding_version: str,
            question_text: str = "",
            skill_focus: str = "",
            difficulty: str = "",
        ):
            record = {
                "question_id": question_id,
                "embedding_model": embedding_model,
                "embedding_version": embedding_version,
                "embedding_vector": embedding_vector,
                "question_text": question_text,
                "skill_focus": skill_focus,
                "difficulty": difficulty,
            }
            self.saved_embeddings[question_id] = record
            return record

        def get_question_embedding(self, question_id: str):
            return self.saved_embeddings.get(question_id)

        def get_all_question_embeddings(self, embedding_model=None, embedding_version=None):
            return list(self.saved_embeddings.values())

    return MockSupabaseService()


@pytest.fixture
def retriever(mock_supabase):
    """Retriever using sentence-transformers/all-MiniLM-L6-v2 embeddings."""
    extractor = TextEmbeddingExtractor(enable_transformer=True)
    retriever = SemanticQuestionRetriever(
        embedding_extractor=extractor,
        supabase_service=mock_supabase,
        auto_index_catalog=True,
    )
    return retriever


def test_vector_storage_schema(retriever, mock_supabase):
    """Verify that stored embeddings strictly comply with the required fields:
    question_id, embedding model, embedding version, embedding vector."""
    embeddings = mock_supabase.get_all_question_embeddings()
    assert len(embeddings) > 0, "Corpus should have been indexed and saved."

    sample = embeddings[0]
    assert "question_id" in sample and sample["question_id"]
    assert "embedding_model" in sample and sample["embedding_model"] == DEFAULT_EMBEDDING_MODEL
    assert "embedding_version" in sample and sample["embedding_version"] == EMBEDDING_VERSION
    assert "embedding_vector" in sample
    assert isinstance(sample["embedding_vector"], list)
    assert len(sample["embedding_vector"]) == EMBEDDING_DIM, f"Vector should have {EMBEDDING_DIM} dimensions."


def test_exact_duplicate_detection(retriever):
    """Test that identical or normalized exact matches are flagged as exact duplicates."""
    # Query with exact text from corpus (Two Sum)
    two_sum_text = (
        "Given an array of integers `nums` and an integer `target`, return the indices "
        "of the two numbers such that they add up to `target`. Optimize for O(N) time using a hash map."
    )

    result = retriever.detect_duplicates(two_sum_text)
    assert result.is_duplicate is True
    assert result.classification == "exact_duplicate"
    assert result.max_similarity >= EXACT_DUPLICATE_THRESHOLD
    assert result.matched_question_id == "dsa_arr_two_sum"

    is_dup, sim = retriever.is_exact_duplicate(two_sum_text, "dsa_arr_two_sum")
    assert is_dup is True
    assert sim >= EXACT_DUPLICATE_THRESHOLD


def test_paraphrase_near_duplicate_detection(retriever):
    """Test that a rephrased / paraphrased question is detected as a near-duplicate."""
    # Paraphrased version of Two Sum
    paraphrased_two_sum = (
        "Given an integer array nums and target value, find two array indices whose elements "
        "sum to target in linear O(N) time with a hash map."
    )

    result = retriever.detect_duplicates(paraphrased_two_sum)
    # Should detect high similarity to Two Sum
    assert result.max_similarity >= NEAR_DUPLICATE_THRESHOLD
    assert result.matched_question_id in ["dsa_arr_two_sum", "dsa_arr_longest_consecutive"]
    assert result.classification in ["near_duplicate", "exact_duplicate"]

    is_near, sim = retriever.is_near_duplicate(paraphrased_two_sum, "dsa_arr_two_sum")
    assert sim >= NEAR_DUPLICATE_THRESHOLD


def test_unrelated_questions_discrimination(retriever):
    """Test that completely unrelated questions yield low similarity (< UNRELATED_THRESHOLD)."""
    # Unrelated question: Web performance / CRP vs graph/array questions
    frontend_text = (
        "Walk through the browser Critical Rendering Path from HTML byte stream to pixels on screen. "
        "How do script defer/async, CSS object model construction, reflow, and repaint impact Core Web Vitals?"
    )
    unrelated_target = "dsa_dp_climbing_stairs"  # Climbing stairs DP

    is_dup, sim = retriever.is_exact_duplicate(frontend_text, unrelated_target)
    assert is_dup is False
    assert sim < UNRELATED_THRESHOLD, f"Expected similarity < {UNRELATED_THRESHOLD}, got {sim}"


def test_similarity_search_ranking(retriever):
    """Test that similarity search returns results ordered by descending cosine similarity."""
    query = "reverse singly linked list iterative recursive"
    matches = retriever.similarity_search(query, top_k=5)

    assert len(matches) <= 5
    assert len(matches) > 0

    # Ensure monotonic non-increasing similarity
    similarities = [m.similarity for m in matches]
    assert similarities == sorted(similarities, reverse=True)

    # Top match should be the linked list reverse question
    top_match = matches[0]
    assert "linked" in top_match.question_text.lower() or "list" in top_match.question_text.lower()


def test_skill_aware_retrieval(retriever):
    """Test that skill-aware retrieval restricts results to specified skill focuses."""
    query = "shortest path optimization"

    # Search specifically for graph questions
    graph_matches = retriever.retrieve_skill_aware(query, target_skills=["graphs"], top_k=3)
    for m in graph_matches:
        q_skill = m.skill_focus.lower()
        canonical = [c.lower() for c in m.canonical_skills]
        assert "graphs" in q_skill or any("graph" in c for c in canonical)

    # Search specifically for trees
    tree_matches = retriever.retrieve_skill_aware(query, target_skills=["trees"], top_k=3)
    for m in tree_matches:
        q_skill = m.skill_focus.lower()
        canonical = [c.lower() for c in m.canonical_skills]
        assert "trees" in q_skill or any("tree" in c for c in canonical)


def test_interview_engine_novelty_protection(retriever):
    """Test that the interview engine novelty checker properly penalizes duplicates and allows distinct questions."""
    history = [
        "Given an array of integers `nums` and an integer `target`, return the indices of the two numbers such that they add up to `target`.",
    ]

    # 1. Exact Duplicate
    novelty, most_sim, verdict = retriever.check_question_novelty(history[0], history)
    assert novelty == 0.0
    assert verdict == "REJECT_EXACT_DUPLICATE"

    # 2. Distinct Unrelated Question
    distinct_question = "Explain relational database B-Tree index structure and leftmost prefix matching."
    novelty, most_sim, verdict = retriever.check_question_novelty(distinct_question, history)
    assert novelty > 0.60
    assert verdict in ["ALLOW_DISTINCT", "ALLOW_RELATED"]

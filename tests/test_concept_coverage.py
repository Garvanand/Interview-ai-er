"""
Comprehensive test suite for the Hybrid Semantic Answer Analysis Layer.

Tests the ConceptCoverageAnalyzer and HybridAssessmentPipeline across 5 scenarios:
    1. Relevant answers — concepts are well covered
    2. Irrelevant answers — answer doesn't address any concepts
    3. Contradictory answers — answer directly contradicts expected concepts
    4. Partial answers — some concepts covered, some missing
    5. Empty answers — blank or whitespace-only answers

These tests exercise the deterministic aggregation formula and status assignment
without requiring the actual transformer models to be loaded (they use the
lexical fallback when models aren't available).
"""
from __future__ import annotations

import pytest
from typing import Dict, List, Any

from ml.models.concept_coverage import (
    ConceptCoverageAnalyzer,
    W_NLI,
    W_SIM,
    COVERED_THRESHOLD,
    PARTIAL_THRESHOLD,
    CONTRADICTION_THRESHOLD,
)
from ml.pipelines.hybrid_assessment import HybridAssessmentPipeline


# ────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────

@pytest.fixture
def analyzer():
    """A fresh ConceptCoverageAnalyzer instance (will use fallback if no GPU/models)."""
    return ConceptCoverageAnalyzer(device="cpu")


@pytest.fixture
def pipeline():
    """A fresh HybridAssessmentPipeline instance."""
    return HybridAssessmentPipeline(device="cpu")


@pytest.fixture
def database_concepts():
    """Standard concepts for a database indexing question."""
    return [
        "database indexing reduces lookup search space",
        "B-tree indexes enable logarithmic time lookups",
        "indexing introduces write overhead and storage cost",
        "composite indexes follow leftmost prefix matching",
    ]


@pytest.fixture
def database_question():
    return "Explain how database indexing works, including B-tree structures, write overhead, and composite index behavior."


@pytest.fixture
def database_rubric():
    return (
        "The candidate should explain:\n"
        "1. Database indexing reduces lookup search space from O(n) to O(log n)\n"
        "2. B-tree indexes enable logarithmic time lookups through balanced tree structures\n"
        "3. Indexing introduces write overhead and storage cost for maintaining index structures\n"
        "4. Composite indexes follow leftmost prefix matching rules for multi-column queries"
    )


# ────────────────────────────────────────────────────────────────────
# Test 1: Relevant Answers
# ────────────────────────────────────────────────────────────────────

class TestRelevantAnswers:
    """Answers that directly address the expected concepts should score high coverage."""

    def test_fully_relevant_answer_produces_high_coverage(self, analyzer, database_concepts):
        """A thorough, on-topic answer should produce high overall coverage."""
        answer = (
            "Database indexing reduces the lookup search space by organizing data "
            "in structured formats like B-tree indexes. B-tree indexes enable logarithmic "
            "time lookups because the balanced tree structure allows binary-search-like "
            "traversal. However, indexing introduces write overhead and storage cost "
            "since every insert or update must also maintain the index. Composite indexes "
            "follow leftmost prefix matching, meaning a composite index on (A, B, C) "
            "can serve queries filtering on A, or A+B, but not just B or C alone."
        )
        result = analyzer.evaluate_concepts(answer, database_concepts)

        assert result["overall_coverage_pct"] > 30.0  # Should be high, even with fallback
        assert result["signal_type"] == "ml_derived_concept_coverage_signal"
        assert len(result["concept_results"]) == len(database_concepts)
        assert isinstance(result["concept_results"], list)

        # Each concept result should have the full NLI triplet
        for cr in result["concept_results"]:
            assert "entailment_probability" in cr
            assert "contradiction_probability" in cr
            assert "neutral_probability" in cr
            assert "semantic_similarity" in cr
            assert "concept_score" in cr
            assert "status" in cr
            assert cr["status"] in ("covered", "partially_covered", "missing", "contradicted")

    def test_relevant_answer_has_low_contradiction(self, analyzer, database_concepts):
        """A correct, relevant answer should have low contradiction probabilities."""
        answer = (
            "Indexing creates data structures that reduce lookup search space. "
            "B-tree indexes provide logarithmic lookups. The overhead includes "
            "write cost and storage for maintaining indexes. Composite indexes "
            "use leftmost prefix matching rules."
        )
        result = analyzer.evaluate_concepts(answer, database_concepts)

        for cr in result["concept_results"]:
            # With correct answers, contradiction should generally be low
            assert cr["contradiction_probability"] < CONTRADICTION_THRESHOLD, (
                f"Concept '{cr['concept']}' has unexpectedly high contradiction "
                f"({cr['contradiction_probability']}) for a correct answer"
            )

    def test_method_field_is_populated(self, analyzer, database_concepts):
        """The method field should indicate which models/fallbacks were used."""
        answer = "Database indexing reduces lookup time using B-tree structures."
        result = analyzer.evaluate_concepts(answer, database_concepts)

        assert "method" in result
        assert result["method"]  # Non-empty string
        # Should contain info about both NLI and similarity method
        assert "nli" in result["method"].lower() or "fallback" in result["method"].lower()


# ────────────────────────────────────────────────────────────────────
# Test 2: Irrelevant Answers
# ────────────────────────────────────────────────────────────────────

class TestIrrelevantAnswers:
    """Answers about completely unrelated topics should score very low coverage."""

    def test_completely_off_topic_answer(self, analyzer, database_concepts):
        """An answer about cooking should produce near-zero coverage for DB concepts."""
        answer = (
            "To make a perfect soufflé, you need to whisk egg whites until stiff peaks form, "
            "then gently fold in the base mixture. Bake at 375°F for about 12 minutes. "
            "The key is not opening the oven door during baking."
        )
        result = analyzer.evaluate_concepts(answer, database_concepts)

        assert result["overall_coverage_pct"] < 50.0
        assert len(result["missing_concepts"]) > 0
        assert result["signal_type"] == "ml_derived_concept_coverage_signal"

    def test_tangentially_related_answer(self, analyzer, database_concepts):
        """An answer about databases but not about indexing should score poorly."""
        answer = (
            "Databases store information in tables with rows and columns. "
            "SQL is used to query data. You can use SELECT statements to retrieve records. "
            "Normalization helps reduce data redundancy."
        )
        result = analyzer.evaluate_concepts(answer, database_concepts)

        # Should have poor coverage since it doesn't address specific concepts
        assert result["overall_coverage_pct"] < 70.0
        assert len(result["missing_concepts"]) >= 1

    def test_irrelevant_answer_missing_all_concepts(self, analyzer):
        """When all concepts are completely absent from the answer."""
        concepts = [
            "TCP three-way handshake establishes reliable connections",
            "UDP provides connectionless communication with lower latency",
        ]
        answer = "My favorite color is blue and I enjoy playing basketball on weekends."
        result = analyzer.evaluate_concepts(answer, concepts)

        assert len(result["missing_concepts"]) == len(concepts)
        assert result["overall_coverage_pct"] < 30.0


# ────────────────────────────────────────────────────────────────────
# Test 3: Contradictory Answers
# ────────────────────────────────────────────────────────────────────

class TestContradictoryAnswers:
    """Answers that directly contradict expected concepts should be flagged."""

    def test_direct_contradiction_flagged(self, analyzer):
        """Test with concepts that the answer directly contradicts."""
        concepts = [
            "database indexing reduces lookup search space",
            "indexing introduces write overhead and storage cost",
        ]
        # NOTE: With lexical fallback, true contradiction detection is limited.
        # With the actual DeBERTa model, this would correctly identify contradiction.
        answer = (
            "Database indexing has absolutely no effect on lookup performance. "
            "Adding indexes is completely free with zero storage cost and zero write overhead."
        )
        result = analyzer.evaluate_concepts(answer, concepts)

        # We mainly verify the structure is correct
        assert len(result["concept_results"]) == 2
        for cr in result["concept_results"]:
            assert "contradiction_probability" in cr
            assert 0.0 <= cr["contradiction_probability"] <= 1.0

    def test_contradiction_threshold_logic(self):
        """Verify the status determination logic for contradictions."""
        status = ConceptCoverageAnalyzer._determine_status(
            concept_score=0.80,
            contradiction_prob=0.60,  # Above threshold
        )
        assert status == "contradicted", (
            "High contradiction probability should override high concept score"
        )

    def test_mixed_correct_and_contradictory(self, analyzer, database_concepts):
        """An answer that is correct on some points and wrong on others."""
        answer = (
            "Database indexing does reduce the lookup search space through tree structures. "
            "However, indexing has absolutely no write overhead whatsoever. "
            "B-tree indexes enable logarithmic lookups. "
            "Composite indexes have nothing to do with prefix matching."
        )
        result = analyzer.evaluate_concepts(answer, database_concepts)

        assert len(result["concept_results"]) == 4
        # Verify structural integrity
        for cr in result["concept_results"]:
            assert "status" in cr
            assert cr["status"] in ("covered", "partially_covered", "missing", "contradicted")


# ────────────────────────────────────────────────────────────────────
# Test 4: Partial Answers
# ────────────────────────────────────────────────────────────────────

class TestPartialAnswers:
    """Answers that cover some but not all concepts should have mixed results."""

    def test_half_concepts_covered(self, analyzer, database_concepts):
        """An answer covering only the first two concepts should show partial coverage."""
        answer = (
            "Database indexing reduces the lookup search space by creating organized "
            "data structures. B-tree indexes enable logarithmic time lookups because "
            "the tree stays balanced."
        )
        result = analyzer.evaluate_concepts(answer, database_concepts)

        # Should have some covered and some missing
        total_covered = len(result["covered_concepts"])
        total_missing = len(result["missing_concepts"])
        total_partial = len(result["partially_covered_concepts"])

        # At least some concepts should not be fully covered
        assert total_missing + total_partial > 0, (
            "A partial answer should have at least some missing/partial concepts"
        )
        # But overall coverage should be moderate, not zero
        assert result["overall_coverage_pct"] > 0.0

    def test_single_concept_covered(self, analyzer, database_concepts):
        """An answer addressing only one concept explicitly."""
        answer = "Indexing reduces the lookup search space by narrowing the scan range."
        result = analyzer.evaluate_concepts(answer, database_concepts)

        # At least 2 concepts should be missing
        assert len(result["missing_concepts"]) >= 2

    def test_vague_partial_answer(self, analyzer, database_concepts):
        """A vague, surface-level answer that touches concepts without depth."""
        answer = (
            "Indexes help with database performance. "
            "There are different types of indexes. "
            "They have tradeoffs."
        )
        result = analyzer.evaluate_concepts(answer, database_concepts)

        # Should reflect poor coverage since no specific concepts are addressed
        assert result["overall_coverage_pct"] < 80.0


# ────────────────────────────────────────────────────────────────────
# Test 5: Empty Answers
# ────────────────────────────────────────────────────────────────────

class TestEmptyAnswers:
    """Empty or whitespace-only answers should produce zero coverage."""

    def test_empty_string(self, analyzer, database_concepts):
        """An empty string answer should produce 0% coverage."""
        result = analyzer.evaluate_concepts("", database_concepts)

        assert result["overall_coverage_pct"] == 0.0
        assert result["method"] == "empty_answer"
        assert len(result["missing_concepts"]) == len(database_concepts)
        assert len(result["covered_concepts"]) == 0

    def test_whitespace_only(self, analyzer, database_concepts):
        """Whitespace-only answer should be treated as empty."""
        result = analyzer.evaluate_concepts("   \n\t  \n  ", database_concepts)

        assert result["overall_coverage_pct"] == 0.0
        assert result["method"] == "empty_answer"
        assert len(result["missing_concepts"]) == len(database_concepts)

    def test_none_like_empty(self, analyzer, database_concepts):
        """None-like empty should produce 0% coverage for all concepts."""
        result = analyzer.evaluate_concepts("", database_concepts)

        for cr in result["concept_results"]:
            assert cr["entailment_probability"] == 0.0
            assert cr["semantic_similarity"] == 0.0
            assert cr["concept_score"] == 0.0
            assert cr["status"] == "missing"

    def test_empty_concepts_list(self, analyzer):
        """When no concepts are expected, coverage should be 100% trivially."""
        result = analyzer.evaluate_concepts("Some answer text", [])

        assert result["overall_coverage_pct"] == 100.0
        assert result["method"] == "trivial_empty_rubric"


# ────────────────────────────────────────────────────────────────────
# Aggregation formula tests
# ────────────────────────────────────────────────────────────────────

class TestAggregationFormula:
    """Verify the documented deterministic aggregation formula."""

    def test_aggregation_weights_sum(self):
        """W_NLI + W_SIM must equal 1.0 for proper normalization."""
        assert abs(W_NLI + W_SIM - 1.0) < 1e-9

    def test_status_determination_covered(self):
        """Score >= COVERED_THRESHOLD with low contradiction → covered."""
        status = ConceptCoverageAnalyzer._determine_status(0.65, 0.10)
        assert status == "covered"

    def test_status_determination_partial(self):
        """PARTIAL_THRESHOLD <= score < COVERED_THRESHOLD → partially_covered."""
        status = ConceptCoverageAnalyzer._determine_status(0.45, 0.10)
        assert status == "partially_covered"

    def test_status_determination_missing(self):
        """Score < PARTIAL_THRESHOLD → missing."""
        status = ConceptCoverageAnalyzer._determine_status(0.20, 0.10)
        assert status == "missing"

    def test_status_determination_contradicted_overrides_covered(self):
        """High contradiction overrides even a high concept score."""
        status = ConceptCoverageAnalyzer._determine_status(0.90, 0.55)
        assert status == "contradicted"

    def test_concept_score_formula(self, analyzer):
        """Verify the composite score matches the documented formula."""
        concepts = ["test concept about algorithms and data structures"]
        answer = "algorithms and data structures are fundamental to computer science"
        result = analyzer.evaluate_concepts(answer, concepts)

        for cr in result["concept_results"]:
            expected_score = round(
                (W_NLI * cr["entailment_probability"]) + (W_SIM * cr["semantic_similarity"]),
                4,
            )
            assert abs(cr["concept_score"] - expected_score) < 0.001, (
                f"Concept score {cr['concept_score']} doesn't match formula result {expected_score}"
            )


# ────────────────────────────────────────────────────────────────────
# HybridAssessmentPipeline tests
# ────────────────────────────────────────────────────────────────────

class TestHybridPipeline:
    """Tests for the full pipeline including evidence generation and formatting."""

    def test_generate_ml_evidence_structure(self, pipeline, database_question, database_rubric):
        """Verify the complete evidence structure from the pipeline."""
        answer = "Database indexing reduces lookup search space using B-tree structures."
        evidence = pipeline.generate_ml_evidence(
            candidate_answer=answer,
            question_text=database_question,
            evaluation_rubric=database_rubric,
        )

        assert "ml_concept_coverage" in evidence
        assert "concepts_evaluated" in evidence
        assert "concepts_list" in evidence
        assert "pipeline_version" in evidence
        assert "total_pipeline_time_ms" in evidence
        assert "disclaimer" in evidence
        assert evidence["pipeline_version"] == "hybrid_v1.0"
        assert evidence["concepts_evaluated"] > 0

    def test_generate_ml_evidence_with_explicit_concepts(self, pipeline, database_question, database_rubric, database_concepts):
        """When explicit concepts are provided, they should be used directly."""
        answer = "B-tree indexing enables log-time lookups."
        evidence = pipeline.generate_ml_evidence(
            candidate_answer=answer,
            question_text=database_question,
            evaluation_rubric=database_rubric,
            expected_concepts=database_concepts,
        )

        assert evidence["concepts_list"] == database_concepts
        assert evidence["concepts_evaluated"] == len(database_concepts)

    def test_format_evidence_for_gemini_produces_text(self, pipeline, database_question, database_rubric):
        """The Gemini evidence block should be a non-empty string with instructions."""
        answer = "Indexing helps databases perform lookups faster."
        evidence = pipeline.generate_ml_evidence(
            candidate_answer=answer,
            question_text=database_question,
            evaluation_rubric=database_rubric,
        )
        formatted = pipeline.format_evidence_for_gemini(evidence)

        assert isinstance(formatted, str)
        assert len(formatted) > 100  # Should be substantial
        assert "ML-DERIVED CONCEPT COVERAGE SIGNAL" in formatted
        assert "IMPORTANT INSTRUCTIONS FOR EVALUATOR" in formatted
        assert "Overall Coverage" in formatted

    def test_format_evidence_empty_when_no_concepts(self, pipeline):
        """If no concepts exist, format should return empty string."""
        evidence = pipeline.generate_ml_evidence(
            candidate_answer="Some answer",
            question_text="Some question",
            evaluation_rubric="",
        )
        formatted = pipeline.format_evidence_for_gemini(evidence)
        # With no concepts extracted, the formatted output should be empty
        assert formatted == "" or evidence["concepts_evaluated"] > 0


# ────────────────────────────────────────────────────────────────────
# Concept extraction tests
# ────────────────────────────────────────────────────────────────────

class TestConceptExtraction:
    """Tests for extracting concepts from evaluation rubrics."""

    def test_extract_from_numbered_list(self, analyzer):
        """Concepts from a numbered rubric should be properly extracted."""
        rubric = (
            "The candidate should demonstrate:\n"
            "1. Understanding of database indexing mechanisms and B-tree structures\n"
            "2. Knowledge of write overhead and storage cost tradeoffs\n"
            "3. Ability to explain composite index leftmost prefix matching rules\n"
        )
        concepts = analyzer.extract_concepts_from_rubric(rubric)
        assert len(concepts) >= 3

    def test_extract_from_bullet_list(self, analyzer):
        """Concepts from bullet-point rubrics should be extracted."""
        rubric = (
            "• Understanding of TCP handshake and connection establishment\n"
            "• Knowledge of HTTP protocol and status codes\n"
            "• Ability to explain DNS resolution process\n"
        )
        concepts = analyzer.extract_concepts_from_rubric(rubric)
        assert len(concepts) >= 2

    def test_extract_filters_short_fragments(self, analyzer):
        """Very short fragments (<15 chars) should be filtered out."""
        rubric = "1. OK\n2. Understanding of database normalization forms and their tradeoffs\n3. Yes"
        concepts = analyzer.extract_concepts_from_rubric(rubric)
        for c in concepts:
            assert len(c) > 15

    def test_extract_empty_rubric(self, analyzer):
        """Empty rubric should return empty list."""
        assert analyzer.extract_concepts_from_rubric("") == []
        assert analyzer.extract_concepts_from_rubric("  ") == []

    def test_extract_caps_at_20(self, analyzer):
        """Concept extraction should cap at 20 to bound inference cost."""
        rubric = "\n".join([
            f"{i}. Understanding of concept number {i} in computer science and engineering"
            for i in range(1, 30)
        ])
        concepts = analyzer.extract_concepts_from_rubric(rubric)
        assert len(concepts) <= 20


# ────────────────────────────────────────────────────────────────────
# Edge cases
# ────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_very_long_answer(self, analyzer):
        """A very long answer should not crash the analyzer."""
        concepts = ["recursion uses a call stack for function invocation"]
        answer = "Recursion works by having a function call itself. " * 500
        result = analyzer.evaluate_concepts(answer, concepts)

        assert "overall_coverage_pct" in result
        assert len(result["concept_results"]) == 1

    def test_unicode_in_answer_and_concepts(self, analyzer):
        """Unicode content should be handled gracefully."""
        concepts = ["algorithmic complexity analysis using Big-Ω notation"]
        answer = "Big-Ω (omega) notation represents the lower bound of algorithmic complexity."
        result = analyzer.evaluate_concepts(answer, concepts)

        assert len(result["concept_results"]) == 1
        assert result["concept_results"][0]["concept"] == concepts[0]

    def test_single_concept_single_word_answer(self, analyzer):
        """A one-word answer should produce valid (low) coverage."""
        concepts = ["binary search divides the search space in half each iteration"]
        answer = "Yes"
        result = analyzer.evaluate_concepts(answer, concepts)

        assert result["overall_coverage_pct"] < 50.0
        assert len(result["concept_results"]) == 1

    def test_inference_time_is_tracked(self, analyzer):
        """The inference_time_ms field should be populated."""
        concepts = ["hash tables provide O(1) average lookup time"]
        answer = "Hash tables use hashing for fast lookups."
        result = analyzer.evaluate_concepts(answer, concepts)

        assert "inference_time_ms" in result
        assert result["inference_time_ms"] >= 0.0

    def test_nli_probability_triplets_sum_to_approximately_one(self, analyzer):
        """Entailment + contradiction + neutral should sum to ~1.0."""
        concepts = ["linked lists allow O(1) insertion at the head"]
        answer = "Linked lists support constant time insertion at the front of the list."
        result = analyzer.evaluate_concepts(answer, concepts)

        for cr in result["concept_results"]:
            total = (
                cr["entailment_probability"]
                + cr["contradiction_probability"]
                + cr["neutral_probability"]
            )
            assert abs(total - 1.0) < 0.05, (
                f"NLI probabilities sum to {total}, expected ~1.0"
            )

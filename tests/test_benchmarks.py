"""
Unit and integration tests for the Interview-ai-er realistic benchmark suite.

Validates that:
- Dataset sources remain separate (public, synthetic, interview-specific, manually curated)
- All 6 benchmark categories (A through F) execute cleanly
- Category D enforces distinction between dynamic test execution and ML defect risk
- Category E validates the 5 core adaptive selection behaviors
- Category C validates consistency, contradiction, and irrelevant rejection
- Category F validates monotonicity, difficulty sensitivity, and SEM reduction
- Reports are generated in both JSON and Markdown formats
"""
from __future__ import annotations

import json
import os
import tempfile
import pytest

from ml.evaluation.benchmarks.sources import (
    load_public_difficulty_samples,
    load_public_skill_samples,
    load_public_code_defect_samples,
    load_synthetic_difficulty_fixtures,
    load_synthetic_answer_concept_fixtures,
    load_synthetic_code_defect_fixtures,
    load_interview_specific_questions,
    load_interview_specific_answers,
    load_curated_difficulty_questions,
    load_curated_skill_questions,
    load_curated_code_samples,
)
from ml.evaluation.benchmarks.suites import (
    run_difficulty_benchmark,
    run_skills_benchmark,
    run_answer_concept_benchmark,
    run_code_defect_benchmark,
    run_adaptive_selection_benchmark,
    run_mastery_benchmark,
)
from ml.evaluation.benchmarks.runner import (
    run_full_benchmark_suite,
    generate_markdown_benchmark_report,
)


class TestBenchmarkSourcesSeparation:
    """Test that dataset sources are strictly kept separate with explicit provenance."""

    def test_sources_have_explicit_source_tags(self):
        public_diff = load_public_difficulty_samples(max_samples=5)
        assert len(public_diff) > 0
        for item in public_diff:
            assert item["source"] == "public_dataset"

        syn_diff = load_synthetic_difficulty_fixtures()
        assert len(syn_diff) > 0
        for item in syn_diff:
            assert item["source"] == "synthetic_fixtures"

        interview_q = load_interview_specific_questions()
        assert len(interview_q) > 0
        for item in interview_q:
            assert item["source"] == "interview_specific"

        curated_q = load_curated_difficulty_questions()
        assert len(curated_q) > 0
        for item in curated_q:
            assert item["source"] == "manually_curated"


class TestCategoryAQuestionDifficulty:
    """Test Category A: Question difficulty benchmark execution."""

    def test_difficulty_benchmark_structure(self):
        res = run_difficulty_benchmark()
        assert res["category"] == "A. Question difficulty"
        assert res["total_samples"] > 0
        assert "overall_accuracy" in res
        assert "overall_macro_f1" in res
        assert "overall_ordinal_mae" in res
        assert "per_source_breakdown" in res
        # Check all 4 sources are represented
        sources = set(res["per_source_breakdown"].keys())
        assert "public_dataset" in sources
        assert "synthetic_fixtures" in sources
        assert "interview_specific" in sources
        assert "manually_curated" in sources


class TestCategoryBQuestionSkills:
    """Test Category B: Question skills multi-label benchmark execution."""

    def test_skills_benchmark_structure(self):
        res = run_skills_benchmark()
        assert res["category"] == "B. Question skills"
        assert res["total_samples"] > 0
        assert "mean_jaccard_similarity" in res
        assert "mean_sample_f1" in res
        assert "per_source_breakdown" in res


class TestCategoryCAnswerConceptCoverage:
    """Test Category C: Answer concept coverage benchmark execution."""

    def test_answer_concept_evaluates_required_criteria(self):
        res = run_answer_concept_benchmark()
        assert res["category"] == "C. Answer concept coverage"

        # 1. Irrelevant answer rejection
        irr = res["irrelevant_answer_rejection"]
        assert "rejection_rate" in irr
        assert irr["rejection_rate"] >= 0.66  # Must reject vast majority of irrelevant inputs

        # 2. Contradiction detection
        contra = res["contradiction_detection"]
        assert "detection_rate" in contra
        assert contra["total_test_cases"] > 0

        # 3. Consistency evaluation
        consist = res["consistency_evaluation"]
        assert consist["is_100_percent_deterministic"] is True
        assert "mean_paraphrase_score_delta" in consist


class TestCategoryDCodeDefectDetection:
    """Test Category D: Code defect detection vs Dynamic test execution."""

    def test_test_execution_distinct_from_ml_defect_risk(self):
        res = run_code_defect_benchmark()
        assert res["category"] == "D. Code defect detection"
        assert "contingency_matrix_2x2" in res
        assert "divergence_analysis" in res

        # Must record samples where test execution correctness diverges from ML defect risk
        divergence = res["divergence_analysis"]
        assert divergence["divergent_cases_count"] > 0
        assert divergence["divergence_rate"] > 0.0


class TestCategoryEAdaptiveSelection:
    """Test Category E: Adaptive question selection across all 5 core behaviors."""

    def test_adaptive_selection_core_behaviors(self):
        res = run_adaptive_selection_benchmark()
        assert res["category"] == "E. Adaptive selection"

        crit = res["criteria_evaluations"]

        # 1. Avoids repeated questions
        assert crit["avoids_repeated_questions"]["passed"] is True
        assert crit["avoids_repeated_questions"]["duplicate_count"] == 0

        # 2. Targets low-confidence skills
        assert crit["targets_low_confidence_skills"]["passed"] is True
        assert crit["targets_low_confidence_skills"]["remediation_targeted"] is True

        # 3. Adjusts difficulty
        assert crit["adjusts_difficulty"]["passed"] is True

        # 4. Maintains skill diversity
        assert crit["maintains_skill_diversity"]["passed"] is True
        assert crit["maintains_skill_diversity"]["unique_skills_count"] >= 3

        # 5. Produces explainable selections
        assert crit["produces_explainable_selections"]["passed"] is True
        assert crit["produces_explainable_selections"]["all_explainable"] is True


class TestCategoryFMasteryEstimation:
    """Test Category F: Mastery estimation (2PL-IRT)."""

    def test_mastery_evaluates_psychometric_properties(self):
        res = run_mastery_benchmark()
        assert res["category"] == "F. Mastery estimation"

        evals = res["evaluations"]
        assert evals["monotonic_directionality"]["passed"] is True
        assert evals["difficulty_weighted_sensitivity"]["passed"] is True
        assert evals["sem_uncertainty_reduction"]["passed"] is True
        assert evals["scale_bounds_clamping"]["passed"] is True
        assert res["all_evaluations_passed"] is True


class TestFullBenchmarkSuiteExecution:
    """Test end-to-end benchmark runner and report generation."""

    def test_full_benchmark_suite_generates_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest = run_full_benchmark_suite(output_dir=tmp_dir)

            assert "benchmark_suite_version" in manifest
            assert len(manifest["suites"]) == 6

            # Verify JSON file
            json_file = os.path.join(tmp_dir, "benchmark_results.json")
            assert os.path.exists(json_file)
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                assert "suites" in data
                assert "difficulty" in data["suites"]
                assert "adaptive_selection" in data["suites"]

            # Verify Markdown file
            md_file = os.path.join(tmp_dir, "benchmark_report.md")
            assert os.path.exists(md_file)
            with open(md_file, "r", encoding="utf-8") as f:
                md_text = f.read()
                assert "# Production ML & Adaptive Benchmark Report" in md_text
                assert "A. Question Difficulty" in md_text
                assert "D. Code Defect Detection" in md_text
                assert "2x2 Orthogonal Contingency Matrix" in md_text
                assert "E. Adaptive Selection" in md_text

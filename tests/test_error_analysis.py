"""
Test suite for the ML Error-Analysis framework.
Verifies failure categorization, confusion matrices, per-class metrics,
hard example mining, false positive/negative detection, and JSON report generation.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import pytest

from ml.evaluation.error_analysis import (
    DifficultyErrorAnalyzer,
    DifficultyFailureCategory,
    SkillTaggerErrorAnalyzer,
    SkillFailureCategory,
    NLIAnswerAnalyzerErrorAnalyzer,
    NLIFailureCategory,
    CodeDefectErrorAnalyzer,
    CodeFailureCategory,
    MasteryErrorAnalyzer,
    MasteryFailureCategory,
    build_multiclass_confusion_matrix,
    compute_per_class_metrics_from_matrix,
    compute_confidence_distribution_metrics,
    run_all_model_error_analyses,
    ModelErrorReport,
)


class TestMetricsAndConfusionMatrix:
    """Test mathematical and matrix calculation routines."""

    def test_confusion_matrix_dimensions_and_counts(self):
        y_true = ["beginner", "intermediate", "advanced", "beginner"]
        y_pred = ["beginner", "advanced", "advanced", "intermediate"]
        labels = ["beginner", "intermediate", "advanced"]

        cm = build_multiclass_confusion_matrix(y_true, y_pred, labels)
        assert cm.labels == labels
        assert len(cm.matrix) == 3
        assert len(cm.matrix[0]) == 3

        # beginner: 1 beg, 1 int
        assert cm.matrix[0][0] == 1
        assert cm.matrix[0][1] == 1
        assert cm.matrix[0][2] == 0

        # Row normalization
        assert cm.normalized_matrix[0][0] == 0.5
        assert cm.normalized_matrix[0][1] == 0.5

    def test_per_class_metrics_computation(self):
        y_true = ["clean", "clean", "defective", "defective"]
        y_pred = ["clean", "defective", "clean", "defective"]
        labels = ["clean", "defective"]

        cm = build_multiclass_confusion_matrix(y_true, y_pred, labels)
        metrics = compute_per_class_metrics_from_matrix(cm)

        assert "clean" in metrics
        assert "defective" in metrics

        # Both classes have 1 TP, 1 FP, 1 FN
        assert metrics["clean"].precision == 0.5
        assert metrics["clean"].recall == 0.5
        assert metrics["clean"].f1_score == 0.5
        assert metrics["clean"].support == 2

    def test_confidence_distribution_metrics(self):
        confidences = [0.95, 0.85, 0.40, 0.30]
        is_correct = [True, True, False, False]

        cd = compute_confidence_distribution_metrics(confidences, is_correct, num_bins=5)
        assert len(cd.bin_edges) == 6
        assert len(cd.overall_counts) == 5
        assert cd.mean_confidence_correct > cd.mean_confidence_error
        assert cd.calibration_gap > 0

    def test_ascii_table_rendering(self):
        y_true = ["A", "B"]
        y_pred = ["A", "A"]
        labels = ["A", "B"]
        cm = build_multiclass_confusion_matrix(y_true, y_pred, labels)
        table = cm.to_ascii_table(title="Test Matrix")
        assert "Test Matrix" in table
        assert "True \\ Pred" in table
        assert "A" in table
        assert "B" in table


class TestDifficultyErrorAnalyzer:
    """Test Question Difficulty failure categorization and diagnostics."""

    def test_difficulty_analyzer_runs(self):
        analyzer = DifficultyErrorAnalyzer()
        report = analyzer.analyze()

        assert isinstance(report, ModelErrorReport)
        assert report.model_alias == "question-difficulty-v1"
        assert report.total_samples > 0
        assert len(report.confusion_matrix.labels) == 3
        assert len(report.per_class_metrics) == 3

    def test_difficulty_failure_categories_present(self):
        analyzer = DifficultyErrorAnalyzer()
        report = analyzer.analyze()

        counts = report.failure_category_counts
        # Check that specific failure categories are tracked in taxonomy
        assert DifficultyFailureCategory.EASY_AS_MEDIUM.value in counts
        assert DifficultyFailureCategory.MEDIUM_AS_HARD.value in counts
        assert DifficultyFailureCategory.HARD_AS_EASY.value in counts

    def test_difficulty_hard_examples_mined(self):
        analyzer = DifficultyErrorAnalyzer()
        report = analyzer.analyze()

        assert len(report.hard_examples) > 0
        first_hard = report.hard_examples[0]
        assert hasattr(first_hard, "input_snippet")
        assert hasattr(first_hard, "root_cause_explanation")


class TestSkillTaggerErrorAnalyzer:
    """Test Skill Tagger multi-label error categorization."""

    def test_skill_analyzer_runs(self):
        analyzer = SkillTaggerErrorAnalyzer()
        report = analyzer.analyze()

        assert isinstance(report, ModelErrorReport)
        assert report.model_alias == "question-skill-v1"
        assert report.total_samples > 0

    def test_skill_failure_categories(self):
        analyzer = SkillTaggerErrorAnalyzer()
        report = analyzer.analyze()

        counts = report.failure_category_counts
        assert SkillFailureCategory.MISSED_SKILL.value in counts
        assert SkillFailureCategory.INCORRECT_SKILL.value in counts
        assert SkillFailureCategory.AMBIGUOUS_TAG.value in counts

    def test_skill_false_positives_and_negatives_logged(self):
        analyzer = SkillTaggerErrorAnalyzer()
        report = analyzer.analyze()

        # Should catalogue both false positives and false negatives
        assert isinstance(report.false_positives, list)
        assert isinstance(report.false_negatives, list)


class TestNLIAnswerAnalyzerErrorAnalyzer:
    """Test Concept Coverage NLI failure categorization."""

    def test_nli_analyzer_runs(self):
        analyzer = NLIAnswerAnalyzerErrorAnalyzer()
        report = analyzer.analyze()

        assert isinstance(report, ModelErrorReport)
        assert report.model_alias == "answer-nli-v1"
        assert report.total_samples > 0

    def test_nli_failure_categories_tracked(self):
        analyzer = NLIAnswerAnalyzerErrorAnalyzer()
        report = analyzer.analyze()

        counts = report.failure_category_counts
        assert NLIFailureCategory.FALSE_ENTAILMENT.value in counts
        assert NLIFailureCategory.FALSE_CONTRADICTION.value in counts
        assert NLIFailureCategory.PARTIAL_COVERAGE_ERRORS.value in counts


class TestCodeDefectErrorAnalyzer:
    """Test Code Defect detector error categorization."""

    def test_code_defect_analyzer_runs(self):
        analyzer = CodeDefectErrorAnalyzer()
        report = analyzer.analyze()

        assert isinstance(report, ModelErrorReport)
        assert report.model_alias == "code-risk-v1"
        assert len(report.confusion_matrix.labels) == 2

    def test_code_failure_categories(self):
        analyzer = CodeDefectErrorAnalyzer()
        report = analyzer.analyze()

        counts = report.failure_category_counts
        assert CodeFailureCategory.FALSE_VULNERABILITY.value in counts
        assert CodeFailureCategory.MISSED_DEFECT.value in counts

    def test_code_false_positives_logged(self):
        analyzer = CodeDefectErrorAnalyzer()
        report = analyzer.analyze()

        # Defect model is sensitive, so false positives are catalogued
        assert len(report.false_positives) > 0
        first_fp = report.false_positives[0]
        assert "code" in first_fp
        assert "defect_prob" in first_fp


class TestMasteryErrorAnalyzer:
    """Test IRT Mastery Model ability estimation error categorization."""

    def test_mastery_analyzer_runs(self):
        analyzer = MasteryErrorAnalyzer()
        report = analyzer.analyze()

        assert isinstance(report, ModelErrorReport)
        assert report.model_alias == "mastery-v1"
        assert len(report.confusion_matrix.labels) == 3

    def test_mastery_over_under_estimation_detected(self):
        analyzer = MasteryErrorAnalyzer()
        report = analyzer.analyze()

        counts = report.failure_category_counts
        assert MasteryFailureCategory.OVERESTIMATION.value in counts
        assert MasteryFailureCategory.UNDERESTIMATION.value in counts
        assert counts[MasteryFailureCategory.OVERESTIMATION.value] > 0
        assert counts[MasteryFailureCategory.UNDERESTIMATION.value] > 0


class TestFullSuiteExecution:
    """Test running entire suite and exporting JSON manifests."""

    def test_run_all_model_error_analyses(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            results = run_all_model_error_analyses(output_dir=temp_dir)

            assert len(results) == 5
            expected_keys = {"difficulty", "skill_tagger", "nli_analyzer", "code_defect", "mastery"}
            assert set(results.keys()) == expected_keys

            # Check JSON output files
            for k in expected_keys:
                json_file = os.path.join(temp_dir, f"{k}_error_report.json")
                assert os.path.exists(json_file)
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    assert "model_name" in data
                    assert "confusion_matrix" in data
                    assert "per_class_metrics" in data
                    assert "failure_category_counts" in data
                    assert "hard_examples" in data

            # Check summary manifest
            summary_file = os.path.join(temp_dir, "error_analysis_summary.json")
            assert os.path.exists(summary_file)
            with open(summary_file, "r", encoding="utf-8") as f:
                sum_data = json.load(f)
                assert sum_data["models_analyzed"] == 5

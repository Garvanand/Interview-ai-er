"""
Command-line runner for ML Error Analysis across all five models.

Usage:
    python -m ml.evaluation.run_error_analysis [--output-dir reports/error_analysis]
"""
import argparse
import json
import logging
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from ml.evaluation.error_analysis import run_all_model_error_analyses

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("run_error_analysis")


def format_per_class_table(per_class: dict) -> str:
    lines = []
    lines.append(f"+{'-'*24}+{'-'*12}+{'-'*12}+{'-'*12}+{'-'*10}+")
    lines.append(f"| {'Class / Label':<22} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<8} |")
    lines.append(f"+{'-'*24}+{'-'*12}+{'-'*12}+{'-'*12}+{'-'*10}+")
    for lbl, m in per_class.items():
        prec = f"{m.precision:.3f}"
        rec = f"{m.recall:.3f}"
        f1 = f"{m.f1_score:.3f}"
        supp = f"{m.support}"
        lines.append(f"| {lbl:<22} | {prec:^10} | {rec:^10} | {f1:^10} | {supp:^8} |")
    lines.append(f"+{'-'*24}+{'-'*12}+{'-'*12}+{'-'*12}+{'-'*10}+")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run ML error analysis and generate diagnostic reports.")
    parser.add_argument(
        "--output-dir",
        default="reports/error_analysis",
        help="Directory to store JSON reports and diagnostic artifacts."
    )
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print(" INTERVIEW-AI-ER: PRODUCTION ML ERROR ANALYSIS WORKFLOW")
    print("=" * 80)
    print(f"Output directory: {os.path.abspath(args.output_dir)}\n")

    reports = run_all_model_error_analyses(output_dir=args.output_dir)

    for key, report in reports.items():
        print("\n" + "-" * 80)
        print(f" MODEL: {report.model_name} ({report.model_alias})")
        print(f" Samples: {report.total_samples} | Primary Metric: {report.accuracy_or_primary_metric:.3f} | Macro F1: {report.macro_f1:.3f}")
        print("-" * 80)

        # 1. Confusion Matrix
        print("\n[CONFUSION MATRIX]")
        print(report.confusion_matrix.to_ascii_table(title=f"{report.model_name} Confusion Matrix"))

        # 2. Per-class metrics
        print("\n[PER-CLASS METRICS]")
        print(format_per_class_table(report.per_class_metrics))

        # 3. Categorized failure breakdown
        print("\n[CATEGORIZED FAILURE MODES]")
        for cat, cnt in report.failure_category_counts.items():
            if cnt > 0:
                print(f"  • {cat:<32}: {cnt} cases")

        # 4. Hard examples
        if report.hard_examples:
            print(f"\n[HARD EXAMPLES ({len(report.hard_examples)} identified)]")
            for idx, ex in enumerate(report.hard_examples[:3], 1):
                print(f"  [{idx}] ID: {ex.example_id} | Category: {ex.error_category} | Conf: {ex.confidence:.2f}")
                print(f"      Input: {ex.input_snippet[:100]}")
                print(f"      True: {ex.true_label} | Pred: {ex.predicted_label}")
                print(f"      Root Cause: {ex.root_cause_explanation}")

        # 5. Confidence Distribution Summary
        cd = report.confidence_distribution
        print("\n[CONFIDENCE DISTRIBUTION]")
        print(f"  Mean Confidence (Correct): {cd.mean_confidence_correct:.3f}")
        print(f"  Mean Confidence (Errors):  {cd.mean_confidence_error:.3f}")
        print(f"  Calibration Separation Gap: {cd.calibration_gap:.3f}")

    print("\n" + "=" * 80)
    print(f" Error Analysis Complete. All diagnostic reports saved to '{args.output_dir}/'.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

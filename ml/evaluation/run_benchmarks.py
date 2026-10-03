"""
CLI entry point for running the realistic Interview-ai-er Benchmark Suite.

Executes all six categories:
A. Question difficulty
B. Question skills
C. Answer concept coverage
D. Code defect detection
E. Adaptive selection
F. Mastery estimation

Usage:
    python -m ml.evaluation.run_benchmarks [--output-dir reports]
"""
import argparse
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from ml.evaluation.benchmarks.runner import run_full_benchmark_suite


def main():
    parser = argparse.ArgumentParser(description="Run realistic benchmark suite for Interview-ai-er.")
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory to store benchmark_results.json and benchmark_report.md"
    )
    args = parser.parse_args()

    run_full_benchmark_suite(output_dir=args.output_dir)


if __name__ == "__main__":
    main()

"""
Benchmark Suite D: Code Defect Detection & Test Execution Correctness.

CRITICAL REQUIREMENT:
Dynamic Test Execution Correctness must be evaluated as DISTINCT from Static ML Defect Risk.

Evaluates:
1. Dynamic Test Execution Engine:
   - In-memory execution against unit test inputs & assertions
   - Runtime crash capture (ZeroDivisionError, IndexError, SyntaxError)
   - Dynamic pass/fail status
2. Static ML Defect Risk:
   - CodeBERT defect probability and risk band classification
3. Orthogonality Analysis:
   - 2x2 contingency matrix: Dynamic Test Pass/Fail vs Static ML Risk Low/High
   - Divergence case studies (Tests Pass with High ML Risk vs Tests Fail with Low ML Risk)
"""
from __future__ import annotations

import logging
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from ml.models.defect_detector import CodeDefectDetector
from ml.evaluation.benchmarks.sources import (
    load_public_code_defect_samples,
    load_synthetic_code_defect_fixtures,
    load_curated_code_samples,
)

logger = logging.getLogger(__name__)


def execute_python_code_tests(
    code_str: str,
    test_cases: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Executes Python function dynamically against unit test cases.
    Captures test passes, assertion failures, and runtime exceptions.
    """
    t0 = time.time()
    exec_scope: Dict[str, Any] = {}

    try:
        compiled = compile(code_str, "<benchmark_code>", "exec")
        exec(compiled, exec_scope)
    except SyntaxError as se:
        return {
            "all_passed": False,
            "tests_passed": 0,
            "tests_total": len(test_cases),
            "execution_error": f"SyntaxError: {se}",
            "execution_time_ms": round((time.time() - t0) * 1000, 2),
        }
    except Exception as e:
        return {
            "all_passed": False,
            "tests_passed": 0,
            "tests_total": len(test_cases),
            "execution_error": f"{type(e).__name__}: {e}",
            "execution_time_ms": round((time.time() - t0) * 1000, 2),
        }

    # Find the callable function
    target_func = None
    for val in exec_scope.values():
        if callable(val) and not isinstance(val, type):
            target_func = val
            break

    if target_func is None:
        return {
            "all_passed": False,
            "tests_passed": 0,
            "tests_total": len(test_cases),
            "execution_error": "No callable function found in code",
            "execution_time_ms": round((time.time() - t0) * 1000, 2),
        }

    passed_count = 0
    failure_reason = None

    for tc in test_cases:
        args = tc.get("input", ())
        if not isinstance(args, tuple):
            args = (args,)
        kwargs = tc.get("kwargs", {})
        expected = tc.get("expected")
        should_raise = tc.get("should_raise")

        try:
            actual = target_func(*args, **kwargs)
            if should_raise:
                failure_reason = f"Expected exception '{should_raise}' was not raised; returned {actual}"
                break
            elif actual == expected:
                passed_count += 1
            else:
                failure_reason = f"Assertion failed: expected {expected}, got {actual}"
                break
        except Exception as exc:
            if should_raise and type(exc).__name__ == should_raise:
                passed_count += 1
            else:
                failure_reason = f"Unhandled {type(exc).__name__}: {exc}"
                break

    all_passed = (passed_count == len(test_cases)) and (len(test_cases) > 0)
    return {
        "all_passed": all_passed,
        "tests_passed": passed_count,
        "tests_total": len(test_cases),
        "execution_error": failure_reason,
        "execution_time_ms": round((time.time() - t0) * 1000, 2),
    }


def run_code_defect_benchmark(detector: Optional[CodeDefectDetector] = None) -> Dict[str, Any]:
    """Runs Category D: Code Defect Detection & Test Execution benchmark."""
    model = detector or CodeDefectDetector()

    # Collect samples across public, synthetic, and curated sources
    sources = {
        "public_codexglue": load_public_code_defect_samples(),
        "synthetic_fixtures": load_synthetic_code_defect_fixtures(),
        "manually_curated": load_curated_code_samples(),
    }

    all_samples = []
    for s_name, s_list in sources.items():
        for item in s_list:
            item_copy = dict(item)
            item_copy["source_group"] = s_name
            all_samples.append(item_copy)

    evaluation_records = []
    # Contingency table: [Tests_Pass, Tests_Fail] x [ML_Low_Risk, ML_High_Risk]
    contingency = {
        "tests_pass_ml_low_risk": 0,    # Clean & passing (Ideal)
        "tests_pass_ml_high_risk": 0,   # Divergence: Passes unit tests, but has latent vulnerability/defect
        "tests_fail_ml_low_risk": 0,    # Divergence: Clean code with logic bug/typo
        "tests_fail_ml_high_risk": 0,   # Defective & crashing
    }

    for sample in all_samples:
        s_id = sample["id"]
        code = sample["code"]
        test_cases = sample.get("test_cases", [])

        # 1. Dynamic Test Execution Correctness
        exec_res = execute_python_code_tests(code, test_cases)
        tests_passed = exec_res["all_passed"]

        # 2. Static ML Defect Risk Detection
        t0 = time.time()
        ml_res = model.analyze_code(code, allow_llm=False)
        ml_latency_ms = (time.time() - t0) * 1000.0

        defect_prob = ml_res.get("defect_probability", 0.0)
        risk_band = ml_res.get("risk_band", "low")
        is_ml_high_risk = (defect_prob >= 0.40) or (risk_band in ("medium", "high"))

        # 3. Categorize into Orthogonal Grid
        if tests_passed and not is_ml_high_risk:
            contingency["tests_pass_ml_low_risk"] += 1
            quadrant = "tests_pass_ml_low_risk"
        elif tests_passed and is_ml_high_risk:
            contingency["tests_pass_ml_high_risk"] += 1
            quadrant = "tests_pass_ml_high_risk"
        elif not tests_passed and not is_ml_high_risk:
            contingency["tests_fail_ml_low_risk"] += 1
            quadrant = "tests_fail_ml_low_risk"
        else:
            contingency["tests_fail_ml_high_risk"] += 1
            quadrant = "tests_fail_ml_high_risk"

        evaluation_records.append({
            "id": s_id,
            "source": sample.get("source_group", "unknown"),
            "scenario": sample.get("scenario", "standard"),
            "dynamic_tests_passed": tests_passed,
            "tests_passed_count": f"{exec_res['tests_passed']}/{exec_res['tests_total']}",
            "execution_error": exec_res["execution_error"],
            "ml_defect_probability": round(defect_prob, 4),
            "ml_risk_band": risk_band,
            "quadrant": quadrant,
            "notes": sample.get("notes", ""),
        })

    total_samples = len(evaluation_records)
    divergence_count = contingency["tests_pass_ml_high_risk"] + contingency["tests_fail_ml_low_risk"]
    divergence_rate = divergence_count / total_samples if total_samples > 0 else 0.0

    return {
        "category": "D. Code defect detection",
        "model_evaluated": "CodeDefectDetector",
        "total_samples": total_samples,
        "contingency_matrix_2x2": {
            "tests_pass_ml_low_risk": contingency["tests_pass_ml_low_risk"],
            "tests_pass_ml_high_risk": contingency["tests_pass_ml_high_risk"],
            "tests_fail_ml_low_risk": contingency["tests_fail_ml_low_risk"],
            "tests_fail_ml_high_risk": contingency["tests_fail_ml_high_risk"],
        },
        "divergence_analysis": {
            "divergent_cases_count": divergence_count,
            "divergence_rate": round(divergence_rate, 4),
            "significance_note": (
                "Confirms that dynamic test execution correctness is distinct from static ML defect risk. "
                f"{divergence_count} of {total_samples} samples ({divergence_rate:.1%}) exhibit divergence: "
                "either passing unit tests despite latent code defects, or failing assertions with clean syntax."
            )
        },
        "sample_records": evaluation_records,
    }

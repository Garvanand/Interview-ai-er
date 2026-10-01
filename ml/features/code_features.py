"""
Lexical, AST, and structural feature extraction for code submissions.
Used to support defect risk prediction, complexity heuristics, and tabular heads.
"""
from __future__ import annotations

import ast
import re
from typing import Any, Dict


def extract_code_lexical_features(code: str, language: str = "python") -> Dict[str, Any]:
    """Extract structural metrics: line count, cyclomatic complexity indicators, recursion patterns, etc."""
    lines = code.splitlines()
    non_empty = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]

    features: Dict[str, Any] = {
        "raw_character_count": len(code),
        "total_lines": len(lines),
        "non_empty_lines": len(non_empty),
        "has_loops": bool(re.search(r"\b(for|while)\b", code)),
        "nested_loop_depth": 0,
        "has_recursion": False,
        "has_try_except": bool(re.search(r"\b(try|except|catch|throw)\b", code)),
        "has_recursion_call": False,
        "syntax_valid": False,
    }

    if language.lower() in ("python", "py"):
        try:
            tree = ast.parse(code)
            features["syntax_valid"] = True

            func_defs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            func_names = {f.name for f in func_defs}

            # Check for recursive function calls
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in func_names:
                        features["has_recursion"] = True
                        break
        except Exception:
            features["syntax_valid"] = False

    return features

"""
Code execution sandbox infrastructure.

Provides isolated process execution with timeouts for candidate code submissions.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CodeSandbox:
    """Local process execution sandbox with strict execution timeouts."""

    def __init__(self, timeout_seconds: int = 5):
        self.timeout_seconds = timeout_seconds

    def execute(self, code: str, language: str, test_inputs: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute code in a contained environment based on language."""
        lang = language.strip().lower()
        if lang == "python":
            return self._execute_python(code, test_inputs)
        elif lang in ["javascript", "typescript", "js", "ts"]:
            return self._execute_javascript(code, test_inputs)
        else:
            return {
                "success": False,
                "error": f"Language '{language}' is not currently supported by the local sandbox.",
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
            }

    def _execute_python(self, code: str, test_inputs: Optional[List[str]] = None) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "solution.py")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            python_executable = sys.executable

            try:
                process = subprocess.run(
                    [python_executable, file_path],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
                return {
                    "success": process.returncode == 0,
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                    "exit_code": process.returncode,
                }
            except subprocess.TimeoutExpired as e:
                stdout = e.stdout.decode("utf-8") if isinstance(e.stdout, bytes) else (e.stdout or "")
                stderr = e.stderr.decode("utf-8") if isinstance(e.stderr, bytes) else (e.stderr or "")
                return {
                    "success": False,
                    "error": f"Execution timed out after {self.timeout_seconds} seconds.",
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": 124,
                }
            except Exception as e:
                logger.error("Python execution error: %s", e)
                return {
                    "success": False,
                    "error": str(e),
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                }

    def _execute_javascript(self, code: str, test_inputs: Optional[List[str]] = None) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "solution.js")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            try:
                process = subprocess.run(
                    ["node", file_path],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
                return {
                    "success": process.returncode == 0,
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                    "exit_code": process.returncode,
                }
            except subprocess.TimeoutExpired as e:
                stdout = e.stdout.decode("utf-8") if isinstance(e.stdout, bytes) else (e.stdout or "")
                stderr = e.stderr.decode("utf-8") if isinstance(e.stderr, bytes) else (e.stderr or "")
                return {
                    "success": False,
                    "error": f"Execution timed out after {self.timeout_seconds} seconds.",
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": 124,
                }
            except FileNotFoundError:
                return {
                    "success": False,
                    "error": "Node.js is not installed or not available in the system PATH.",
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                }
            except Exception as e:
                logger.error("JavaScript execution error: %s", e)
                return {
                    "success": False,
                    "error": str(e),
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                }

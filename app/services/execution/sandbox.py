import tempfile
import subprocess
import os
import sys
from typing import Dict, Any

class CodeSandbox:
    """
    A local process execution sandbox. 
    In a real production environment with untrusted code, this would use Docker/gVisor.
    Given deployment constraints, we use subprocess isolation with timeouts.
    """
    def __init__(self, timeout_seconds: int = 5):
        self.timeout_seconds = timeout_seconds

    def execute(self, code: str, language: str, test_inputs: list[str] = None) -> Dict[str, Any]:
        """Execute code in a contained environment based on language."""
        if language == "python":
            return self._execute_python(code, test_inputs)
        elif language in ["javascript", "typescript", "js", "ts"]:
            return self._execute_javascript(code, test_inputs)
        else:
            return {
                "success": False,
                "error": f"Language '{language}' is not currently supported by the local sandbox.",
                "stdout": "",
                "stderr": "",
                "exit_code": -1
            }

    def _execute_python(self, code: str, test_inputs: list[str] = None) -> Dict[str, Any]:
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
                    timeout=self.timeout_seconds
                )
                
                return {
                    "success": process.returncode == 0,
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                    "exit_code": process.returncode
                }
            except subprocess.TimeoutExpired as e:
                return {
                    "success": False,
                    "error": f"Execution timed out after {self.timeout_seconds} seconds.",
                    "stdout": (e.stdout.decode('utf-8') if isinstance(e.stdout, bytes) else e.stdout) if e.stdout else "",
                    "stderr": (e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else e.stderr) if e.stderr else "",
                    "exit_code": 124
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1
                }
                
    def _execute_javascript(self, code: str, test_inputs: list[str] = None) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "solution.js")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
            
            try:
                process = subprocess.run(
                    ["node", file_path],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds
                )
                
                return {
                    "success": process.returncode == 0,
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                    "exit_code": process.returncode
                }
            except subprocess.TimeoutExpired as e:
                return {
                    "success": False,
                    "error": f"Execution timed out after {self.timeout_seconds} seconds.",
                    "stdout": (e.stdout.decode('utf-8') if isinstance(e.stdout, bytes) else e.stdout) if e.stdout else "",
                    "stderr": (e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else e.stderr) if e.stderr else "",
                    "exit_code": 124
                }
            except FileNotFoundError:
                return {
                    "success": False,
                    "error": "Node.js is not installed or not available in the system PATH.",
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1
                }

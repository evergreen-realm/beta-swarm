import ast
import importlib.util
import logging
import os
import re
import subprocess
import tempfile
from typing import Dict, Any, List

from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class SentryLayerAgent(BaseAgent):
    """
    Sentry Layer Agent — Security: Triple Gate
    Three sequential gates that code must pass before merge is allowed:
      Gate 1 — Static Analysis:  syntax + py_compile
      Gate 2 — Semantic Analysis: dangerous patterns, bare excepts, credentials
      Gate 3 — Runtime Analysis:  safe import to catch import-time crashes
    """

    def __init__(self, brain=None):
        super().__init__("sentry", "Sentry Agent", "sentry", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        # Support legacy callers that pass a bare string
        if not isinstance(task, dict):
            task = {"code": str(task), "file_path": "unknown.py"}

        code = task.get("code", "")
        file_path = task.get("file_path", "unknown.py")

        # Run three gates
        static = self._static_analysis(code, file_path)
        semantic = self._semantic_analysis(code, file_path)
        runtime = self._runtime_analysis(code, file_path)

        all_passed = (
            static["passed"] and semantic["passed"] and runtime["passed"]
        )

        logger.info(
            f"[Sentry] Static={static['passed']}  "
            f"Semantic={semantic['passed']}  "
            f"Runtime={runtime['passed']}  -> {'APPROVED' if all_passed else 'BLOCKED'}"
        )

        if self.brain:
            self.brain.store_fact(
                self.agent_id,
                (
                    f"Sentry: Static={static['passed']}, "
                    f"Semantic={semantic['passed']}, "
                    f"Runtime={runtime['passed']}"
                ),
                "sentry",
            )

        return {
            "status": "approved" if all_passed else "blocked",
            "gates": {
                "static": static,
                "semantic": semantic,
                "runtime": runtime,
            },
            "can_merge": all_passed,
        }

    # ------------------------------------------------------------------
    # Gate 1 — Static Analysis
    # ------------------------------------------------------------------

    def _static_analysis(self, code: str, path: str) -> Dict[str, Any]:
        """
        Parse the code as an AST and optionally run py_compile.
        Catches syntax errors and compilation failures.
        """
        issues: List[Dict] = []

        if not code.strip():
            return {"passed": True, "issues": []}

        # AST parse
        try:
            ast.parse(code, filename=path)
        except SyntaxError as e:
            issues.append({
                "severity": "error",
                "gate": "static",
                "message": f"Syntax error at line {e.lineno}: {e.msg}",
            })

        # py_compile (only for .py files)
        if path.endswith(".py") and code.strip():
            tmp_path = None
            try:
                fd, tmp_path = tempfile.mkstemp(suffix=".py")
                os.close(fd)
                with open(tmp_path, "w", encoding="utf-8") as f:
                    f.write(code)

                result = subprocess.run(
                    ["python", "-m", "py_compile", tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    stderr = result.stderr.strip()
                    # Don't duplicate the AST parse error we already caught
                    if stderr and "SyntaxError" not in str(issues):
                        issues.append({
                            "severity": "error",
                            "gate": "static",
                            "message": f"py_compile failed: {stderr[-300:]}",
                        })
            except FileNotFoundError:
                pass  # python not on PATH
            except subprocess.TimeoutExpired:
                issues.append({
                    "severity": "warning",
                    "gate": "static",
                    "message": "py_compile timed out",
                })
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        has_errors = any(i["severity"] == "error" for i in issues)
        return {"passed": not has_errors, "issues": issues}

    # ------------------------------------------------------------------
    # Gate 2 — Semantic Analysis
    # ------------------------------------------------------------------

    _DANGEROUS_PATTERNS: List[Dict[str, str]] = [
        {"pattern": "eval(",             "severity": "warning",
         "message": "eval() detected — potential code injection"},
        {"pattern": "exec(",             "severity": "warning",
         "message": "exec() detected — potential code injection"},
        {"pattern": "__import__(",       "severity": "warning",
         "message": "__import__() detected — dynamic import"},
        {"pattern": "subprocess.call(",  "severity": "warning",
         "message": "subprocess.call() detected — prefer subprocess.run"},
        {"pattern": "os.system(",        "severity": "warning",
         "message": "os.system() detected — use subprocess instead"},
        {"pattern": "pickle.loads(",     "severity": "warning",
         "message": "pickle.loads() detected — deserialization risk"},
        {"pattern": "marshal.loads(",    "severity": "warning",
         "message": "marshal.loads() detected — deserialization risk"},
        {"pattern": "shell=True",        "severity": "warning",
         "message": "subprocess with shell=True — shell injection risk"},
        {"pattern": "verify=False",      "severity": "warning",
         "message": "TLS verification disabled"},
    ]

    _YAML_UNSAFE = re.compile(r"yaml\.load\((?!.*Loader\s*=\s*(?:Safe|Full))")

    def _semantic_analysis(self, code: str, path: str) -> Dict[str, Any]:
        """Check for dangerous patterns, bare excepts, and possible credentials."""
        issues: List[Dict] = []

        # Dangerous function / pattern checks
        for entry in self._DANGEROUS_PATTERNS:
            if entry["pattern"] in code:
                issues.append({
                    "severity": entry["severity"],
                    "gate": "semantic",
                    "message": entry["message"],
                })

        # yaml.load without SafeLoader
        if self._YAML_UNSAFE.search(code):
            issues.append({
                "severity": "warning",
                "gate": "semantic",
                "message": "yaml.load() without SafeLoader",
            })

        # Bare except clause
        if re.search(r"\bexcept\s*:", code):
            issues.append({
                "severity": "warning",
                "gate": "semantic",
                "message": "Bare except clause — catches KeyboardInterrupt/SystemExit",
            })

        # Possible hardcoded credentials (heuristic)
        cred_pattern = re.compile(
            r"""(?:password|passwd|secret|api_key|token)\s*=\s*['"][^'"]{8,}['"]""",
            re.IGNORECASE,
        )
        if cred_pattern.search(code):
            issues.append({
                "severity": "warning",
                "gate": "semantic",
                "message": "Possible hardcoded credential in assignment",
            })

        has_errors = any(i["severity"] == "error" for i in issues)
        return {"passed": not has_errors, "issues": issues}

    # ------------------------------------------------------------------
    # Gate 3 — Runtime Analysis
    # ------------------------------------------------------------------

    def _runtime_analysis(self, code: str, path: str) -> Dict[str, Any]:
        """
        Attempt a safe import of the code to catch import-time errors
        (missing dependencies, global side-effects that crash, etc.).
        Only runs on Python files.
        """
        issues: List[Dict] = []

        if not code.strip() or not path.endswith(".py"):
            return {"passed": True, "issues": []}

        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".py")
            os.close(fd)
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(code)

            spec = importlib.util.spec_from_file_location(
                "sentry_runtime_check", tmp_path
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

        except Exception as e:
            issues.append({
                "severity": "error",
                "gate": "runtime",
                "message": f"Runtime import error: {type(e).__name__}: {e}",
            })
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        has_errors = any(i["severity"] == "error" for i in issues)
        return {"passed": not has_errors, "issues": issues}

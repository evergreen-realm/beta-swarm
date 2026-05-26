import ast
import logging
import os
import re
from typing import Dict, Any, List

from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class X3PerformanceReviewAgent(BaseAgent):
    """
    X3: Performance Review Agent
    Review: Performance
    Detects N+1 query patterns, missing caching on API endpoints,
    and synchronous blocking I/O inside async functions.
    """

    def __init__(self, brain=None):
        super().__init__("x3_performance", "Performance Review Agent", "review", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_path = task.get("project_path", "./projects/new_project")
        findings: List[Dict] = []

        # 1. N+1 query detection
        findings.extend(self._check_n_plus_one(project_path))

        # 2. Missing caching check
        findings.extend(self._check_caching(project_path))

        # 3. Blocking I/O inside async code
        findings.extend(self._check_blocking(project_path))

        # 4. Unbounded queries (no LIMIT)
        findings.extend(self._check_unbounded_queries(project_path))

        passed = len([f for f in findings if f["severity"] == "critical"]) == 0

        logger.info(f"[X3] Performance review: {len(findings)} issues, passed={passed}")

        if self.brain:
            self.brain.store_fact(
                self.agent_id,
                f"Performance: {len(findings)} issues, passed={passed}",
                "performance",
            )

        return {
            "status": "complete",
            "findings": findings,
            "passed": passed,
        }

    # ------------------------------------------------------------------
    # N+1 query detection (AST-based)
    # ------------------------------------------------------------------

    def _check_n_plus_one(self, path: str) -> List[Dict]:
        """
        Look for patterns like:
            for item in queryset:        # loop
                item.related.do_stuff()  # query inside loop
        Uses AST to find DB-access calls nested inside For loops.
        """
        findings: List[Dict] = []
        db_calls = {"query", "execute", "fetch", "fetchone", "fetchall",
                     "filter", "get", "all", "select", "find", "find_one"}

        for filepath, tree in self._iter_py_asts(path):
            for node in ast.walk(tree):
                if not isinstance(node, (ast.For, ast.AsyncFor)):
                    continue
                # Walk children of the for-body looking for DB-like calls
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func_name = _call_name(child)
                        if func_name and func_name in db_calls:
                            findings.append({
                                "severity": "warning",
                                "type": "potential_n_plus_one",
                                "file": filepath,
                                "line": getattr(child, "lineno", 0),
                                "message": f"DB call '{func_name}()' inside loop — possible N+1",
                            })
        return findings

    # ------------------------------------------------------------------
    # Caching check
    # ------------------------------------------------------------------

    def _check_caching(self, path: str) -> List[Dict]:
        """
        Flag API route handlers that do not mention any caching mechanism.
        """
        findings: List[Dict] = []
        cache_keywords = {"cache", "cached", "lru_cache", "ttl", "redis",
                          "memcache", "cache_control", "Cache-Control"}

        for filepath, tree in self._iter_py_asts(path):
            source = _read_source(filepath)
            if source is None:
                continue

            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                # Only look at functions decorated with router/app route decorators
                is_route = any(
                    _decorator_name(d) in {"get", "post", "put", "delete", "patch",
                                           "route", "api_view"}
                    for d in node.decorator_list
                ) if node.decorator_list else False

                if not is_route:
                    continue

                # Extract the function source lines
                func_lines = source[node.lineno - 1 : node.end_lineno]
                func_text = "\n".join(func_lines)

                if not any(kw in func_text.lower() for kw in cache_keywords):
                    findings.append({
                        "severity": "info",
                        "type": "missing_cache",
                        "file": filepath,
                        "line": node.lineno,
                        "message": f"Route handler '{node.name}' has no caching",
                    })

        return findings

    # ------------------------------------------------------------------
    # Blocking I/O in async functions
    # ------------------------------------------------------------------

    def _check_blocking(self, path: str) -> List[Dict]:
        """
        Flag synchronous blocking calls (requests.*, open(), time.sleep())
        inside ``async def`` functions.
        """
        findings: List[Dict] = []
        blocking_calls = {
            "requests.get", "requests.post", "requests.put",
            "requests.delete", "requests.patch", "requests.head",
            "time.sleep", "open",
        }

        for filepath, tree in self._iter_py_asts(path):
            for node in ast.walk(tree):
                if not isinstance(node, ast.AsyncFunctionDef):
                    continue
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        name = _call_name(child)
                        if name and name in blocking_calls:
                            findings.append({
                                "severity": "warning",
                                "type": "blocking_io",
                                "file": filepath,
                                "line": getattr(child, "lineno", 0),
                                "message": (
                                    f"Blocking call '{name}()' inside "
                                    f"async function '{node.name}'"
                                ),
                            })
        return findings

    # ------------------------------------------------------------------
    # Unbounded query detection
    # ------------------------------------------------------------------

    def _check_unbounded_queries(self, path: str) -> List[Dict]:
        """
        Flag `.all()` calls that are not followed by `.limit()` or slicing.
        """
        findings: List[Dict] = []
        pattern = re.compile(r"\.all\(\)\s*(?!\[|\.limit)", re.IGNORECASE)

        for filepath, content in self._iter_files(path, (".py",)):
            for m in pattern.finditer(content):
                findings.append({
                    "severity": "info",
                    "type": "unbounded_query",
                    "file": filepath,
                    "line": content[:m.start()].count("\n") + 1,
                    "message": "Unbounded .all() query — consider adding .limit()",
                })

        return findings

    # ------------------------------------------------------------------
    # Iterators / helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _iter_py_asts(path: str):
        """Yield (filepath, ast.Module) for every parseable .py file."""
        skip_dirs = {".git", "__pycache__", "venv", ".venv", "node_modules"}
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                if not file.endswith(".py"):
                    continue
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read(), filename=filepath)
                    yield filepath, tree
                except (SyntaxError, ValueError):
                    continue

    @staticmethod
    def _iter_files(path: str, extensions: tuple):
        skip_dirs = {".git", "__pycache__", "venv", ".venv", "node_modules"}
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                if file.endswith(extensions):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            yield filepath, f.read()
                    except OSError:
                        continue


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _call_name(node: ast.Call) -> str | None:
    """Extract a dotted name from a Call node, e.g. 'requests.get'."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            return f"{func.value.id}.{func.attr}"
        return func.attr
    return None


def _decorator_name(node: ast.expr) -> str:
    """Best-effort decorator name extraction."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _read_source(filepath: str) -> list | None:
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.readlines()
    except OSError:
        return None

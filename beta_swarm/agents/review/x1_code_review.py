import ast
import logging
import os
import re
from typing import Dict, Any, List

from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class X1CodeReviewAgent(BaseAgent):
    """
    X1: Code Review Agent
    Review: Structural Analysis
    Detects dead code, circular dependencies, and excessive complexity
    by walking the Python AST of every .py file under the project path.
    """

    def __init__(self, brain=None):
        super().__init__("x1_review", "Code Review Agent", "review", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_path = task.get("project_path", "./projects/new_project")
        issues: List[Dict] = []

        # --- Dead code detection ---
        dead = self._find_dead_code(project_path)
        for d in dead:
            issues.append({
                "severity": "warning",
                "type": "dead_code",
                "message": f"Potentially unused: {d['name']}",
                "file": d["file"],
            })

        # --- Circular dependency detection ---
        circular = self._find_circular_deps(project_path)
        for c in circular:
            issues.append({
                "severity": "error",
                "type": "circular_dependency",
                "message": c,
            })

        # --- Cyclomatic-complexity check ---
        complexity = self._check_complexity(project_path)
        for c in complexity:
            issues.append({
                "severity": "warning",
                "type": "high_complexity",
                "message": c,
            })

        passed = len([i for i in issues if i["severity"] == "error"]) == 0

        logger.info(
            f"[X1] Code review: {len(issues)} issues, passed={passed}"
        )

        if self.brain:
            self.brain.store_fact(
                self.agent_id,
                f"Code review: {len(issues)} issues, passed={passed}",
                "review",
            )

        return {
            "status": "complete",
            "issues": issues,
            "passed": passed,
        }

    # ------------------------------------------------------------------
    # Dead-code detection (AST-based)
    # ------------------------------------------------------------------

    def _find_dead_code(self, path: str) -> List[Dict]:
        """
        Walk every .py file; collect function *definitions* and *name
        references*.  Any function that is defined but never referenced
        (excluding common entry-points) is flagged.
        """
        dead: List[Dict] = []
        # Built-in / framework names we should never flag
        whitelist = {
            "__init__", "__str__", "__repr__", "__enter__", "__exit__",
            "__aenter__", "__aexit__", "__call__", "__getattr__",
            "main", "execute", "run", "setup", "teardown",
            "setUp", "tearDown", "setUpClass", "tearDownClass",
        }

        for root, _, files in os.walk(path):
            if _skip_dir(root):
                continue
            for file in files:
                if not file.endswith(".py"):
                    continue
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read(), filename=filepath)
                except (SyntaxError, ValueError):
                    continue

                defined: set = set()
                used: set = set()

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        defined.add(node.name)
                    elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                        used.add(node.id)
                    elif isinstance(node, ast.Attribute):
                        used.add(node.attr)

                for func in defined - used - whitelist:
                    if not func.startswith("_test"):
                        dead.append({"name": func, "file": filepath})

        return dead

    # ------------------------------------------------------------------
    # Circular-dependency detection
    # ------------------------------------------------------------------

    def _find_circular_deps(self, path: str) -> List[str]:
        """
        Build a module → [imported-modules] adjacency list, then run DFS
        cycle detection.  Reports cycles as human-readable strings.
        """
        imports: Dict[str, List[str]] = {}

        for root, _, files in os.walk(path):
            if _skip_dir(root):
                continue
            for file in files:
                if not file.endswith(".py"):
                    continue
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read(), filename=filepath)
                except (SyntaxError, ValueError):
                    continue
                mods: List[str] = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            mods.append(alias.name)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        mods.append(node.module)
                imports[filepath] = mods

        # DFS cycle detection
        cycles: List[str] = []
        visited: set = set()
        rec_stack: set = set()
        path_list: List[str] = []

        def _dfs(node: str):
            visited.add(node)
            rec_stack.add(node)
            path_list.append(node)
            for dep_module in imports.get(node, []):
                # Find files that could correspond to this module
                for candidate in imports:
                    mod_path = dep_module.replace(".", os.sep)
                    if mod_path in candidate:
                        if candidate in rec_stack:
                            cycle_start = path_list.index(candidate)
                            cycle = path_list[cycle_start:] + [candidate]
                            short = " -> ".join(
                                os.path.basename(c) for c in cycle
                            )
                            msg = f"Circular import: {short}"
                            if msg not in cycles:
                                cycles.append(msg)
                        elif candidate not in visited:
                            _dfs(candidate)
            path_list.pop()
            rec_stack.discard(node)

        for node in imports:
            if node not in visited:
                _dfs(node)

        return cycles

    # ------------------------------------------------------------------
    # Complexity check (node-count heuristic per function)
    # ------------------------------------------------------------------

    def _check_complexity(self, path: str) -> List[str]:
        """
        For each function, count the number of AST nodes as a rough
        complexity proxy.  Flag functions exceeding the threshold.
        """
        threshold = 100
        issues: List[str] = []

        for root, _, files in os.walk(path):
            if _skip_dir(root):
                continue
            for file in files:
                if not file.endswith(".py"):
                    continue
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read(), filename=filepath)
                except (SyntaxError, ValueError):
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        node_count = len(list(ast.walk(node)))
                        if node_count > threshold:
                            issues.append(
                                f"{filepath}:{node.name} complexity={node_count}"
                            )
        return issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _skip_dir(path: str) -> bool:
    """Skip VCS, virtual-env, and cache directories."""
    skip = {".git", "__pycache__", "venv", ".venv", "node_modules", ".tox", "dist"}
    parts = set(path.replace("\\", "/").split("/"))
    return bool(parts & skip)

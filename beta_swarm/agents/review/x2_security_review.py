import logging
import math
import os
import re
import subprocess
import json
from typing import Dict, Any, List

from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns for common secret / credential leaks
# ---------------------------------------------------------------------------
_SECRET_PATTERNS: Dict[str, re.Pattern] = {
    "api_key":      re.compile(r"""api[_-]?key\s*=\s*['"][a-zA-Z0-9_\-.]{32,}['"]""", re.IGNORECASE),
    "password":     re.compile(r"""password\s*=\s*['"][^'"]{8,}['"]""",                re.IGNORECASE),
    "secret":       re.compile(r"""secret\s*=\s*['"][a-zA-Z0-9_\-.]{16,}['"]""",      re.IGNORECASE),
    "token":        re.compile(r"""token\s*=\s*['"][a-zA-Z0-9_\-.]{20,}['"]""",       re.IGNORECASE),
    "aws_key":      re.compile(r"""AKIA[0-9A-Z]{16}"""),
    "private_key":  re.compile(r"""-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----"""),
}

_SQL_INJECTION_PATTERN = re.compile(
    r"""execute\s*\(\s*['"].*?%[sd].*?['"]\s*\)"""
    r"""|execute\s*\(\s*f['"]"""
    r"""|\.format\s*\(.*\).*execute""",
    re.IGNORECASE,
)

_XSS_PATTERNS = re.compile(
    r"""innerHTML\s*="""
    r"""|document\.write\s*\("""
    r"""|\.html\s*\([^)]*\+"""
    r"""|dangerouslySetInnerHTML""",
)

# File extensions worth scanning
_CODE_EXTS = (".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".yaml", ".yml",
              ".env", ".cfg", ".ini", ".conf", ".json")


class X2SecurityReviewAgent(BaseAgent):
    """
    X2: Security Review Agent
    Review: Security Audit
    Scans the project for hardcoded secrets (regex + Shannon entropy),
    SQL injection patterns, and XSS risks.
    """

    def __init__(self, brain=None):
        super().__init__("x2_security", "Security Review Agent", "review", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_path = task.get("project_path", "./projects/new_project")
        self._log_handover(f"X2 Security Review started. path={project_path}")
        findings: List[Dict] = []

        # 1. Secret scanning (regex + Shannon entropy)
        findings.extend(self._scan_secrets(project_path))

        # 2. SQL injection
        findings.extend(self._scan_sql_injection(project_path))

        # 3. XSS
        findings.extend(self._scan_xss(project_path))

        # 4. bandit static analysis (if installed)
        findings.extend(self._run_bandit(project_path))

        # 5. ruff security rules (if installed)
        findings.extend(self._run_ruff_security(project_path))

        passed = len([f for f in findings if f["severity"] in ("critical", "high")]) == 0

        logger.info(f"[X2] Security scan: {len(findings)} findings, passed={passed}")
        self._log_handover(f"X2 completed. {len(findings)} findings, passed={passed}")

        if self.brain:
            self.brain.store_fact(
                self.agent_id,
                f"Security: {len(findings)} findings, passed={passed}",
                "security",
            )

        return {
            "status": "complete",
            "findings": findings,
            "passed": passed,
            "next_stage": task.get("next_stage", "x3_performance_review")
        }

    # ------------------------------------------------------------------
    # Secret scanning
    # ------------------------------------------------------------------

    def _scan_secrets(self, path: str) -> List[Dict]:
        findings: List[Dict] = []

        for filepath, content in self._iter_files(path, _CODE_EXTS):
            # Regex-based checks
            for secret_type, pattern in _SECRET_PATTERNS.items():
                for match in pattern.finditer(content):
                    findings.append({
                        "severity": "critical",
                        "type": "hardcoded_secret",
                        "subtype": secret_type,
                        "file": filepath,
                        "line": content[:match.start()].count("\n") + 1,
                        "message": f"Potential hardcoded {secret_type} detected",
                    })

            # Entropy-based checks: scan for high-entropy strings that look
            # like keys/tokens (only in assignment contexts)
            for m in re.finditer(
                r"""['"]((?:[A-Za-z0-9+/=_\-]){40,})['"]""", content
            ):
                candidate = m.group(1)
                ent = self._shannon_entropy(candidate)
                if ent > 4.5:
                    findings.append({
                        "severity": "warning",
                        "type": "high_entropy_string",
                        "file": filepath,
                        "line": content[:m.start()].count("\n") + 1,
                        "entropy": round(ent, 2),
                        "message": f"High-entropy string (entropy={ent:.2f}), possible secret",
                    })

        return findings

    # ------------------------------------------------------------------
    # SQL injection detection
    # ------------------------------------------------------------------

    def _scan_sql_injection(self, path: str) -> List[Dict]:
        findings: List[Dict] = []

        for filepath, content in self._iter_files(path, (".py",)):
            for match in _SQL_INJECTION_PATTERN.finditer(content):
                findings.append({
                    "severity": "high",
                    "type": "sql_injection",
                    "file": filepath,
                    "line": content[:match.start()].count("\n") + 1,
                    "message": "Potential SQL injection vulnerability — use parameterised queries",
                })

        return findings

    # ------------------------------------------------------------------
    # XSS detection
    # ------------------------------------------------------------------

    def _scan_xss(self, path: str) -> List[Dict]:
        findings: List[Dict] = []

        for filepath, content in self._iter_files(path, (".js", ".jsx", ".tsx", ".ts", ".html")):
            for match in _XSS_PATTERNS.finditer(content):
                findings.append({
                    "severity": "high",
                    "type": "xss",
                    "file": filepath,
                    "line": content[:match.start()].count("\n") + 1,
                    "message": "Potential XSS vulnerability — avoid raw HTML injection",
                })

        return findings

    # ------------------------------------------------------------------
    # bandit tool integration
    # ------------------------------------------------------------------

    def _run_bandit(self, path: str) -> List[Dict]:
        """Run bandit on the project path and parse JSON output."""
        findings: List[Dict] = []
        try:
            result = subprocess.run(
                ["bandit", "-r", path, "-f", "json", "-q",
                 "--exclude", ".git,__pycache__,venv,.venv,node_modules"],
                capture_output=True, text=True, timeout=60
            )
            data = json.loads(result.stdout or "{}") if result.stdout.strip() else {}
            for issue in data.get("results", []):
                sev = issue.get("issue_severity", "LOW").lower()
                sev_map = {"high": "high", "medium": "warning", "low": "info"}
                findings.append({
                    "severity": sev_map.get(sev, "info"),
                    "type": "bandit_" + issue.get("test_id", "unknown").lower(),
                    "file": issue.get("filename", path),
                    "line": issue.get("line_number", 0),
                    "message": f"[bandit] {issue.get('issue_text', '')}",
                })
            logger.info(f"[X2] bandit: {len(findings)} issues")
        except FileNotFoundError:
            logger.debug("[X2] bandit not installed — skipping")
        except Exception as e:
            logger.warning(f"[X2] bandit failed (non-fatal): {e}")
        return findings

    def _run_ruff_security(self, path: str) -> List[Dict]:
        """Run ruff with security-related rules (S prefix = flake8-bandit)."""
        findings: List[Dict] = []
        try:
            result = subprocess.run(
                ["ruff", "check", path, "--select", "S", "--output-format", "json",
                 "--exclude", "__pycache__,venv,.venv,node_modules"],
                capture_output=True, text=True, timeout=30
            )
            data = json.loads(result.stdout or "[]") if result.stdout.strip() else []
            for issue in data:
                findings.append({
                    "severity": "warning",
                    "type": f"ruff_{issue.get('code', 'S000').lower()}",
                    "file": issue.get("filename", path),
                    "line": issue.get("location", {}).get("row", 0),
                    "message": f"[ruff] {issue.get('message', '')}",
                })
            logger.info(f"[X2] ruff security: {len(findings)} issues")
        except FileNotFoundError:
            logger.debug("[X2] ruff not installed — skipping")
        except Exception as e:
            logger.warning(f"[X2] ruff failed (non-fatal): {e}")
        return findings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _shannon_entropy(data: str) -> float:
        """Calculate Shannon entropy (bits per character)."""
        if not data:
            return 0.0
        length = len(data)
        freq: Dict[str, int] = {}
        for ch in data:
            freq[ch] = freq.get(ch, 0) + 1
        return -sum(
            (count / length) * math.log2(count / length)
            for count in freq.values()
        )

    @staticmethod
    def _iter_files(path: str, extensions: tuple):
        """Yield (filepath, content) for every file matching *extensions*."""
        skip_dirs = {".git", "__pycache__", "venv", ".venv", "node_modules"}
        for root, dirs, files in os.walk(path):
            # Prune in-place to avoid descending into ignored dirs
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                if file.endswith(extensions):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            yield filepath, f.read()
                    except OSError:
                        continue

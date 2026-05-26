import logging
import math
import os
import re
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
        findings: List[Dict] = []

        # 1. Secret scanning
        findings.extend(self._scan_secrets(project_path))

        # 2. SQL injection
        findings.extend(self._scan_sql_injection(project_path))

        # 3. XSS
        findings.extend(self._scan_xss(project_path))

        passed = len([f for f in findings if f["severity"] == "critical"]) == 0

        logger.info(f"[X2] Security scan: {len(findings)} findings, passed={passed}")

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

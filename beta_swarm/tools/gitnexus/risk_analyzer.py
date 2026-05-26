"""GitNexus Risk Analyzer — detects code smells, security risks, and debt."""

import re
import math
import logging
from typing import Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class RiskAnalyzer:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.risks: List[Dict[str, Any]] = []

    def analyze(self) -> Dict[str, Any]:
        """Runs a comprehensive risk analysis on the repository."""
        logger.info(f"Analyzing risks in: {self.repo_path}")
        self.risks = []
        self._scan_secrets()
        self._scan_dependencies()
        self._scan_complexity()
        self._scan_test_coverage()
        
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for risk in self.risks:
            severity_counts[risk["severity"]] += 1
            
        return {
            "status": "complete",
            "total_risks": len(self.risks),
            "severity_breakdown": severity_counts,
            "risks": self.risks
        }

    def _calculate_entropy(self, data: str) -> float:
        """Calculates Shannon entropy to detect random-looking strings (likely keys)."""
        if not data: return 0
        entropy = 0
        for x in range(256):
            p_x = data.count(chr(x)) / len(data)
            if p_x > 0:
                entropy += - p_x * math.log2(p_x)
        return entropy

    def _scan_secrets(self):
        """Combines regex patterns with entropy analysis for robust secret detection."""
        patterns = [
            (r'(?i)(api[_-]?key|secret[_-]?key|password|token|access[_-]?token)\s*[:=]\s*["\']([^"\']{8,})["\']', "Hardcoded secret/token detected", "critical"),
            (r'(?i)(aws_access_key_id|aws_secret_access_key)\s*[:=]\s*["\']([^"\']+)["\']', "AWS credentials exposed", "critical"),
        ]
        
        for file_path in self.repo_path.rglob("*"):
            if file_path.is_dir() or ".git" in file_path.parts or "node_modules" in file_path.parts:
                continue
            if file_path.suffix in [".py", ".js", ".ts", ".env", ".yaml", ".yml", ".json", ".md"]:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    
                    # Regex Scan
                    for pattern, message, severity in patterns:
                        for match in re.finditer(pattern, content):
                            self.risks.append({
                                "file": str(file_path.relative_to(self.repo_path)),
                                "line": content[:match.start()].count("\n") + 1,
                                "message": message,
                                "severity": severity,
                                "category": "security"
                            })
                    
                    # Entropy Scan for long strings
                    words = re.findall(r'["\']([a-zA-Z0-9\/\+=]{20,})["\']', content)
                    for word in words:
                        if self._calculate_entropy(word) > 4.5:
                            self.risks.append({
                                "file": str(file_path.relative_to(self.repo_path)),
                                "message": f"High-entropy string detected (Potential Key): {word[:8]}...",
                                "severity": "high",
                                "category": "security"
                            })
                except Exception:
                    pass

    def _scan_dependencies(self):
        """Checks for unpinned or potentially vulnerable dependency patterns."""
        req_file = self.repo_path / "requirements.txt"
        if req_file.exists():
            with open(req_file, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    if "==" not in line and "@" not in line:
                        self.risks.append({
                            "file": "requirements.txt",
                            "line": i,
                            "message": f"Unpinned dependency: {line}",
                            "severity": "medium",
                            "category": "dependency"
                        })

    def _scan_complexity(self):
        """Identifies oversized functions and long lines."""
        for py_file in self.repo_path.rglob("*.py"):
            if "node_modules" in py_file.parts or ".venv" in py_file.parts: continue
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                # Check for long files
                if len(lines) > 500:
                    self.risks.append({
                        "file": str(py_file.relative_to(self.repo_path)),
                        "message": f"File is too long ({len(lines)} lines)",
                        "severity": "low",
                        "category": "debt"
                    })
                
                # Check for long lines
                for i, line in enumerate(lines, 1):
                    if len(line) > 120:
                        self.risks.append({
                            "file": str(py_file.relative_to(self.repo_path)),
                            "line": i,
                            "message": "Line exceeds 120 characters",
                            "severity": "low",
                            "category": "style"
                        })
            except Exception:
                pass

    def _scan_test_coverage(self):
        """Detects if test suites exist."""
        test_patterns = ["test/", "tests/", "*_test.py", "test_*.py"]
        found_tests = False
        for pattern in test_patterns:
            if list(self.repo_path.glob(pattern)):
                found_tests = True
                break
        
        if not found_tests:
            self.risks.append({
                "file": "ROOT",
                "message": "No test directory or test files detected",
                "severity": "high",
                "category": "testing"
            })

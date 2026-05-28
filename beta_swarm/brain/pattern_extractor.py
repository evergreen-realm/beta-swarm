"""
PatternExtractor - Deep pattern detection for Phase 2 Self-Growing Brain.
Scans project files recursively and extracts technology stack, architectural patterns,
database schemas, and common code idioms using regex keyword boundary heuristics.
"""

import os
import re
import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class PatternExtractor:
    """
    Analyzes project source code and configuration files recursively to extract
    tech stack metadata, architecture blueprints, database choices, and code patterns.
    """
    def __init__(self, project_path: str):
        self.project_path = project_path

    def extract(self) -> Dict[str, List[str]]:
        """
        Recursively scans directory tree files and compiles structural design patterns.
        """
        patterns: Dict[str, List[str]] = {
            "tech_stack": [],
            "architecture": [],
            "db_schema": [],
            "code_patterns": []
        }

        # Check if project_path is accessible
        if not self.project_path or not os.path.exists(self.project_path) or not os.path.isdir(self.project_path):
            logger.warning(f"Project path is invalid or inaccessible: {self.project_path}")
            return patterns

        # Compile word-boundary regexes to prevent partial matching (e.g. 'react' inside 'reaction')
        tech_rules = {
            "FastAPI": re.compile(r"\bFastAPI\b"),
            "React": re.compile(r"\bReact\b", re.IGNORECASE),
            "PostgreSQL": re.compile(r"\b(PostgreSQL|postgres)\b", re.IGNORECASE),
            "Flask": re.compile(r"\bFlask\b"),
            "Django": re.compile(r"\bDjango\b"),
            "Next.js": re.compile(r"\b(Nextjs|Next\.js)\b", re.IGNORECASE),
            "Vue": re.compile(r"\bVue\b")
        }

        db_rules = {
            "SQLAlchemy": re.compile(r"\b(SQLAlchemy|sqlalchemy)\b", re.IGNORECASE),
            "Prisma": re.compile(r"\bPrisma\b", re.IGNORECASE),
            "Pydantic": re.compile(r"\bPydantic\b", re.IGNORECASE),
            "Mongo": re.compile(r"\b(MongoDB|pymongo|mongo)\b", re.IGNORECASE),
            "Redis": re.compile(r"\bRedis\b", re.IGNORECASE)
        }

        code_rules = {
            "async": re.compile(r"\basync\s+def\b"),
            "dependency_injection": re.compile(r"\b(Depends|DependencyInjection|inject)\b", re.IGNORECASE),
            "decorator": re.compile(r"@\w+"),
            "dataclass": re.compile(r"\bdataclass\b")
        }

        arch_rules = {
            "microservices": re.compile(r"\bmicroservices?\b", re.IGNORECASE),
            "dockerized": re.compile(r"\b(docker|docker-compose|dockerfile)\b", re.IGNORECASE)
        }

        # Traverse the directories
        for root, _, files in os.walk(self.project_path):
            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()

                # Process specific file extensions
                if ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".yml", ".md"]:
                    try:
                        # Scan configuration or compose files directly by name
                        if file in ["docker-compose.yml", "docker-compose.yaml", "Dockerfile"]:
                            if "dockerized" not in patterns["architecture"]:
                                patterns["architecture"].append("dockerized")

                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()

                        # Apply Tech rules
                        for name, rx in tech_rules.items():
                            if name not in patterns["tech_stack"] and rx.search(content):
                                patterns["tech_stack"].append(name)

                        # Apply Database rules
                        for name, rx in db_rules.items():
                            if name not in patterns["db_schema"] and rx.search(content):
                                patterns["db_schema"].append(name)

                        # Apply Code pattern rules
                        for name, rx in code_rules.items():
                            if name not in patterns["code_patterns"] and rx.search(content):
                                patterns["code_patterns"].append(name)

                        # Apply Architecture rules
                        for name, rx in arch_rules.items():
                            if name not in patterns["architecture"] and rx.search(content):
                                patterns["architecture"].append(name)

                    except Exception as e:
                        logger.debug(f"Failed parsing file {file_path}: {e}")

        return patterns

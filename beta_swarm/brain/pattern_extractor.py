import os
import json
import re
from typing import Dict, List

class PatternExtractor:
    def __init__(self, project_path: str):
        self.project_path = project_path

    def extract(self) -> Dict[str, List[str]]:
        patterns = {
            "tech_stack": [],
            "architecture": [],
            "db_schema": [],
            "code_patterns": []
        }
        if not os.path.exists(self.project_path):
            return patterns

        for root, _, files in os.walk(self.project_path):
            for f in files:
                file_path = os.path.join(root, f)
                if f.endswith(".py"):
                    try:
                        with open(file_path, "r", encoding="utf-8") as code:
                            content = code.read()
                            if "FastAPI" in content and "FastAPI" not in patterns["tech_stack"]:
                                patterns["tech_stack"].append("FastAPI")
                            if ("SQLAlchemy" in content or "sqlalchemy" in content) and "SQLAlchemy" not in patterns["db_schema"]:
                                patterns["db_schema"].append("SQLAlchemy")
                            if "async def" in content and "async" not in patterns["code_patterns"]:
                                patterns["code_patterns"].append("async")
                    except Exception:
                        pass
                elif f.endswith(".json"):
                    try:
                        with open(file_path, "r", encoding="utf-8") as cfg:
                            data = json.load(cfg)
                            if "docker" in str(data).lower() and "dockerized" not in patterns["architecture"]:
                                patterns["architecture"].append("dockerized")
                    except Exception:
                        pass
                elif f.endswith(".md") and "prd" in f.lower():
                    try:
                        with open(file_path, "r", encoding="utf-8") as doc:
                            content = doc.read()
                            if "microservices" in content.lower() and "microservices" not in patterns["architecture"]:
                                patterns["architecture"].append("microservices")
                    except Exception:
                        pass
        return patterns

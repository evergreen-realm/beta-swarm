from beta_swarm.agents.base import BaseAgent
from typing import Dict, Any
import os

class S11DocumentationAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("s11_docs", "Documentation Agent", "Stage 11: Docs", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_path = task.get("project_path", "./projects/new_project")
        prd = task.get("prd", {})

        # IMPROVEMENT: Ensure path exists
        os.makedirs(project_path, exist_ok=True)

        self._generate_mkdocs_config(project_path)
        self._generate_index_md(project_path, prd)

        if self.brain:
            self.brain.store_fact(self.agent_id, f"Docs generated for {project_path}", "documentation")

        return {"status": "complete", "path": project_path, "next_stage": "s12_maintenance"}

    def _generate_mkdocs_config(self, path: str):
        config = '''site_name: Beta Swarm Project
theme: material
nav:
  - Home: index.md
  - API: api.md
  - Architecture: architecture.md
'''
        with open(os.path.join(path, "mkdocs.yml"), "w", encoding="utf-8") as f:
            f.write(config)

    def _generate_index_md(self, path: str, prd: Dict):
        title = prd.get("metadata", {}).get("title", "Project")
        content = f'''# {title}

## Overview

{prd.get("overview", "No overview provided.")}

## Quick Start

```bash
docker-compose up -d
```

## Monitoring

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
'''
        # mkdocs expects index.md to be inside a 'docs' directory by default
        docs_dir = os.path.join(path, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        with open(os.path.join(docs_dir, "index.md"), "w", encoding="utf-8") as f:
            f.write(content)

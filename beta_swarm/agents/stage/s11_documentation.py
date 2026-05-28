"""
S11 — Documentation Agent (full rewrite).
Generates README.md, API.md, ARCHITECTURE.md, CONTRIBUTING.md via LLM with guaranteed fallbacks.
Syncs to SQLiteBrain and Obsidian vault.
"""
from beta_swarm.agents.base import BaseAgent
import json, os, re, logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class S11DocumentationAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("s11_docs", "Documentation Agent", "Stage 11: Documentation", brain)

    def _get_default_next_stage(self):
        return "s12_monitoring"

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_id   = task.get("project_id", "default")
        project_path = task.get("project_path", f"./projects/{project_id}")
        s3_out       = task.get("s3_prd", {})
        prd          = s3_out.get("prd") or task.get("prd") or {}
        s4_out       = task.get("s4_architecture", {})
        architecture = s4_out.get("architecture") or task.get("architecture", {})
        preview_url  = task.get("preview_url", "http://localhost:8000")

        title      = prd.get("metadata", {}).get("title", "App")
        overview   = prd.get("overview", "")
        tech_stack = prd.get("tech_stack_recommendation", {})
        api_specs  = prd.get("api_specifications", architecture.get("api_contracts", []))

        self._log_handover(f"S11 started. title={title}")

        docs_dir = os.path.join(project_path, "docs")
        os.makedirs(docs_dir, exist_ok=True)

        files_written: List[str] = []

        def write(rel: str, content: str):
            p = os.path.join(project_path, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            files_written.append(rel)

        # ── README.md ─────────────────────────────────────────────────── #
        readme_prompt = f"""Write a comprehensive README.md for "{title}".
Project overview: {overview[:500]}
Tech stack: {json.dumps(tech_stack)}
Preview URL: {preview_url}
Include: title, badges, overview, features, tech stack, quickstart, API usage, docker deploy, contributing, license."""
        readme = self._call_llm(readme_prompt, task_type="s11_docs")
        m = re.search(r'```(?:markdown|md)?\s*\n?(.*?)\n?```', readme, re.DOTALL)
        if m: readme = m.group(1).strip()
        if len(readme) < 100: readme = self._fallback_readme(title, overview, tech_stack, preview_url)
        write("README.md", readme)

        # ── API.md ────────────────────────────────────────────────────── #
        api_prompt = f"""Write a detailed API.md for "{title}".
Base URL: {preview_url}
Endpoints: {json.dumps(api_specs[:8], indent=2)}
Include for each endpoint: method, path, description, request body, response, example curl."""
        api_doc = self._call_llm(api_prompt, task_type="s11_docs")
        m = re.search(r'```(?:markdown|md)?\s*\n?(.*?)\n?```', api_doc, re.DOTALL)
        if m: api_doc = m.group(1).strip()
        if len(api_doc) < 100: api_doc = self._fallback_api_doc(title, api_specs, preview_url)
        write("docs/API.md", api_doc)

        # ── ARCHITECTURE.md ───────────────────────────────────────────── #
        arch_prompt = f"""Write ARCHITECTURE.md for "{title}".
Components: {json.dumps(architecture.get('components', []), indent=2)[:1000]}
Data flow: {architecture.get('data_flow', 'Client -> API -> Database')}
Include: system diagram (ASCII), component descriptions, data flow, security."""
        arch_doc = self._call_llm(arch_prompt, task_type="s11_docs")
        m = re.search(r'```(?:markdown|md)?\s*\n?(.*?)\n?```', arch_doc, re.DOTALL)
        if m: arch_doc = m.group(1).strip()
        if len(arch_doc) < 100: arch_doc = self._fallback_arch_doc(title, architecture)
        write("docs/ARCHITECTURE.md", arch_doc)

        # ── CONTRIBUTING.md ───────────────────────────────────────────── #
        write("docs/CONTRIBUTING.md", self._contributing(title))

        # ── Sync to SQLiteBrain ───────────────────────────────────────── #
        try:
            from beta_swarm.brain.sqlite_brain import SQLiteBrain
            db = SQLiteBrain.get_instance()
            db.register_agent("s11_docs", "Documentation Agent", "Stage 11")
            db.store_artifact(agent_id="s11_docs", project=title, stage="S11",
                              data=f"Docs: {', '.join(files_written)}")
        except Exception as e:
            logger.warning(f"[S11] SQLiteBrain sync (non-fatal): {e}")

        # ── Sync to Obsidian ──────────────────────────────────────────── #
        try:
            from beta_swarm.brain.obsidian_sync import obsidian_sync
            obsidian_sync.sync_to_daily_note(
                f"S11 documented {title}: README, API.md, ARCHITECTURE.md",
                agent_id="s11_docs"
            )
        except Exception as e:
            logger.warning(f"[S11] Obsidian sync (non-fatal): {e}")

        artifact = {"doc_files": files_written}
        artifact_path = f"./projects/{project_id}/s11_docs_output.json"
        os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)

        self._log_handover(f"S11 completed. {len(files_written)} doc files.")

        return {
            "status": "complete",
            "doc_files": files_written,
            "artifact": artifact,
            "artifact_path": artifact_path,
            "next_stage": task.get("next_stage") or self._get_default_next_stage()
        }

    # ── Fallbacks ─────────────────────────────────────────────────────── #
    def _fallback_readme(self, title, overview, tech_stack, preview_url) -> str:
        fe  = tech_stack.get("frontend", "React") if isinstance(tech_stack, dict) else "React"
        be  = tech_stack.get("backend",  "FastAPI") if isinstance(tech_stack, dict) else "FastAPI"
        db  = tech_stack.get("database", "SQLite") if isinstance(tech_stack, dict) else "SQLite"
        dep = tech_stack.get("deployment", "Docker") if isinstance(tech_stack, dict) else "Docker"
        return f"""# {title}

> Autonomously generated by **Beta Swarm** — the self-growing AI development platform.

## Overview
{overview or f'A modern web application: {title}'}

## Tech Stack
| Layer      | Technology |
|------------|------------|
| Frontend   | {fe}       |
| Backend    | {be}       |
| Database   | {db}       |
| Deployment | {dep}      |

## Quick Start
```bash
git clone <repo>
cd {title.lower().replace(' ', '-')}

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload --port 8000
```

## Docker
```bash
docker-compose up --build
```

## API
See [docs/API.md](docs/API.md) | Base URL: `{preview_url}`

## Architecture
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## License
MIT
"""

    def _fallback_api_doc(self, title, api_specs, preview_url) -> str:
        lines = [f"# {title} — API Reference\n\nBase URL: `{preview_url}`\n\n"]
        for ep in api_specs[:8]:
            method = ep.get("method", "GET")
            path   = ep.get("endpoint", "/api/v1/items/")
            desc   = ep.get("description", "")
            lines.append(f"## `{method} {path}`\n{desc}\n\n```bash\ncurl -X {method} {preview_url}{path}\n```\n")
        return "".join(lines)

    def _fallback_arch_doc(self, title, architecture) -> str:
        components = architecture.get("components", [])
        comp_lines = "\n".join([f"- **{c.get('name', c)}** ({c.get('tech', '')})" for c in components])
        comp_lines_val = comp_lines or "- Backend: FastAPI\n- Database: SQLite\n- Frontend: React"
        return f"""# {title} — Architecture

## System Overview
```
Browser → Nginx (port 80) → FastAPI (port 8000) → SQLite/Postgres
```

## Components
{comp_lines_val}

## Data Flow
{architecture.get('data_flow', 'Client → API Gateway → Business Logic → Database')}

## Security
- JWT authentication
- HTTPS via reverse proxy
- Input validation on all endpoints
"""

    def _contributing(self, title) -> str:
        return f"""# Contributing to {title}

## Development Setup
1. Fork and clone the repo
2. `pip install -r requirements.txt`
3. `python -m pytest tests/ -v`

## Pull Request Process
1. Create a feature branch: `git checkout -b feature/my-feature`
2. Commit with clear messages
3. Run tests: `make test`
4. Open a PR against `main`

## Code Style
- Python: PEP 8, max line length 120
- JavaScript: ESLint config included
"""

from beta_swarm.agents.base import BaseAgent
import json, re, os
from typing import Dict, Any, List
from datetime import datetime

class S3PRDAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("s3_prd", "PRD Agent", "Stage 3: Product Requirements", brain)

    def _get_default_next_stage(self):
        return "s4_architecture"

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_id = task.get("project_id", "default")
        s1_out = task.get("s1_ideation", {})
        concept = s1_out.get("concept") or task.get("concept") or {}
        s2_out = task.get("s2_research", {})
        research = s2_out.get("research_summary") or task.get("research_summary", "")

        self._log_handover(f"S3 started. Concept='{concept.get('title', 'N/A')}'")

        prompt = f"""You are the PRD Agent. Generate a comprehensive Product Requirements Document.

CONCEPT:
{json.dumps(concept, indent=2)}

RESEARCH SUMMARY:
{research[:2000]}

Return ONLY a JSON object with these fields:
{{
  "metadata": {{"title": "", "version": "1.0", "date": "", "author": "Beta Swarm"}},
  "overview": "Project overview paragraph",
  "objectives": ["obj1", "obj2"],
  "user_stories": [{{"as_a": "user", "i_want": "feature", "so_that": "goal"}}],
  "functional_requirements": ["FR-1: ...", "FR-2: ..."],
  "non_functional_requirements": ["NFR-1: ...", "NFR-2: ..."],
  "tech_stack_recommendation": {{"frontend": "React", "backend": "FastAPI", "database": "PostgreSQL", "deployment": "Docker"}},
  "api_specifications": [{{"endpoint": "/api/v1/items", "method": "GET", "description": "List items"}}],
  "ui_ux_requirements": {{"design_system": "dark mode glassmorphism", "components": ["App", "Login", "Dashboard", "ItemList"]}},
  "security_requirements": ["SEC-1: JWT auth", "SEC-2: Input validation"],
  "milestones": [{{"name": "M1", "duration": "2 days"}}],
  "blueprint": {{"data_schema": "schema details", "api_spec": "api details", "components": "component details"}}
}}"""

        llm_output = self._call_llm(prompt, task_type="s3_prd")
        parsed = self._safe_parse_json(llm_output)

        if not parsed or not parsed.get("metadata"):
            parsed = self._generate_fallback_prd(concept, research)

        # Ensure metadata has date
        if "metadata" in parsed:
            parsed["metadata"]["date"] = datetime.now().isoformat()

        os.makedirs(f"./projects/{project_id}", exist_ok=True)
        artifact_path = f"./projects/{project_id}/s3_prd_output.json"
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2)

        if self.brain:
            try:
                self.brain.store_fact(self.agent_id, f"PRD for {concept.get('title')}", "prd")
            except Exception:
                pass

        self._log_handover(f"S3 completed. PRD saved: {artifact_path}")

        return {
            "status": "complete",
            "prd": parsed,
            "artifact": parsed,
            "artifact_path": artifact_path,
            "next_stage": task.get("next_stage") or self._get_default_next_stage()
        }

    def _generate_fallback_prd(self, concept: dict, research: str) -> dict:
        title = concept.get("title", "Untitled Project")
        features = concept.get("key_features", [])
        return {
            "metadata": {"title": title, "version": "1.0", "date": datetime.now().isoformat(), "author": "Beta Swarm"},
            "overview": concept.get("problem_statement", ""),
            "objectives": [f"Implement {f}" for f in features[:3]],
            "user_stories": [{"as_a": u, "i_want": features[0] if features else "core feature", "so_that": "I achieve my goal"} for u in concept.get("target_users", ["user"])[:3]],
            "functional_requirements": [f"FR-{i+1}: {f}" for i, f in enumerate(features)],
            "non_functional_requirements": ["NFR-1: <200ms response time", "NFR-2: 99.9% uptime", "NFR-3: Secure by default"],
            "tech_stack_recommendation": {"frontend": "React", "backend": "FastAPI", "database": "SQLite", "deployment": "Docker"},
            "api_specifications": [{"endpoint": "/api/v1/items", "method": "GET", "description": "List items"}, {"endpoint": "/api/v1/items", "method": "POST", "description": "Create item"}],
            "ui_ux_requirements": {"design_system": "dark mode glassmorphism", "components": ["App", "Login", "Dashboard", "ItemList"]},
            "security_requirements": ["SEC-1: JWT authentication", "SEC-2: Input validation on all endpoints"],
            "milestones": [{"name": "M1: Setup", "duration": "1 day"}, {"name": "M2: Core", "duration": "3 days"}, {"name": "M3: UI", "duration": "2 days"}],
            "blueprint": {"data_schema": str(features), "api_spec": "/api/v1/items CRUD", "components": "App, Dashboard, ItemList"}
        }

    def _safe_parse_json(self, text: str) -> dict:
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except Exception:
                pass
        m2 = re.search(r'\{.*\}', text, re.DOTALL)
        if m2:
            try:
                return json.loads(m2.group(0))
            except Exception:
                pass
        return {}

from beta_swarm.agents.base import BaseAgent
import json, re, os
from typing import Dict, Any

class S4ArchitectureAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("s4_architecture", "Architecture Agent", "Stage 4: System Design", brain)

    def _get_default_next_stage(self):
        return "s5_backend"

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_id = task.get("project_id", "default")
        s3_out = task.get("s3_prd", {})
        prd = s3_out.get("prd") or task.get("prd") or {}
        domain = task.get("business_domain", "general")

        self._log_handover(f"S4 started. Project={project_id}")

        prompt = f"""You are the Architecture Agent. Design a complete system architecture.

PRD:
{json.dumps(prd, indent=2)[:3000]}

Domain: {domain}

Return ONLY a JSON object:
{{
  "system_overview": "Description of the overall system",
  "components": [
    {{"name": "API Gateway", "type": "service", "tech": "FastAPI", "port": 8000}},
    {{"name": "Database", "type": "storage", "tech": "PostgreSQL", "port": 5432}},
    {{"name": "Frontend", "type": "web", "tech": "React", "port": 3000}}
  ],
  "data_flow": "Client -> API Gateway -> Services -> Database",
  "api_contracts": [
    {{"endpoint": "/api/v1/items", "method": "GET", "auth": "JWT", "returns": "list"}},
    {{"endpoint": "/api/v1/items", "method": "POST", "auth": "JWT", "body": "item_data"}}
  ],
  "database_schema": [
    {{"table": "items", "columns": [{{"name": "id", "type": "UUID", "pk": true}}, {{"name": "title", "type": "VARCHAR(255)"}}, {{"name": "user_id", "type": "UUID"}}]}}
  ],
  "infrastructure": {{"containerization": "Docker Compose", "reverse_proxy": "Nginx", "monitoring": "Prometheus"}},
  "security_model": {{"auth": "JWT", "tls": true, "secrets_management": "env vars"}}
}}"""

        llm_output = self._call_llm(prompt, task_type="s4_architecture")
        parsed = self._safe_parse_json(llm_output)

        if not parsed or not parsed.get("components"):
            parsed = {
                "system_overview": f"Microservices architecture for {prd.get('metadata', {}).get('title', 'project')}",
                "components": [
                    {"name": "FastAPI Backend", "type": "service", "tech": "FastAPI/Python", "port": 8000},
                    {"name": "SQLite DB", "type": "storage", "tech": "SQLite", "port": None},
                    {"name": "React Frontend", "type": "web", "tech": "React", "port": 3000}
                ],
                "data_flow": "Browser -> FastAPI -> SQLite",
                "api_contracts": [
                    {"endpoint": "/api/v1/items", "method": "GET", "auth": "JWT", "returns": "list"},
                    {"endpoint": "/api/v1/items", "method": "POST", "auth": "JWT", "body": "item_data"},
                    {"endpoint": "/api/v1/items/{id}", "method": "PUT", "auth": "JWT", "body": "item_data"},
                    {"endpoint": "/api/v1/items/{id}", "method": "DELETE", "auth": "JWT"}
                ],
                "database_schema": [{"table": "items", "columns": [{"name": "id", "type": "UUID"}, {"name": "title", "type": "VARCHAR"}, {"name": "user_id", "type": "UUID"}, {"name": "status", "type": "VARCHAR"}]}],
                "infrastructure": {"containerization": "Docker Compose", "reverse_proxy": "Nginx", "monitoring": "Prometheus"},
                "security_model": {"auth": "JWT", "tls": False, "secrets_management": "env vars"}
            }

        os.makedirs(f"./projects/{project_id}", exist_ok=True)
        artifact_path = f"./projects/{project_id}/s4_architecture_output.json"
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2)

        self._log_handover(f"S4 completed. Architecture saved: {artifact_path}")

        return {
            "status": "complete",
            "architecture": parsed,
            "artifact": parsed,
            "artifact_path": artifact_path,
            "next_stage": task.get("next_stage") or self._get_default_next_stage()
        }

    def _safe_parse_json(self, text: str) -> dict:
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if m:
            try: return json.loads(m.group(1).strip())
            except Exception: pass
        m2 = re.search(r'\{.*\}', text, re.DOTALL)
        if m2:
            try: return json.loads(m2.group(0))
            except Exception: pass
        return {}

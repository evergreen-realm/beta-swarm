from beta_swarm.agents.base import BaseAgent
import json, re, os, logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class S6APIAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("s6_api", "API Integration Agent", "Stage 6: API Integration", brain)

    def _get_default_next_stage(self):
        return "s7_frontend"

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_id = task.get("project_id", "default")
        project_path = task.get("project_path", f"./projects/{project_id}")
        s4_out = task.get("s4_architecture", {})
        architecture = s4_out.get("architecture") or task.get("architecture", {})
        api_contracts = architecture.get("api_contracts", [
            {"endpoint": "/api/v1/items/", "method": "GET"},
            {"endpoint": "/api/v1/items/", "method": "POST"},
        ])

        self._log_handover(f"S6 started. Project={project_id}")

        prompt = f"""You are an expert frontend developer. Generate a JavaScript API client.

API Contracts:
{json.dumps(api_contracts, indent=2)[:2000]}

Generate a complete APIClient.js that:
1. Has a base URL configuration
2. Has methods for each endpoint (getItems, createItem, updateItem, deleteItem, etc.)
3. Uses fetch() with proper headers (Content-Type, Authorization)
4. Handles errors gracefully
5. Returns parsed JSON

Output ONLY the JavaScript code, no markdown."""

        api_client_code = self._call_llm(prompt, task_type="s6_api")

        # Extract code from markdown block if wrapped
        m = re.search(r'```(?:javascript|js)?\s*\n?(.*?)\n?```', api_client_code, re.DOTALL)
        if m:
            api_client_code = m.group(1).strip()

        # Fallback API client
        if len(api_client_code) < 100:
            api_client_code = self._generate_fallback_client(api_contracts)

        # Write APIClient.js
        client_dir = os.path.join(project_path, "frontend", "src")
        os.makedirs(client_dir, exist_ok=True)
        client_path = os.path.join(client_dir, "APIClient.js")
        with open(client_path, "w", encoding="utf-8") as f:
            f.write(api_client_code)

        artifact_path = f"./projects/{project_id}/s6_api_output.json"
        artifact = {"api_client_path": client_path, "api_contracts": api_contracts}
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)

        self._log_handover(f"S6 completed. APIClient.js written: {client_path}")

        return {
            "status": "complete",
            "api_client_code": api_client_code,
            "api_client_path": client_path,
            "api_contracts": api_contracts,
            "artifact": artifact,
            "artifact_path": artifact_path,
            "next_stage": task.get("next_stage") or self._get_default_next_stage()
        }

    def _generate_fallback_client(self, api_contracts: list) -> str:
        methods = ""
        for c in api_contracts[:8]:
            ep = c.get("endpoint", "/api/v1/items/")
            method = c.get("method", "GET").upper()
            fn_name = method.lower() + "_" + re.sub(r'[^a-zA-Z0-9]', '_', ep).strip('_').lower()
            if method in ("GET", "DELETE"):
                methods += f"""
  async {fn_name}(id = null) {{
    const url = id ? `${{this.baseUrl}}{ep}${{id}}` : `${{this.baseUrl}}{ep}`;
    const res = await fetch(url, {{ headers: this.headers }});
    if (!res.ok) throw new Error(`HTTP ${{res.status}}`);
    return res.json();
  }}
"""
            else:
                methods += f"""
  async {fn_name}(data) {{
    const res = await fetch(`${{this.baseUrl}}{ep}`, {{
      method: '{method}',
      headers: this.headers,
      body: JSON.stringify(data)
    }});
    if (!res.ok) throw new Error(`HTTP ${{res.status}}`);
    return res.json();
  }}
"""
        return f"""// Auto-generated APIClient by Beta Swarm S6
class APIClient {{
  constructor(baseUrl = 'http://localhost:8000', token = null) {{
    this.baseUrl = baseUrl;
    this.headers = {{'Content-Type': 'application/json'}};
    if (token) this.headers['Authorization'] = `Bearer ${{token}}`;
  }}

  setToken(token) {{
    this.headers['Authorization'] = `Bearer ${{token}}`;
  }}

  async getItems() {{
    const res = await fetch(`${{this.baseUrl}}/api/v1/items/`, {{ headers: this.headers }});
    if (!res.ok) throw new Error(`HTTP ${{res.status}}`);
    return res.json();
  }}

  async createItem(data) {{
    const res = await fetch(`${{this.baseUrl}}/api/v1/items/`, {{
      method: 'POST', headers: this.headers, body: JSON.stringify(data)
    }});
    if (!res.ok) throw new Error(`HTTP ${{res.status}}`);
    return res.json();
  }}

  async getItem(id) {{
    const res = await fetch(`${{this.baseUrl}}/api/v1/items/${{id}}`, {{ headers: this.headers }});
    if (!res.ok) throw new Error(`HTTP ${{res.status}}`);
    return res.json();
  }}

  async updateItem(id, data) {{
    const res = await fetch(`${{this.baseUrl}}/api/v1/items/${{id}}`, {{
      method: 'PUT', headers: this.headers, body: JSON.stringify(data)
    }});
    if (!res.ok) throw new Error(`HTTP ${{res.status}}`);
    return res.json();
  }}

  async deleteItem(id) {{
    const res = await fetch(`${{this.baseUrl}}/api/v1/items/${{id}}`, {{
      method: 'DELETE', headers: this.headers
    }});
    if (!res.ok) throw new Error(`HTTP ${{res.status}}`);
    return res.json();
  }}

  async healthCheck() {{
    const res = await fetch(`${{this.baseUrl}}/health`, {{ headers: this.headers }});
    return res.json();
  }}
{methods}}}

export default APIClient;
"""

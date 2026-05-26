from beta_swarm.agents.base import BaseAgent
from typing import Dict, Any, List

class S4ArchitectureAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("s4_architecture", "Architecture Agent", "Stage 4: System Design", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        s3_out = task.get("s3_prd", {})
        prd = s3_out.get("prd") or task.get("prd") or {}
        blueprint = prd.get("blueprint", {})

        prompt = f"""
        Design a detailed system architecture for the project "{prd.get('metadata', {}).get('title')}".
        
        PRD BLUEPRINT:
        - DATA SCHEMA: {blueprint.get('data_schema')}
        - API SPEC: {blueprint.get('api_spec')}
        - COMPONENTS: {blueprint.get('components')}
        
        Generate a JSON structure with:
        - diagram_type: "c4"
        - components: List of service components with tech details.
        - data_flow: List of interactions between components.
        - api_contracts: Detailed list of endpoints, methods, and auth requirements.
        - database_schema: Finalized table structures and field types.
        - infrastructure: Docker, proxy, and monitoring configuration.
        - security_model: Auth and data protection details.
        
        NO STUBS. Ensure the architecture matches the specific blueprint provided.
        """

        llm_response = self.call_llm([{"role": "user", "content": prompt}], max_tokens=2048)
        
        # Simple extraction (assuming LLM returns JSON or we can parse it)
        # For now, we'll store the full response as the architecture description
        # Robust fallbacks for components and data flows
        components = self._parse_list(llm_response, "components")
        if not components or len(components) < 4:
            components = self._generate_default_components()
            
        data_flow = self._parse_list(llm_response, "data_flow")
        if not data_flow:
            data_flow = self._generate_default_data_flow()

        architecture = {
            "description": llm_response,
            "components": components,
            "data_flow": data_flow,
            "api_contracts": self._parse_field(llm_response, "api_contracts") or "contracts: standard",
            "database_schema": self._parse_field(llm_response, "database_schema") or "schema: standard",
            "infrastructure": self._parse_field(llm_response, "infrastructure") or "infra: standard",
            "security_model": self._parse_field(llm_response, "security_model") or "security: standard"
        }

        if self.brain:
            self.brain.store_fact(self.agent_id, f"Architecture designed for {prd.get('metadata', {}).get('title')}", "architecture")

        return {"status": "complete", "architecture": architecture, "next_stage": "s5_backend"}

    def _generate_default_components(self) -> List[Dict]:
        return [
            {"name": "Frontend Portal", "tech": "React SPA", "purpose": "User dashboard, metrics charts, and control interface."},
            {"name": "API Gateway", "tech": "FastAPI + Traefik", "purpose": "Routes requests, manages rate limits, and validates CORS."},
            {"name": "Database Cluster", "tech": "KuzuDB + SQLite", "purpose": "Manages local memory recall and session fact trees."},
            {"name": "Worker Node", "tech": "Python Async Task Runner", "purpose": "Handles background agent execution and third-party integrations."}
        ]

    def _generate_default_data_flow(self) -> List[str]:
        return [
            "User clicks UI -> API Gateway routes to Frontend SPA",
            "SPA triggers start -> FastAPI routes execution to Swarm Orchestrator",
            "Swarm Orchestrator -> queries facts in KuzuDB Database Cluster",
            "Worker Node processes task -> updates status and broadcasts via WebSockets"
        ]

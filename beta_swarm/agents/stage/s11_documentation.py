import logging
import os
from typing import Dict, Any
from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class S11DocumentationAgent(BaseAgent):
    """
    S11: Documentation Agent
    Generates all project documentation, including README, API docs, and architecture docs.
    """
    def __init__(self, brain=None):
        super().__init__("s11_docs", "Documentation Agent", "Stage 11: Documentation", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        s3_out = task.get("s3_prd", {})
        prd = s3_out.get("prd") or task.get("prd") or {}
        
        project_path = task.get("project_path", "./projects/new_project")
        
        prompt = f"""
        Generate comprehensive documentation for the project "{prd.get('metadata', {}).get('title')}".
        
        PRD SUMMARY:
        {prd.get('full_content', '')[:1000]}
        
        REQUIREMENTS:
        - Generate a README.md with project overview, setup instructions, and features.
        - Generate an API.md detailing all endpoints, parameters, and examples.
        - Generate an ARCHITECTURE.md explaining the system design, data flow, and components.
        - Use clear Markdown formatting.
        """
        
        docs_path = os.path.join(project_path, "docs")
        os.makedirs(docs_path, exist_ok=True)
        
        generated_files = self.generate_codebase(prompt, docs_path)
        
        logger.info(f"[S11] Documentation synthesized: {generated_files}")
        
        return {
            "status": "complete",
            "path": docs_path,
            "generated_files": generated_files,
            "next_stage": "s12_maintenance"
        }

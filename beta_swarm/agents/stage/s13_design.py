import logging
import os
from typing import Dict, Any
from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class S13DesignAgent(BaseAgent):
    """
    S13: Design Agent
    Generates presentation materials and infographics for the project.
    """
    def __init__(self, brain=None):
        super().__init__("s13_design", "Design Agent", "Stage 13: Visual Design", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        s3_out = task.get("s3_prd", {})
        prd = s3_out.get("prd") or task.get("prd") or {}
        
        project_path = task.get("project_path", "./projects/new_project")
        
        prompt = f"""
        Generate project presentation and design assets for "{prd.get('metadata', {}).get('title')}".
        
        REQUIREMENTS:
        - Generate a PRESENTATION.md outline for a stakeholder demo.
        - Generate a BRANDING.md with color palettes, typography, and logo concepts.
        - Generate a FEATURE_MAP.md visualizing the project's core value proposition.
        """
        
        design_path = os.path.join(project_path, "design")
        os.makedirs(design_path, exist_ok=True)
        
        generated_files = self.generate_codebase(prompt, design_path)
        
        logger.info(f"[S13] Design assets synthesized: {generated_files}")
        
        return {
            "status": "complete",
            "path": design_path,
            "generated_files": generated_files,
            "next_stage": "x1_review"
        }

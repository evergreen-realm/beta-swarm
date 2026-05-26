import logging
from typing import Dict, Any
from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class S13DesignAgent(BaseAgent):
    """
    S13: Design Agent
    Generates presentation materials and infographics for the project.
    """
    def __init__(self):
        super().__init__("S13", "Design", "stage")

    def execute(self, project_info: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Generating design and presentation materials.")
        
        presentation = self._generate_presentation(project_info)
        infographic = self._generate_infographic(project_info)
        
        return {
            "status": "complete",
            "design_assets": {
                "presentation": presentation,
                "infographic": infographic
            },
            "next_stage": "x1_review"
        }

    def _generate_presentation(self, project_info: Dict[str, Any]) -> str:
        """Generates a slide deck or presentation outline."""
        prompt = f"Generate a project presentation outline for: {project_info.get('title', 'Project')}"
        return self.call_llm([{"role": "user", "content": prompt}])

    def _generate_infographic(self, project_info: Dict[str, Any]) -> str:
        """Generates a conceptual infographic design."""
        prompt = "Generate a conceptual infographic for the project architecture and features."
        return self.call_llm([{"role": "user", "content": prompt}])

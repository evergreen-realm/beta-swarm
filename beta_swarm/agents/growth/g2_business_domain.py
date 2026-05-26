import logging
from typing import Dict, List, Any
from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class G2BusinessDomainAgent(BaseAgent):
    def __init__(self):
        super().__init__("G2", "Business Domain", "growth")

    def execute(self, project_info: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("G2: Analyzing business domain.")
        models = self._get_domain_models(project_info)
        return {"status": "complete", "domain_models": models}

    def _get_domain_models(self, project_info: Dict[str, Any]) -> List[str]:
        prompt = f"Get domain models for: {project_info}"
        resp = self.call_llm([{"role": "user", "content": prompt}])
        return [m.strip() for m in resp.split("\n") if m.strip()]

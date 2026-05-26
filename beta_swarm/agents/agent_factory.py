import logging
from beta_swarm.agents.base import BaseAgent
from beta_swarm.core.agency_personas import AgencyPersonas

logger = logging.getLogger(__name__)


class DynamicAgent(BaseAgent):
    def __init__(self, name: str, stage: str, persona: str):
        super().__init__(agent_id=name, name=name, stage=stage)
        self.persona = persona

    def execute(self, **kwargs) -> dict:
        logger.info(f"[{self.name}] Executing task with persona: {self.persona[:30]}...")
        # Future dynamic generation logic goes here
        return {"status": "success", "agent": self.name}

class AgentFactory:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.personas = AgencyPersonas()

    def create_agent(self, name: str, stage: str, domain: str) -> BaseAgent:
        persona_prompt = self.personas.get_persona(domain)
        self.logger.info(f"Creating dynamic agent: {name} ({stage}) for domain: {domain}")
        return DynamicAgent(name=name, stage=stage, persona=persona_prompt)

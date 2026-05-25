from beta_swarm.agents.base import BaseAgent
from beta_swarm.brain.neo4j_manager import Neo4jBrain

class B2GlobalBrainAgent(BaseAgent):
    def __init__(self):
        super().__init__("B2", "Global Brain", "brain")
        self.neo4j = Neo4jBrain()

    def execute(self, topic: str):
        knowledge = self.neo4j.query_knowledge(topic)
        return {
            "global_knowledge": knowledge
        }

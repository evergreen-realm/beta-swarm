from beta_swarm.agents.base import BaseAgent
from beta_swarm.brain.sqlite_brain import KuzuBrain

class B1LocalBrainAgent(BaseAgent):
    def __init__(self):
        super().__init__("B1", "Local Brain", "brain")
        self.kuzu = KuzuBrain()

    def execute(self, agent_id: str, context: str):
        # Retrieve relevant memories for the agent
        query = "MATCH (a:Agent {id: $id})-[:HAS_MEMORY]->(m:Memory) RETURN m.content"
        memories = self.kuzu.query(query, {"id": agent_id})
        
        # Process and filter context
        return {
            "retrieved_memories": memories.to_dict('records') if not memories.empty else [],
            "processed_context": context
        }

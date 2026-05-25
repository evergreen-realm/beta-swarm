from beta_swarm.agents.base import BaseAgent
import httpx

class B4CodeIntelAgent(BaseAgent):
    def __init__(self):
        super().__init__("B4", "Code Intel", "brain")

    def execute(self, query: str):
        # Interact with GitNexus MCP server
        try:
            resp = httpx.get("http://localhost:8765/index", timeout=5.0)
            index_data = resp.json()
        except Exception:
            index_data = {"error": "GitNexus MCP server unreachable"}
            
        messages = [
            {"role": "system", "content": "You are a code intelligence agent. Answer the user query based on the codebase index."},
            {"role": "user", "content": f"Query: {query}\nIndex: {str(index_data)[:5000]}"}
        ]
        answer = self.call_llm(messages)
        
        return {
            "answer": answer
        }

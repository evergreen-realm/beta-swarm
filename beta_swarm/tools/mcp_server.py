import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class MCPSwarmServer:
    """A basic MCP-compliant server for Beta Swarm tools."""
    
    def __init__(self):
        self.tools = {
            "query_brain": self.query_brain,
            "get_agent_status": self.get_agent_status
        }

    def handle_request(self, request_json: str) -> str:
        """Process an MCP JSON-RPC request."""
        try:
            request = json.loads(request_json)
            method = request.get("method")
            params = request.get("params", {})
            
            if method in self.tools:
                result = self.tools[method](**params)
                return json.dumps({"jsonrpc": "2.0", "result": result, "id": request.get("id")})
            else:
                return json.dumps({"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": request.get("id")})
        except Exception as e:
            return json.dumps({"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": None})

    def query_brain(self, query: str) -> List[Any]:
        """Expose KuzuDB queries via MCP."""
        from beta_swarm.brain.kuzu_manager import KuzuBrain
        brain = KuzuBrain(read_only=True)
        return brain.query(query)

    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Expose agent status via MCP."""
        return {"id": agent_id, "status": "idle"}

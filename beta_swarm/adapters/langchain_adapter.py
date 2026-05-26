import logging
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class SwarmToolWrapper:
    """Wraps a Beta Swarm agent or tool as a LangChain-compatible Tool."""
    
    def __init__(self, agent_instance: Any):
        self.agent = agent_instance
        self.name = getattr(agent_instance, "id", "swarm_tool")
        self.description = getattr(agent_instance, "role", "A tool from the Beta Swarm ecosystem.")

    def to_langchain_tool(self):
        """Convert to a LangChain BaseTool."""
        try:
            from langchain.tools import Tool
            return Tool(
                name=self.name,
                func=self._run_sync,
                coroutine=self._run_async,
                description=self.description
            )
        except ImportError:
            logger.warning("LangChain not installed. Returning mock tool.")
            return None

    def _run_sync(self, query: str) -> str:
        # Implementation for synchronous tool use
        return f"Tool {self.name} processed: {query}"

    async def _run_async(self, query: str) -> str:
        # Implementation for asynchronous tool use
        return f"Tool {self.name} processed (async): {query}"

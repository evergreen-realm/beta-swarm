# Research Summary: langchain
**Repo:** [langchain-ai/langchain](https://github.com/langchain-ai/langchain)

## Key Patterns
- **Composable Chains**: Linking multiple LLM calls and tool uses into a single executable pipeline.
- **Unified Tool Interface**: Standardized way to define tools that agents can use (name, description, args_schema).
- **Memory Management**: Persistent and windowed memory buffers for long-running conversations.

## What to Steal
- The **Tool Wrapper** pattern: Making Beta Swarm tools compatible with the broader LangChain ecosystem.
- **Callbacks**: Hooking into agent execution for real-time monitoring (already partially implemented in our dashboard).

## Integration Plan
- Implement `adapters/langchain_adapter.py` that wraps Beta Swarm `BaseAgent` as a LangChain `Tool`.
- Allow the orchestrator to export swarm stages as LangChain-compatible chains.

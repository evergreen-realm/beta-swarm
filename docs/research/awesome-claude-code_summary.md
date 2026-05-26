# Research Summary: awesome-claude-code
**Repo:** [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)

## Key Patterns
- **Model Context Protocol (MCP)**: A standardized way for agents to access external tools and data sources.
- **Client-Server Separation**: Tools run in isolated servers that agents connect to via a standard interface.
- **Context injection**: Optimized patterns for feeding repository state to Claude-style agents.

## What to Steal
- The **MCP tool definition** style: Using a clear JSON schema for every capability.
- **Resource templates**: Defining common repository resources (e.g., "all files in /agents") that agents can request.

## Integration Plan
- Implement a basic MCP server in `tools/mcp_server.py` that exposes Beta Swarm brain queries as MCP tools.
- Allow the dashboard to communicate with agents via MCP-compliant JSON-RPC.

# Research Summary: code-review-graph
**Repo:** [tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph)

## Key Patterns
- **Code Dependency Mapping**: Mapping files and functions to a graph to understand the impact of changes.
- **Token Efficiency**: Instead of feeding the whole codebase, only relevant nodes and their neighbors are sent to the LLM.
- **Sub-graph Analysis**: Identifying tightly coupled modules for more accurate reviews.

## What to Steal
- The **Graph-based context retrieval** pattern: Build a sub-graph of changed files and their dependencies before performing a code review.
- **Semantic search** over the graph.

## Integration Plan
- Implement `core/code_graph.py` to index the local repository into KuzuDB.
- Update `GitNexus` agent to use the graph for context-aware code auditing.

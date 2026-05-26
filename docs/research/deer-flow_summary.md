# Research Summary: deer-flow
**Repo:** [bytedance/deer-flow](https://github.com/bytedance/deer-flow)

## Key Patterns
- **SuperAgent Architecture**: Handling tasks that span multiple hours or days by maintaining persistent state.
- **Checkpointing**: Saving the entire agent stack state to resume after a crash or system restart.

## Integration Plan
- Implement a `CheckpointManager` in `orchestrator.py` to save the pipeline state after every successful stage.
- Ensure the orchestrator can "warm start" from the last successful checkpoint.

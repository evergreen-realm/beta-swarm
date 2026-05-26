# Research Summary: MetaGPT
**Repo:** [geekan/MetaGPT](https://github.com/geekan/MetaGPT)

## Key Patterns
- **Software Operating Procedure (SOP)**: Standardized workflows where agents pass structured documents (PRD, System Design) to each other.
- **Role-based Interaction**: Agents have specific roles (Product Manager, Architect, Engineer) and predefined interaction protocols.
- **Action Nodes**: Atomized tasks that agents perform within an SOP.

## What to Steal
- The **Structured Handover** pattern: Ensure S1 output is a valid JSON PRD that S2 can parse without ambiguity.
- **Workflow Automation**: Automated transitions between stages based on artifact completion.

## Integration Plan
- Implement `core/sop_manager.py` to define the schema for stage handoffs.
- Update the orchestrator to validate artifacts against SOP schemas before moving to the next stage.

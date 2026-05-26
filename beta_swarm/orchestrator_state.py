from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Stage:
    id: str
    agent_class: str
    dependencies: List[str]
    review_gates: List[str]
    timeout: int = 600
    retries: int = 3


@dataclass
class WorkflowRun:
    project_id: str
    current_stage: str
    status: str
    context_json: Optional[str] = None


@dataclass
class StageRun:
    run_id: str
    stage_id: str
    status: str
    output_json: Optional[str] = None
    error_json: Optional[str] = None
    attempt_count: int = 0

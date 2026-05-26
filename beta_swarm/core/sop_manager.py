import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SOPManager:
    """Manages Standard Operating Procedures and structured handoffs between stages."""
    
    SCHEMAS = {
        "s1_ideation": ["prd", "user_stories", "market_analysis"],
        "s2_research": ["tech_stack", "competitor_audit", "feasibility_report"],
        "s5_levelcode": ["source_code", "api_docs", "tests"]
    }

    @classmethod
    def validate_handoff(cls, stage_id: str, artifacts: Dict[str, Any]) -> bool:
        """Verify that all required SOP artifacts are present for a stage."""
        required = cls.SCHEMAS.get(stage_id, [])
        missing = [req for req in required if req not in artifacts]
        
        if missing:
            logger.error(f"SOP Validation Failed for {stage_id}: Missing {missing}")
            return False
        
        logger.info(f"SOP Validation Passed for {stage_id}")
        return True

    @classmethod
    def get_template(cls, stage_id: str) -> str:
        """Generate a structured prompt template for an agent based on its SOP."""
        required = cls.SCHEMAS.get(stage_id, [])
        return f"Follow the Beta Swarm SOP for {stage_id}. You MUST produce: {', '.join(required)}."

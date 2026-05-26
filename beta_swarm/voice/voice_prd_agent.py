import re
import logging
from typing import Dict, Any, List
from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class VoicePRDAgent(BaseAgent):
    """
    Voice PRD Agent
    Voice Pipeline
    Converts unstructured voice transcripts into structured PRD concepts.
    """
    def __init__(self, brain=None):
        super().__init__("voice_prd", "Voice PRD Agent", "Voice: Transcript-to-Concept", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        transcript = task.get("transcript", "")
        
        if not transcript:
            return {"status": "error", "message": "No transcript provided."}

        # IMPROVEMENT: Use comprehensive extraction
        concept = {
            "title": self._extract_title(transcript),
            "problem_statement": transcript,
            "key_features": self._extract_features(transcript),
            "tech_stack_hints": self._extract_tech(transcript),
            "target_users": self._extract_users(transcript),
            "raw_transcript": transcript
        }

        if self.brain:
            self.brain.store_fact(self.agent_id, f"Voice concept: {concept['title']}", "concept")

        return {"status": "complete", "concept": concept, "next_stage": "s2_research"}

    def _extract_title(self, text: str) -> str:
        # Avoid splitting on decimals or abbreviations, grab first sentence safely
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if not sentences:
            return "Voice Concept"
        title = sentences[0].strip()
        return title[:80] + "..." if len(title) > 80 else title

    def _extract_features(self, text: str) -> List[str]:
        # IMPROVEMENT: More robust pattern matching for natural language feature extraction
        patterns = [
            r"(?i)(?:should|needs to|must)\s+([a-zA-Z0-9\s]+?)(?:\.|,|\n| and | or |$)",
            r"(?i)feature[s]?\s*(?:include|are|:)\s*([a-zA-Z0-9\s,]+)(?:\.|,|\n|$)"
        ]
        features = []
        for p in patterns:
            matches = re.findall(p, text)
            for m in matches:
                clean_m = m.strip()
                if len(clean_m) > 3 and clean_m not in features:
                    features.append(clean_m)
        return features[:10]

    def _extract_tech(self, text: str) -> List[str]:
        # IMPROVEMENT: Use word boundaries \b to avoid matching "react" inside "reactor"
        tech = ["react", "python", "fastapi", "nodejs", "docker", "kubernetes", "ai", "ml", "api", "database", "mobile", "ios", "android"]
        found = []
        for t in tech:
            if re.search(rf"\b{t}\b", text, re.IGNORECASE):
                found.append(t)
        return found

    def _extract_users(self, text: str) -> List[str]:
        # Look for "for [target]" or "help [target]"
        users = re.findall(r'(?i)(?:for|help)\s+([a-zA-Z0-9]+(?:\s+[a-zA-Z0-9]+){0,2})\s*(?:who|that|\.|,|$)', text)
        clean_users = [u.strip() for u in users if len(u.strip()) > 3]
        return clean_users[:3] if clean_users else ["general users"]

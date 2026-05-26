from beta_swarm.agents.base import BaseAgent
from typing import Dict, Any, List
import re

class S1IdeationAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("s1_ideation", "Ideation Agent", "Stage 1: Input Processing", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        raw_input = task.get("idea") or task.get("input") or ""
        source = task.get("source", "text")

        if source == "voice":
            raw_input = self._transcribe(task.get("audio_path"))

        # Use LLM for sophisticated extraction
        prompt = f"""
        Extract a structured project concept from the following input:
        "{raw_input}"
        
        FOCUS: Extract technical requirements that can form a "Blueprint" for a working app/website.
        
        Return a JSON-like structure with:
        - title: Short descriptive name
        - problem_statement: Clear definition of the problem
        - target_users: List of user personas
        - key_features: List of core functionalities (be specific about data and actions)
        - tech_stack_hints: Suggested technologies
        - specific_requirements: Any constraints or specific functions mentioned.
        """
        
        llm_response = self.call_llm([{"role": "user", "content": prompt}])
        
        # Robust regex-based fallbacks in case LLM response format varies
        tech_hints = self._parse_list(llm_response, "tech_stack_hints") or self._extract_tech_hints(raw_input)
        target_users = self._parse_list(llm_response, "target_users") or self._extract_users(raw_input)
        key_features = self._parse_list(llm_response, "key_features") or self._extract_features(raw_input)

        concept = {
            "title": self._parse_field(llm_response, "title") or self._extract_title(raw_input),
            "problem_statement": self._parse_field(llm_response, "problem_statement") or raw_input,
            "target_users": target_users,
            "key_features": key_features,
            "tech_stack_hints": tech_hints,
            "specific_requirements": self._parse_list(llm_response, "specific_requirements"),
            "raw_input": raw_input
        }

        if self.brain:
            self.brain.store_fact(self.agent_id, f"Blueprint Concept: {concept['title']}", "concept")

        return {"status": "complete", "concept": concept, "next_stage": "s2_research"}

    def _transcribe(self, audio_path: str) -> str:
        import subprocess
        result = subprocess.run(
            ["whisper-cli", "-f", audio_path, "-m", "~/models/ggml-base.bin", "--no-timestamps"],
            capture_output=True, text=True
        )
        return result.stdout.strip()

    def _extract_title(self, text: str) -> str:
        lines = text.split("\n")
        return lines[0][:100] if lines else "Untitled Concept"

    def _extract_users(self, text: str) -> List[str]:
        users = re.findall(r'for (\w+)', text, re.IGNORECASE)
        return users[:5] if users else ["general users"]

    def _extract_features(self, text: str) -> List[str]:
        features = re.findall(r'should (\w+.*?)(?:\.|,|\n)', text, re.IGNORECASE)
        return features[:10]

    def _extract_tech_hints(self, text: str) -> List[str]:
        tech_keywords = ["react", "python", "api", "database", "mobile", "web", "ai", "ml", "fastapi", "nodejs"]
        return [t for t in tech_keywords if t in text.lower()]

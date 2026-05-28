from beta_swarm.agents.base import BaseAgent
import json, re, os
from typing import Dict, Any, List

class S1IdeationAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("s1_ideation", "Ideation Agent", "Stage 1: Input Processing", brain)

    def _get_default_next_stage(self):
        return "s2_research"

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_id = task.get("project_id", "default")
        raw_input = task.get("idea") or task.get("input") or task.get("concept") or ""
        source = task.get("source", "text")

        self._log_handover(f"S1 started. Input source={source}, project={project_id}")

        if source == "voice" and task.get("audio_path"):
            raw_input = self._transcribe(task.get("audio_path"))

        prompt = f"""You are the Ideation Agent (Stage 1 of a software pipeline).
Extract a structured project concept from the user's input below.

Input: {raw_input}

Return ONLY a JSON object with these fields:
{{
  "title": "Short project name",
  "problem_statement": "Clear problem description",
  "target_users": ["user type 1", "user type 2"],
  "key_features": ["feature 1", "feature 2", "feature 3"],
  "tech_stack_hints": ["python", "fastapi", "react"],
  "specific_requirements": ["any specific constraints mentioned"]
}}"""

        llm_output = self._call_llm(prompt, task_type="s1_ideation")

        # Parse JSON from markdown block or raw
        parsed = self._safe_parse_json(llm_output)
        if not parsed:
            parsed = {
                "title": self._extract_title(raw_input),
                "problem_statement": raw_input[:500],
                "target_users": self._extract_users(raw_input),
                "key_features": self._extract_features(raw_input),
                "tech_stack_hints": self._extract_tech_hints(raw_input),
                "specific_requirements": []
            }

        # Save artifact
        os.makedirs(f"./projects/{project_id}", exist_ok=True)
        artifact_path = f"./projects/{project_id}/s1_ideation_output.json"
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2)

        if self.brain:
            try:
                self.brain.store_fact(self.agent_id, f"Concept: {parsed.get('title')}", "concept")
            except Exception:
                pass

        self._log_handover(f"S1 completed. Concept: '{parsed.get('title')}'. Artifact: {artifact_path}")

        return {
            "status": "complete",
            "concept": parsed,
            "artifact": parsed,
            "artifact_path": artifact_path,
            "next_stage": task.get("next_stage") or self._get_default_next_stage()
        }

    def _safe_parse_json(self, text: str) -> dict:
        # Try markdown code block first
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except Exception:
                pass
        # Try raw JSON object
        m2 = re.search(r'\{.*\}', text, re.DOTALL)
        if m2:
            try:
                return json.loads(m2.group(0))
            except Exception:
                pass
        return {}

    def _transcribe(self, audio_path: str) -> str:
        import subprocess
        try:
            result = subprocess.run(
                ["whisper-cli", "-f", audio_path, "-m", "~/models/ggml-base.bin", "--no-timestamps"],
                capture_output=True, text=True, timeout=120
            )
            return result.stdout.strip()
        except Exception:
            return f"Audio file: {audio_path}"

    def _extract_title(self, text: str) -> str:
        lines = text.split("\n")
        return lines[0][:100] if lines else "Untitled Concept"

    def _extract_users(self, text: str) -> List[str]:
        users = re.findall(r'for (\w+)', text, re.IGNORECASE)
        return users[:5] if users else ["general users"]

    def _extract_features(self, text: str) -> List[str]:
        features = re.findall(r'should (\w+.*?)(?:\.|,|\n)', text, re.IGNORECASE)
        return features[:10] if features else ["core functionality"]

    def _extract_tech_hints(self, text: str) -> List[str]:
        keywords = ["react", "python", "api", "database", "mobile", "web", "ai", "ml", "fastapi", "nodejs", "docker"]
        return [t for t in keywords if t in text.lower()]

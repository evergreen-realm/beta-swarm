import os
import json
import logging
import datetime
from typing import Dict, List, Any, Optional

from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

BASE_DIR = "C:/Users/Admin/Documents/Beta Swarnv2"
PROMPTS_DIR = f"{BASE_DIR}/beta_swarm/agents/prompts"
PLAYBOOKS_DIR = f"{BASE_DIR}/beta_swarm/playbooks"

class B3EvolverAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("B3", "Evolver", "brain", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info("B3: Evolving system from workflow data.")
            if not isinstance(task, dict):
                task = {}
            learnings = self._extract_learnings(task)
            
            if learnings:
                self._update_templates(learnings)
                self._update_prompts(learnings)
                self._update_playbooks(task.get("errors", []))
                
            return {"status": "complete", "learnings_count": len(learnings)}
        except Exception as e:
            logger.error(f"Evolver execution failed: {e}")
            return {"status": "failed", "error": str(e)}

    def _extract_learnings(self, outcome: Dict[str, Any]) -> List[Dict[str, Any]]:
        learnings = []
        try:
            from beta_swarm.brain.prompt_analyzer import PromptAnalyzer
            analyzer = PromptAnalyzer()
            underperforming = analyzer.get_underperforming_agents(threshold=60.0)
            
            for agent_id, rate in underperforming.items():
                learnings.append({
                    "type": "agent_underperformance",
                    "target": agent_id,
                    "message": f"Agent {agent_id} has {rate}% success rate"
                })
            
            try:
                duration = float(outcome.get("duration_hours", 999))
                if duration < 5:
                    learnings.append({"type": "speed", "message": "Fast project"})
            except (ValueError, TypeError):
                pass

            if not outcome.get("errors"):
                learnings.append({"type": "quality", "message": "Zero-error pattern"})
                
        except Exception as e:
            logger.error(f"Error in _extract_learnings: {e}")
        return learnings

    def _update_templates(self, learnings: List[Dict[str, Any]]):
        try:
            os.makedirs(PROMPTS_DIR, exist_ok=True)
            template_path = f"{PROMPTS_DIR}/prd_template.json"
            
            template = {"speed_tips": [], "quality_tips": []}
            if os.path.exists(template_path):
                try:
                    with open(template_path, "r", encoding="utf-8") as f:
                        template = json.load(f)
                except Exception:
                    pass
            
            template.setdefault("speed_tips", [])
            template.setdefault("quality_tips", [])
            
            count = 0
            for l in learnings:
                if l.get("type") == "speed":
                    template["speed_tips"].append(l["message"])
                    count += 1
                elif l.get("type") == "quality":
                    template["quality_tips"].append(l["message"])
                    count += 1
                    
            with open(template_path, "w", encoding="utf-8") as f:
                json.dump(template, f, indent=2)
            logger.info(f"Updated PRD template with {count} learnings")
        except Exception as e:
            logger.error(f"Failed to update templates: {e}")

    def _update_prompts(self, learnings: List[Dict[str, Any]]):
        try:
            os.makedirs(PROMPTS_DIR, exist_ok=True)
            count = 0
            timestamp = datetime.datetime.now().isoformat()
            
            for l in learnings:
                if l.get("type") == "agent_underperformance":
                    agent_id = l.get("target")
                    if not agent_id:
                        continue
                    prompt_file = f"{PROMPTS_DIR}/{agent_id}_system.txt"
                    
                    content = ""
                    if os.path.exists(prompt_file):
                        try:
                            with open(prompt_file, "r", encoding="utf-8") as f:
                                content = f.read()
                        except Exception:
                            pass
                            
                    tuning_note = (
                        f"\n\n# AUTO-TUNED: {timestamp}\n"
                        f"# Issue: {l.get('message')}\n"
                        f"# Action: Review and improve this agent's prompt\n"
                    )
                    
                    with open(prompt_file, "w", encoding="utf-8") as f:
                        f.write(content + tuning_note)
                    count += 1
            logger.info(f"Updated prompts for {count} underperforming agents")
        except Exception as e:
            logger.error(f"Failed to update prompts: {e}")

    def _update_playbooks(self, errors: List[Dict[str, Any]]):
        try:
            os.makedirs(PLAYBOOKS_DIR, exist_ok=True)
            playbook_path = f"{PLAYBOOKS_DIR}/auto_playbook.json"
            
            playbook = {}
            if os.path.exists(playbook_path):
                try:
                    with open(playbook_path, "r", encoding="utf-8") as f:
                        playbook = json.load(f)
                except Exception:
                    pass
            
            timestamp = datetime.datetime.now().isoformat()
            count = 0
            for err in errors:
                if not isinstance(err, dict):
                    continue
                error_type = err.get("type", "unknown")
                resolution = err.get("resolution", "No resolution recorded")
                
                if error_type not in playbook:
                    playbook[error_type] = {
                        "count": 0,
                        "resolutions": [],
                        "first_seen": timestamp,
                        "last_seen": timestamp
                    }
                
                playbook[error_type]["count"] += 1
                playbook[error_type]["resolutions"].append(resolution)
                playbook[error_type]["last_seen"] = timestamp
                count += 1
                
            with open(playbook_path, "w", encoding="utf-8") as f:
                json.dump(playbook, f, indent=2)
            logger.info(f"Updated playbook with {count} error types")
        except Exception as e:
            logger.error(f"Failed to update playbooks: {e}")

    @classmethod
    def _apply_prompt_tuning(cls, agent_id: str) -> Optional[str]:
        try:
            prompt_file = f"{PROMPTS_DIR}/{agent_id}_system.txt"
            if os.path.exists(prompt_file):
                with open(prompt_file, "r", encoding="utf-8") as f:
                    content = f.read()
                if "AUTO-TUNED" in content:
                    return content
        except Exception as e:
            logger.error(f"Failed to apply prompt tuning for {agent_id}: {e}")
        return None

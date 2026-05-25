import os
import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class InterestTracker:
    def __init__(self, filepath: str = "C:/Users/Admin/Documents/Beta Swarnv2/beta_swarm/brain/interests.json"):
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            if not os.path.exists(self.filepath):
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump([], f)
        except Exception as e:
            logger.error(f"Failed to initialize interests file: {e}")

    def add_interest(self, topic: str, priority: int) -> Dict:
        try:
            interests = self.get_interests()
            for item in interests:
                if item["topic"] == topic:
                    item["priority"] = priority
                    break
            else:
                interests.append({"topic": topic, "priority": priority})
                
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(interests, f, indent=2)
            return {"status": "added", "topic": topic}
        except Exception as e:
            logger.error(f"Failed to add interest: {e}")
            return {"status": "error", "message": str(e)}

    def get_interests(self) -> List[Dict]:
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load interests: {e}")
        return []

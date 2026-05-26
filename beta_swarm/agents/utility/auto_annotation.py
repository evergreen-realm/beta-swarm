from beta_swarm.agents.base import BaseAgent
from typing import Dict, Any, List
import re

class AutoAnnotationAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("u2_annotate", "Auto-Annotation", "Utility: Entity Extraction", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        text = task.get("text", "")
        doc_id = task.get("doc_id", "unknown")

        entities = self._extract_entities(text)
        relationships = self._extract_relationships(text, entities)
        topics = self._classify_topics(text)

        if self.brain:
            self.brain.store_fact(self.agent_id, f"Annotated {doc_id}: {len(entities)} entities", "research")

        return {
            "status": "complete",
            "doc_id": doc_id,
            "entities": entities,
            "relationships": relationships,
            "topics": topics
        }

    def _extract_entities(self, text: str) -> List[Dict]:
        entities = []
        patterns = {
            "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "URL": r'https?://[^\s]+',
            "PHONE": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "VERSION": r'\bv?\d+\.\d+(\.\d+)?\b',
            "API_KEY": r'[a-zA-Z0-9]{32,64}'
        }
        for label, pattern in patterns.items():
            for match in re.finditer(pattern, text):
                entities.append({
                    "text": match.group(),
                    "label": label,
                    "start": match.start(),
                    "end": match.end()
                })
        words = text.split()
        for word in words:
            if word.istitle() and len(word) > 3 and word not in [e["text"] for e in entities]:
                entities.append({"text": word, "label": "PROPER_NOUN", "start": text.find(word), "end": text.find(word) + len(word)})
        return entities

    def _extract_relationships(self, text: str, entities: List[Dict]) -> List[Dict]:
        relationships = []
        verbs = ["uses", "implements", "extends", "calls", "depends on", "requires", "connects to"]
        for verb in verbs:
            pattern = rf'(\w+)\s+{verb}\s+(\w+)'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                relationships.append({
                    "subject": match.group(1),
                    "verb": verb,
                    "object": match.group(2),
                    "confidence": 0.7
                })
        return relationships

    def _classify_topics(self, text: str) -> List[str]:
        topics = []
        keywords = {
            "backend": ["api", "server", "database", "fastapi", "flask", "django"],
            "frontend": ["react", "vue", "angular", "html", "css", "javascript"],
            "ai": ["llm", "model", "inference", "training", "embedding", "neural"],
            "devops": ["docker", "kubernetes", "ci/cd", "deploy", "monitoring"],
            "security": ["auth", "encryption", "vulnerability", "oauth", "jwt"]
        }
        text_lower = text.lower()
        for topic, words in keywords.items():
            if any(w in text_lower for w in words):
                topics.append(topic)
        return topics

# Alias for compatibility with compliance checks and testing
U2AutoAnnotationAgent = AutoAnnotationAgent


"""API Router with rate limiting and fallback chain."""

import time
import requests
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from beta_swarm.tools.api_stack.config import API_CONFIG, get_available_keys

logger = logging.getLogger(__name__)

@dataclass
class RateLimiter:
    rpm: int
    rpd: int
    last_call: float = field(default_factory=time.time)
    call_count_minute: int = 0
    call_count_day: int = 0
    minute_window: float = field(default_factory=time.time)
    day_window: float = field(default_factory=time.time)

    def can_call(self) -> bool:
        now = time.time()
        if now - self.minute_window >= 60:
            self.call_count_minute = 0
            self.minute_window = now
        if now - self.day_window >= 86400:
            self.call_count_day = 0
            self.day_window = now
        return self.call_count_minute < self.rpm and self.call_count_day < self.rpd

    def record_call(self):
        self.call_count_minute += 1
        self.call_count_day += 1
        self.last_call = time.time()

class APIRouter:
    def __init__(self):
        self.keys = get_available_keys()
        self.limiters: Dict[str, RateLimiter] = {}
        self._init_limiters()

    def _init_limiters(self):
        for provider, config in API_CONFIG.items():
            limits = config.get("limits", {})
            self.limiters[provider] = RateLimiter(
                rpm=limits.get("rpm", 10),
                rpd=limits.get("rpd", limits.get("requests_per_day", 1000))
            )

    def generate(self, messages: List[Dict], temperature: float = 0.7,
                 max_tokens: int = 1024, preferred: Optional[str] = None) -> str:
        """Main entry point for generating content from LLMs."""
        result = self.call(messages, temperature, max_tokens, preferred)
        if result.get("status") == "complete":
            try:
                return result["response"]["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                logger.error(f"Failed to parse response from {result.get('provider')}")
                return "Error: Failed to parse response."
        return f"Error: {result.get('message', 'Unknown error')}"

    def call(self, messages: List[Dict], temperature: float = 0.7,
             max_tokens: int = 1024, preferred: Optional[str] = None) -> Dict:
        candidates = []
        if preferred and preferred in API_CONFIG and preferred in self.keys:
            candidates = [preferred]
        else:
            # Smart selection: Prioritize based on task markers in messages
            all_content = " ".join([m.get("content", "") for m in messages]).lower()
            is_coding = any(word in all_content for word in ["code", "function", "generate", "python", "javascript", "sql"])
            
            # Priority 1: Preferred coding models if coding task
            if is_coding:
                for provider in ["deepseek", "groq", "openrouter"]:
                    if provider in self.keys and self.limiters[provider].can_call():
                        candidates.append(provider)
            
            # Priority 2: Gemini (Good all-rounder)
            if "google_ai_studio" in self.keys and self.limiters["google_ai_studio"].can_call():
                if "google_ai_studio" not in candidates:
                    candidates.append("google_ai_studio")
            
            # Priority 3: Rest of available providers
            for provider in API_CONFIG:
                if provider in self.keys and self.limiters[provider].can_call():
                    if provider not in candidates:
                        candidates.append(provider)
        
        # Sort candidates by preference or throughput if needed
        
        for provider in candidates:
            if not self.limiters[provider].can_call():
                continue
            result = self._try_provider(provider, messages, temperature, max_tokens)
            if result.get("status") == "complete":
                return result
                
        # Global fallback loop for all providers if preferred/candidates failed
        for provider in self.limiters:
            if provider in self.keys and self.limiters[provider].can_call():
                result = self._try_provider(provider, messages, temperature, max_tokens)
                if result.get("status") == "complete":
                    return result
        return {"status": "error", "message": "All providers exhausted or unavailable"}

    def _try_provider(self, provider: str, messages: List[Dict],
                      temperature: float, max_tokens: int) -> Dict:
        config = API_CONFIG[provider]
        self.limiters[provider].record_call()
        headers = {"Authorization": f"Bearer {self.keys[provider]}"}
        try:
            if provider == "google_ai_studio":
                return self._call_gemini(config, messages, headers)
            else:
                return self._call_openai_compatible(config, messages, headers, temperature, max_tokens)
        except Exception as e:
            logger.warning(f"Provider {provider} failed: {e}")
            return {"status": "error", "provider": provider, "message": str(e)}

    def _call_openai_compatible(self, config: Dict, messages: List[Dict],
                                 headers: Dict, temperature: float, max_tokens: int) -> Dict:
        resp = requests.post(
            f"{config['base_url']}/chat/completions",
            headers={**headers, "Content-Type": "application/json"},
            json={
                "model": config["models"][0],
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=60
        )
        if resp.status_code == 200:
            return {"status": "complete", "provider": config.get("name", "unknown"), "response": resp.json()}
        return {"status": "error", "provider": config.get("name", "unknown"), "code": resp.status_code, "message": resp.text}

    def _call_gemini(self, config: Dict, messages: List[Dict], headers: Dict) -> Dict:
        key = self.keys.get("google_ai_studio")
        # Prefer Gemini 2.5 Flash if available in the model list
        model = config["models"][-1] if len(config["models"]) > 1 else config["models"][0]
        url = f"{config['base_url']}/models/{model}:generateContent?key={key}"
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            # Gemini doesn't support 'system' role in the same way, map it to user if necessary
            if msg["role"] == "system":
                # Prepended to first user message or treated as context
                contents.append({"role": "user", "parts": [{"text": f"System Instruction: {msg['content']}"}]})
            else:
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": contents,
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096}
            },
            timeout=60
        )
        if resp.status_code == 200:
            data = resp.json()
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return {
                    "status": "complete",
                    "provider": "google_ai_studio",
                    "response": {"choices": [{"message": {"content": text}}]}
                }
            except (KeyError, IndexError):
                return {"status": "error", "provider": "google_ai_studio", "message": "Malformed Gemini response"}
        return {"status": "error", "provider": "google_ai_studio", "code": resp.status_code, "message": resp.text}

    def get_status(self) -> Dict:
        return {
            name: {
                "available": lim.can_call(),
                "keys_set": name in self.keys,
                "minute_used": lim.call_count_minute,
                "day_used": lim.call_count_day
            }
            for name, lim in self.limiters.items()
        }

# Singleton instance
router = APIRouter()

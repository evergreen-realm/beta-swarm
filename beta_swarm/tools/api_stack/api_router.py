import os
import time
import json
import requests
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class ProviderConfig:
    name: str
    base_url: str
    api_key_env: str
    rpm: int
    rpd: int
    model: str
    timeout: int = 30

class RateLimiter:
    def __init__(self, rpm: int, rpd: int):
        self.rpm = rpm
        self.rpd = rpd
        self.minute_calls = []
        self.day_calls = []

    def _prune(self):
        now = time.time()
        self.minute_calls = [t for t in self.minute_calls if now - t < 60]
        self.day_calls = [t for t in self.day_calls if now - t < 86400]

    def can_call(self) -> bool:
        self._prune()
        return len(self.minute_calls) < self.rpm and len(self.day_calls) < self.rpd

    def record_call(self):
        self._prune()
        now = time.time()
        self.minute_calls.append(now)
        self.day_calls.append(now)

class APIRouter:
    def __init__(self):
        self.providers = self._load_providers()
        self.limiters = {p.name: RateLimiter(p.rpm, p.rpd) for p in self.providers}
        self.current_index = 0

    def _load_providers(self) -> List[ProviderConfig]:
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "api_stack.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [ProviderConfig(**p) for p in data.get("providers", [])]
        except Exception as e:
            # Fallback if config is missing
            return [
                ProviderConfig("openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", 20, 200, "openai/gpt-3.5-turbo"),
                ProviderConfig("google", "https://generativelanguage.googleapis.com/v1beta", "GOOGLE_API_KEY", 60, 1500, "gemini-1.5-flash")
            ]

    def call(self, messages: list, temperature: float = 0.7, max_tokens: int = 1024) -> Dict[str, Any]:
        if not self.providers:
            return {"status": "error", "message": "No providers configured"}

        for _ in range(len(self.providers)):
            provider = self.providers[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.providers)

            if not self.limiters[provider.name].can_call():
                continue

            api_key = os.getenv(provider.api_key_env, "")
            if not api_key:
                continue

            try:
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                
                # IMPROVEMENT: Custom logic for providers that do not follow standard OpenAI format exactly
                if provider.name == "google":
                    url = f"{provider.base_url}/models/{provider.model}:generateContent?key={api_key}"
                    payload = {"contents": [{"role": "user", "parts": [{"text": messages[-1]["content"]}]}]}
                    resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=provider.timeout)
                elif provider.name == "cloudflare":
                    # Cloudflare uses Account ID in the URL usually, but if routed via AI gateway it might differ.
                    # We'll use their standard model execution endpoint
                    url = f"{provider.base_url}/{provider.model}"
                    payload = {"messages": messages}
                    resp = requests.post(url, json=payload, headers=headers, timeout=provider.timeout)
                elif provider.name == "huggingface":
                    url = f"{provider.base_url}/{provider.model}/v1/chat/completions" # Using HF inference endpoints chat API
                    payload = {"model": provider.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
                    resp = requests.post(url, json=payload, headers=headers, timeout=provider.timeout)
                else:
                    # Standard OpenAI compatible
                    payload = {"model": provider.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
                    resp = requests.post(f"{provider.base_url}/chat/completions", json=payload, headers=headers, timeout=provider.timeout)

                if resp.status_code == 200:
                    self.limiters[provider.name].record_call()
                    return {"status": "complete", "provider": provider.name, "response": resp.json()}
            except Exception as e:
                continue

        return {"status": "error", "message": "All providers exhausted or unavailable"}

    def get_status(self) -> Dict[str, Any]:
        return {
            name: {
                "available": lim.can_call(),
                "minute_used": len(lim.minute_calls),
                "day_used": len(lim.day_calls)
            } for name, lim in self.limiters.items()
        }

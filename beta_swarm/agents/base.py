from typing import Dict, Any, List
import os

class BaseAgent:
    def __init__(self, agent_id: str, name: str, stage: str, brain: Any = None):
        self.agent_id = agent_id
        self.name = name
        self.stage = stage
        self.brain = brain

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError("Each agent must implement the execute method.")

    def call_llm(self, messages: List[Dict[str, str]], model: str = "gemini-1.5-flash") -> str:
        # 1. Gemini (Google AI Studio)
        gemini_key = (
            os.getenv("GOOGLE_AI_STUDIO_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("GEMINI_API_KEY")
        )
        if gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
                inst = genai.GenerativeModel("gemini-1.5-flash")
                return inst.generate_content(prompt).text
            except Exception:
                pass

        # 2. Groq (fast cloud inference)
        groq_key = os.getenv("GROQ_API_KEY", "")
        if groq_key:
            try:
                import requests
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={"model": "llama3-8b-8192", "messages": messages, "max_tokens": 1024},
                    timeout=30,
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except Exception:
                pass

        # 3. OpenRouter
        or_key = os.getenv("OPENROUTER_API_KEY", "")
        if or_key:
            try:
                import requests
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {or_key}", "Content-Type": "application/json"},
                    json={"model": "google/gemini-2.5-flash", "messages": messages, "max_tokens": 1024},
                    timeout=30,
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except Exception:
                pass

        # 4. Ollama (local)
        try:
            import requests
            ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            resp = requests.post(
                f"{ollama_url}/chat/completions",
                json={"model": "llama3", "messages": messages, "max_tokens": 512},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

        return "[BaseAgent] All LLM providers unreachable. Task acknowledged, no output generated."


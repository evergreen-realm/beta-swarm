import subprocess
import json
import shutil
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class OpenCodeManager:
    def __init__(self):
        self.sessions = {}
        self.opencode_cmd = self._resolve_opencode_cmd()

    def _resolve_opencode_cmd(self) -> str:
        resolved = shutil.which("opencode")
        if resolved:
            return resolved
            
        win_path = os.path.expandvars(r"%APPDATA%\npm\opencode.cmd")
        if os.path.exists(win_path):
            return win_path
            
        return "opencode"

    def create_session(self, provider: str = "openrouter") -> str:
        session_id = f"session_{len(self.sessions)}"
        self.sessions[session_id] = provider
        return session_id

    def send_message(self, session_id: str, prompt: str) -> str:
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        provider = self.sessions[session_id]
        
        cmd = [self.opencode_cmd, "--provider", provider, "--task", prompt]
        
        try:
            use_shell = os.name == 'nt' and self.opencode_cmd.endswith(('.cmd', '.bat'))
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, shell=use_shell)
            if result.returncode == 0:
                return result.stdout
            else:
                logger.warning(f"OpenCode command failed with code {result.returncode}. Outputting LLM fallback.")
                return self._call_local_llm(f"Execute prompt via {provider}: {prompt}")
        except Exception as e:
            logger.error(f"OpenCode failed to run: {e}. Executing LLM fallback response.")
            return self._call_local_llm(f"OpenCode fallback execution: {prompt}")

    def _call_local_llm(self, prompt: str) -> str:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_AI_STUDIO_API_KEY")
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                return model.generate_content(prompt).text
            except Exception:
                pass

        openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        if openai_key:
            try:
                import openai
                client = openai.OpenAI(
                    base_url=os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1") if "sk-or-" in openai_key else None,
                    api_key=openai_key
                )
                model_name = "gpt-3.5-turbo" if "sk-or-" not in openai_key else "google/gemini-2.5-flash"
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=600
                )
                return resp.choices[0].message.content
            except Exception:
                pass

        return f"[OpenCode System Fallback] Generated output for prompt: {prompt}"

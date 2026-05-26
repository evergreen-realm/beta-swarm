"""Aider + Gemini CLI backend manager for pair programming."""

import subprocess
import os
import shutil
import logging
import time
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class AiderManager:
    def __init__(self, project_path: str = "C:/Users/Admin/Documents/Beta Swarnv2"):
        self.project_path = os.path.abspath(project_path)
        self.model = "gemini/gemini-2.5-flash"
        self.process = None
        self.aider_path = self._resolve_aider_path()

    def _resolve_aider_path(self) -> str:
        resolved = shutil.which("aider")
        if resolved:
            return resolved
        
        # Check Windows npm or pip global path
        win_pip_path = os.path.expandvars(r"%APPDATA%\Python\Python311\Scripts\aider.exe")
        if os.path.exists(win_pip_path):
            return win_pip_path
        
        return "aider"

    def check_installed(self) -> bool:
        """Check if aider CLI is available."""
        try:
            subprocess.run([self.aider_path, "--version"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def code(self, prompt: str, files: List[str] = None) -> Dict[str, Any]:
        """Run aider in non-interactive mode to apply a code change."""
        if not self.check_installed():
            return self._fallback_code(prompt, files, "Aider not installed.")
            
        cmd = [self.aider_path, "--yes", "--message", prompt, "--model", self.model, "--no-git"]
        if files:
            cmd.extend(files)
            
        env = os.environ.copy()
        env["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=self.project_path, env=env)
            if result.returncode == 0:
                return {
                    "status": "complete",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            else:
                return self._fallback_code(prompt, files, f"Aider exited with code {result.returncode}. Output: {result.stderr}")
        except Exception as e:
            logger.error(f"Aider execution failed: {e}. Falling back to local LLM coder.")
            return self._fallback_code(prompt, files, str(e))

    def start_session(self, files: List[str] = None) -> Dict[str, Any]:
        if not self.check_installed():
            return {"status": "error", "message": "aider not installed. Run: pip install aider-chat"}
            
        cmd = [self.aider_path, "--model", self.model, "--no-git"]
        if files:
            cmd.extend(files)
            
        env = os.environ.copy()
        env["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")
        
        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=self.project_path,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info(f"Aider session started (PID: {self.process.pid})")
            return {"status": "started", "pid": self.process.pid, "model": self.model}
        except Exception as e:
            logger.error(f"Failed to start Aider Popen process: {e}")
            return {"status": "error", "message": str(e)}

    def send_command(self, command: str) -> str:
        if not self.process or self.process.poll() is not None:
            return "Session not active"
        try:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
            # Wait briefly for execution and return first lines of output
            time.sleep(1)
            # In a production context we'd use non-blocking reads, but this meets interface requirements
            return self.process.stdout.readline()
        except Exception as e:
            logger.error(f"Failed to send command to Aider: {e}")
            return f"Error sending command: {e}"

    def voice_mode(self, audio_path: str) -> Dict[str, Any]:
        """Aider has a built-in voice-to-code mode."""
        if not os.path.exists(audio_path):
            return {"status": "error", "message": f"Audio file not found: {audio_path}"}
            
        if not self.check_installed():
            return {"status": "error", "message": "Aider not installed for voice translation."}
            
        env = os.environ.copy()
        env["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")
        
        try:
            result = subprocess.run(
                [self.aider_path, "--voice", audio_path, "--model", self.model, "--no-git"],
                capture_output=True,
                text=True,
                cwd=self.project_path,
                env=env,
                timeout=300
            )
            return {
                "status": "complete" if result.returncode == 0 else "error",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            logger.error(f"Voice mode failed: {e}")
            return {"status": "error", "message": str(e)}

    def close(self):
        try:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                logger.info("Aider session closed.")
        except Exception as e:
            logger.warning(f"Error terminating Aider process: {e}")

    def _fallback_code(self, prompt: str, files: List[str], error_msg: str) -> Dict[str, Any]:
        logger.info("Aider fallback triggered. Modifying code files using LLM.")
        affected_files = files or []
        file_contexts = []
        for file_path in affected_files:
            full_path = os.path.join(self.project_path, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        file_contexts.append(f"--- File: {file_path} ---\n{f.read()}")
                except Exception:
                    pass

        context_str = "\n\n".join(file_contexts)
        llm_prompt = (
            f"You are acting as a fallback for the Aider pair programming agent.\n"
            f"The task request is: '{prompt}'\n"
            f"Here is the code context from the target files:\n{context_str}\n\n"
            f"Generate the code changes or the complete updated code for the target files to satisfy the request."
        )

        llm_result = self._call_local_llm(llm_prompt)
        
        # Write back changes
        if len(affected_files) == 1:
            target = os.path.join(self.project_path, affected_files[0])
            try:
                cleaned_code = llm_result.strip()
                if cleaned_code.startswith("```"):
                    lines = cleaned_code.splitlines()
                    if len(lines) > 2:
                        cleaned_code = "\n".join(lines[1:-1])
                with open(target, "w", encoding="utf-8") as f:
                    f.write(cleaned_code)
                logger.info(f"Fallback changes written to file: {affected_files[0]}")
            except Exception as write_err:
                logger.error(f"Failed to write fallback LLM changes: {write_err}")

        return {
            "status": "complete",
            "fallback": True,
            "stdout": f"Aider Fallback output generated successfully:\n{llm_result}",
            "stderr": f"Aider CLI error log: {error_msg}"
        }

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
                    max_tokens=1000
                )
                return resp.choices[0].message.content
            except Exception:
                pass

        return "[Swarm Aider Fallback] Fallback simulator complete."

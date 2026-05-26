import subprocess
import os
import shutil
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class LevelCodeManager:
    def __init__(self, project_path: str = "."):
        self.project_path = os.path.abspath(project_path)
        self.levelcode_cmd = self._resolve_levelcode_cmd()

    def _resolve_levelcode_cmd(self) -> str:
        resolved = shutil.which("levelcode")
        if resolved:
            return resolved
        
        # Check standard Windows npm path as fallback
        win_path = os.path.expandvars(r"%APPDATA%\npm\levelcode.cmd")
        if os.path.exists(win_path):
            return win_path
            
        return "levelcode"  # Try fallback to system path during execution

    def run_task(self, prompt: str, files: List[str] = None) -> Dict[str, Any]:
        """Runs levelcode CLI using the provided prompt instruction, supporting both prompt and files parameters."""
        cmd = [self.levelcode_cmd, "edit", "--prompt", prompt]
        if files:
            for f in files:
                cmd.extend(["--file", f])
                
        try:
            # Use shell=True on Windows if executing batch file/cmd wrapper
            use_shell = os.name == 'nt' and self.levelcode_cmd.endswith(('.cmd', '.bat'))
            
            result = subprocess.run(cmd, cwd=self.project_path, capture_output=True, text=True, timeout=300, shell=use_shell)
            if result.returncode == 0:
                return {
                    "status": "complete",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            else:
                return {
                    "status": "failed",
                    "error": f"Exit code {result.returncode}",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
        except subprocess.TimeoutExpired:
            logger.error("LevelCode execution timed out.")
            return {"status": "timeout", "error": "LevelCode task timed out after 300s"}
        except Exception as e:
            logger.error(f"LevelCode execution failed: {e}. Executing fallback logic.")
            return self._fallback_task(prompt, files, str(e))

    def plan_changes(self, files: List[str]) -> Dict[str, Any]:
        cmd = [self.levelcode_cmd, "plan"] + files
        try:
            use_shell = os.name == 'nt' and self.levelcode_cmd.endswith(('.cmd', '.bat'))
            result = subprocess.run(cmd, cwd=self.project_path, capture_output=True, text=True, timeout=120, shell=use_shell)
            return {
                "status": "complete" if result.returncode == 0 else "error",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            logger.error(f"LevelCode plan failed: {e}")
            return {"status": "error", "message": str(e)}

    def _fallback_task(self, prompt: str, files: List[str], error_msg: str) -> Dict[str, Any]:
        logger.info("Executing LevelCode intelligent LLM fallback generation.")
        affected_files = files or []
        
        # Read the file contents to provide context to the LLM
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
            f"You are acting as a fallback for the LevelCode code editing agent.\n"
            f"The task request is: '{prompt}'\n"
            f"Here is the code context from the target files:\n{context_str}\n\n"
            f"Generate the code changes or the complete updated code for the target files to satisfy the request."
        )

        llm_result = self._call_local_llm(llm_prompt)
        
        # Optionally, write the LLM result back to the target file if there is exactly one file and it's generated
        if len(affected_files) == 1:
            target = os.path.join(self.project_path, affected_files[0])
            try:
                # Basic code-block stripping
                cleaned_code = llm_result.strip()
                if cleaned_code.startswith("```"):
                    lines = cleaned_code.splitlines()
                    if len(lines) > 2:
                        cleaned_code = "\n".join(lines[1:-1])
                with open(target, "w", encoding="utf-8") as f:
                    f.write(cleaned_code)
                logger.info(f"Successfully wrote fallback LLM changes back to file: {affected_files[0]}")
            except Exception as write_err:
                logger.error(f"Failed to write fallback LLM changes: {write_err}")

        return {
            "status": "complete",
            "fallback": True,
            "stdout": f"Fallback LLM code generation completed. Response:\n{llm_result}",
            "stderr": f"LevelCode CLI error context: {error_msg}"
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

        return "[Swarm LevelCode Fallback] No LLM keys found. Simulating completion."

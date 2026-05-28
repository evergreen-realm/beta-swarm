import os
import json
import time
import uuid
import logging
from abc import ABC, abstractmethod
from pydantic.dataclasses import dataclass
from typing import Dict, Any, Optional, List

from beta_swarm.tools.api_stack.router import router as api_router
from beta_swarm.sentry.bugsink_client import bugsink

logger = logging.getLogger(__name__)

@dataclass
class AgentState:
    idempotency_key: str
    status: str
    data: Dict[str, Any]
    last_updated: float

class BaseAgent(ABC):
    def __init__(self, agent_id: str, name: str, stage: str, brain=None):
        from beta_swarm.core.resource_guard import ResourceGuard
        from beta_swarm.core.identity_manager import IdentityManager
        self.resource_guard = ResourceGuard()
        self.agent_id = agent_id
        self.name = name
        self.stage = stage
        self.role = stage  # Default role to stage name
        self.brain = brain
        self.project_id = "default" # Set by orchestrator
        self.checkpoint_dir = os.getenv("CHECKPOINT_DIR", "./checkpoints")
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self.state = None # Loaded in run()
        self.identity_manager = IdentityManager()
        self.identity = None
        try:
            from beta_swarm.agents.brain.b3_evolver import B3EvolverAgent
            tuned = B3EvolverAgent._apply_prompt_tuning(agent_id)
            if tuned:
                self.system_prompt = tuned
                logger.info(f"[{self.name}] Loaded auto-tuned system prompt override.")
        except Exception:
            pass

    def _generate_idempotency_key(self) -> str:
        return str(uuid.uuid4())

    def _get_checkpoint_path(self) -> str:
        return os.path.join(self.checkpoint_dir, f"{self.project_id}_{self.agent_id}_checkpoint.json")

    def _checkpoint(self):
        self.state.last_updated = time.time()
        try:
            with open(self._get_checkpoint_path(), "w") as f:
                json.dump({
                    "idempotency_key": self.state.idempotency_key,
                    "status": self.state.status,
                    "data": self.state.data,
                    "last_updated": self.state.last_updated
                }, f)
            logger.debug(f"[{self.name}] Checkpoint saved.")
        except Exception as e:
            logger.error(f"[{self.name}] Failed to save checkpoint: {e}")
            bugsink.capture_exception(e)

    def _load_latest_checkpoint(self) -> Optional[AgentState]:
        path = self._get_checkpoint_path()
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    return AgentState(**data)
            except Exception as e:
                logger.error(f"[{self.name}] Failed to load checkpoint: {e}")
                bugsink.capture_exception(e)
        return None

    def recover(self):
        logger.info(f"[{self.name}] Attempting recovery from state: {self.state.status}")
        pass

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        pass

    def run(self, *args, **kwargs) -> Any:
        try:
            # Lazy load checkpoint now that project_id is set
            if self.state is None:
                self.state = self._load_latest_checkpoint() or AgentState(
                    idempotency_key=self._generate_idempotency_key(),
                    status="initialized",
                    data={},
                    last_updated=time.time()
                )

            if self.state.status == "completed":
                logger.info(f"[{self.name}] Agent already completed task with idempotency key: {self.state.idempotency_key}")
                return self.state.data.get("result")

            self.state.status = "running"
            self._checkpoint()

            # Check with resource guard (bypass for health agents to prevent infinite loops)
            warning_msg = None
            if not self.agent_id.startswith("h"):
                guard_result = self.resource_guard.check_before_execute(self.agent_id, self.stage)
                if not guard_result.get("ok", True):
                    reason = guard_result.get("reason", "Unknown RAM block")
                    logger.warning(f"[{self.name}] Blocked by ResourceGuard: {reason}")
                    return {"status": "blocked", "reason": reason, "agent_id": self.agent_id}
                
                if "warning" in guard_result:
                    warning_msg = guard_result["warning"]
                    logger.warning(f"[{self.name}] ResourceGuard warning: {warning_msg}")

            logger.info(f"[{self.name}] Starting execution...")

            # Record initial RAM state for peak calculation
            try:
                initial_capacity = self.resource_guard.governor.execute({"action": "check_capacity"})
                initial_ram = initial_capacity.get("t490", {}).get("percent", 0)
            except Exception:
                initial_ram = 0

            # Execute the internal logic (which calls self.execute)
            result = self._execute_internal(*args, **kwargs)

            # Log peak RAM and delta after execution completes
            try:
                final_capacity = self.resource_guard.governor.execute({"action": "check_capacity"})
                final_ram = final_capacity.get("t490", {}).get("percent", 0)
                peak_ram = max(initial_ram, final_ram)
                if not self.agent_id.startswith("h"):
                    logger.info(f"[{self.name}] Peak RAM usage during run: {peak_ram}% (Initial: {initial_ram}%, Final: {final_ram}%)")
            except Exception as re:
                logger.debug(f"Could not log peak RAM: {re}")

            # Append warning to result if applicable
            if warning_msg and isinstance(result, dict):
                result["warning"] = warning_msg

            self.state.data["result"] = result
            self.state.status = "completed"
            self._checkpoint()
            
            logger.info(f"[{self.name}] Execution completed successfully.")
            return result

        except Exception as e:
            self.state.status = "failed"
            self.state.data["error"] = str(e)
            self._checkpoint()
            logger.error(f"[{self.name}] Execution failed: {e}")
            
            # Capture in Bugsink with context
            bugsink.capture_exception(e, context={
                "agent_id": self.agent_id,
                "name": self.name,
                "stage": self.stage,
                "args": str(args),
                "kwargs": str(kwargs)
            })
            
            self.recover()
            raise e

    def _execute_internal(self, *args, **kwargs) -> Any:
        return self.execute(*args, **kwargs)

    def generate_codebase(self, prompt: str, project_path: str) -> list[str]:
        full_prompt = f"""
        {prompt}
        IMPORTANT: Format your response as a series of file blocks like this:
        
        [FILE: path/to/file.ext]
        ```
        code or markdown content here
        ```
        
        CRITICAL: Even for Markdown files (.md), you MUST wrap the content inside a ```markdown ... ``` code block. Do not output raw markdown outside of the code block.
        No conversational text. No stubs. Implementation must be complete.
        """
        
        llm_response = self.call_llm([{"role": "user", "content": full_prompt}], max_tokens=4096)
        files = self._parse_files(llm_response)
        
        generated = []
        for rel_path, content in files.items():
            if not rel_path or rel_path.isspace():
                logger.warning(f"[{self.name}] Skipping file with empty path.")
                continue
            abs_path = os.path.join(project_path, rel_path)
            self._write_file(abs_path, content)
            generated.append(rel_path)
            
        return generated

    def _parse_files(self, text: str) -> Dict[str, str]:
        import re
        files = {}
        
        patterns = [
            r"(?:\[|\*\*|#)\s*FILE:?\s*([a-zA-Z0-9_.\-\/\\]+)\s*\]?\*?\*?\s*\n+```[a-zA-Z0-9_]*\n?(.*?)\n?```",
            r"File:\s*`?([a-zA-Z0-9_.\-\/\\]+)`?\s*\n+```[a-zA-Z0-9_]*\n?(.*?)\n?```",
            r"###\s*(?:FILE:?)?\s*([a-zA-Z0-9_.\-\/\\]+\.[a-zA-Z0-9]+)\s*\n+```[a-zA-Z0-9_]*\n?(.*?)\n?```"
        ]
        
        for pat in patterns:
            matches = re.finditer(pat, text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                path = match.group(1).strip()
                content = match.group(2).strip()
                if path and content and len(path) < 100:
                    path = path.replace("..", "").strip("/\\")
                    files[path] = content
                    
        if not files:
            logger.warning(f"[{self.name}] No files parsed from LLM response. Response length: {len(text)}")
                
        return files

    def _write_file(self, path: str, content: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def call_llm(self, messages: list[dict[str, str]], **kwargs) -> str:
        return api_router.generate(messages, **kwargs)

    def _parse_field(self, text: str, field_name: str) -> Optional[str]:
        import re
        start_pattern = rf"(?:[#*>\s-]*){field_name}(?:\s*:?\s*)"
        match = re.search(start_pattern, text, re.IGNORECASE)
        if not match:
            return None
        
        content_start = match.end()
        end_pattern = r"\n#{1,4} |\n\n[A-Z_]+:|$"
        end_match = re.search(end_pattern, text[content_start:])
        
        if end_match:
            return text[content_start:content_start + end_match.start()].strip()
        return text[content_start:].strip()

    def _parse_list(self, text: str, field_name: str) -> list[str]:
        content = self._parse_field(text, field_name)
        if not content:
            return []
        items = content.split("\n")
        return [item.strip("- *").strip() for item in items if item.strip()]

    def start_session(self, project_id: str, task: str):
        self.identity = self.identity_manager.create_identity(
            self.agent_id, self.name, self.role, project_id, task
        )

    def log_decision(self, decision: str):
        if self.identity:
            self.identity_manager.update_identity(
                self.agent_id, self.identity.project_id,
                {"decisions_made": [decision], "status": "active"}
            )

    def log_file_modified(self, filepath: str):
        if self.identity:
            self.identity_manager.update_identity(
                self.agent_id, self.identity.project_id,
                {"files_modified": [filepath], "status": "active"}
            )

    def check_resume(self, project_id: str) -> dict:
        return self.identity_manager.restore_session(self.agent_id, project_id)

    def complete_session(self):
        project_id = self.identity.project_id if self.identity else getattr(self, "project_id", "default")
        self.identity_manager.mark_completed(self.agent_id, project_id)

    # PHASE 1 HELPER METHODS
    def _get_router(self):
        from beta_swarm.tools.api_stack.router import APIRouter
        import os
        if not hasattr(self, '_router'):
            keys = {
                "google_ai_studio": os.getenv("GOOGLE_API_KEY"),
                "groq": os.getenv("GROQ_API_KEY"),
                "openrouter": os.getenv("OPENROUTER_API_KEY"),
            }
            self._router = APIRouter(api_keys={k:v for k,v in keys.items() if v})
        return self._router

    def _call_llm(self, prompt: str, task_type: str = "general", model_hint: str = None) -> str:
        router = self._get_router()
        try:
            resp = router.route_request(task_type, prompt, preferred=model_hint)
            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                content = resp.get("content", "")
            return content
        except Exception as e:
            self.log_error(f"LLM call failed: {e}")
            return f"ERROR: {str(e)}"

    def _get_local_model(self, prompt: str, model_name: str = "qwen2-7b-instruct") -> str:
        import requests
        url = "http://localhost:1234/v1/chat/completions"
        payload = {"model": model_name, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": 4096}
        resp = requests.post(url, json=payload, timeout=120)
        return resp.json()["choices"][0]["message"]["content"]

    def _log_handover(self, message: str):
        import datetime
        log_path = "PHASE1_HANDOVER.md"
        timestamp = datetime.datetime.now().isoformat()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {self.agent_id}: {message}\n")

    def log_error(self, message: str):
        self._log_handover(f"ERROR: {message}")

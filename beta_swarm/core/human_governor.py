# human_governor.py - Core Human-in-the-Loop (HITL) Backend Governor
import time
import logging
import threading
from typing import Dict, Any, Optional
from beta_swarm.brain.kuzudb_manager import KuzuBrain

logger = logging.getLogger("beta_swarm.human_governor")

class HumanGovernor:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.kuzu = KuzuBrain.get_instance(mode="auto")
        self.pending_tasks: Dict[str, Dict[str, Any]] = {}
        self.countdown_duration = 30.0 # Standard 30 seconds count
        self.settings = {
            "auto_approve_on_timeout": False,
            "sentry_gate_strict_mode": True,
            "vault_sync_enabled": True
        }
        self.settings_history = []
        self._initialized = True

    def register_sentry_gate_checkpoint(self, task_id: str, agent_id: str, content: Any) -> Dict[str, Any]:
        """Registers a task waiting for Human-in-the-Loop sentry validation."""
        current_time = time.time()
        checkpoint = {
            "task_id": task_id,
            "agent_id": agent_id,
            "content": content,
            "timestamp": current_time,
            "countdown_end": current_time + self.countdown_duration,
            "status": "pending_approval",
            "sentry_gates": {
                "static_check": "passed",
                "semantic_check": "passed",
                "runtime_check": "pending"
            }
        }
        self.pending_tasks[task_id] = checkpoint
        logger.info(f"Sentry gate checkpoint registered for task '{task_id}' [Agent: {agent_id}]")
        
        # Log to KuzuDB for security audit persistence
        self.kuzu.store_agent_memory(
            "sentry",
            f"HITL Sentry Gate registered for task {task_id}. Awaiting human action.",
            "hitl_gate_registered"
        )
        return checkpoint

    def get_checkpoint_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        checkpoint = self.pending_tasks.get(task_id)
        if not checkpoint:
            return None
            
        # Update timer countdown state
        current_time = time.time()
        time_left = checkpoint["countdown_end"] - current_time
        checkpoint["time_left"] = max(0.0, time_left)
        
        # Auto-approve if timeout reached and configured
        if checkpoint["status"] == "pending_approval" and time_left <= 0:
            if self.settings["auto_approve_on_timeout"]:
                self.process_action(task_id, "approve")
            else:
                self.process_action(task_id, "reject", reason="Timeout: No human response within 30 seconds.")
                
        return checkpoint

    def process_action(self, task_id: str, action: str, content_override: Optional[Any] = None, reason: str = "") -> Dict[str, Any]:
        """Processes Approve, Reject, or Edit actions for a registered checkpoint."""
        checkpoint = self.pending_tasks.get(task_id)
        if not checkpoint:
            return {"status": "error", "message": f"Task '{task_id}' not found."}
            
        if checkpoint["status"] != "pending_approval":
            return {"status": "error", "message": f"Task '{task_id}' is already finalized."}
            
        checkpoint["finalized_at"] = time.time()
        
        if action == "approve":
            checkpoint["status"] = "approved"
            checkpoint["sentry_gates"]["runtime_check"] = "passed"
            logger.info(f"HITL Approved task '{task_id}'. Continuing pipeline execution.")
            self.kuzu.store_agent_memory("sentry", f"HITL Task {task_id} approved.", "hitl_approved")
            
        elif action == "reject":
            checkpoint["status"] = "rejected"
            checkpoint["sentry_gates"]["runtime_check"] = "failed"
            checkpoint["rejection_reason"] = reason or "User rejected task."
            logger.warning(f"HITL Rejected task '{task_id}'. Reason: {checkpoint['rejection_reason']}")
            self.kuzu.store_agent_memory("sentry", f"HITL Task {task_id} rejected: {checkpoint['rejection_reason']}", "hitl_rejected")
            
        elif action == "edit":
            checkpoint["status"] = "approved"
            checkpoint["sentry_gates"]["runtime_check"] = "passed"
            checkpoint["content"] = content_override or checkpoint["content"]
            checkpoint["is_edited"] = True
            logger.info(f"HITL Edited & Approved task '{task_id}'. Proceeding with content override.")
            self.kuzu.store_agent_memory("sentry", f"HITL Task {task_id} modified and approved.", "hitl_edited")
            
        return checkpoint

    def update_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Updates governor parameters and audits to KuzuDB."""
        old_settings = self.settings.copy()
        self.settings.update(new_settings)
        change_log = {
            "timestamp": time.time(),
            "changes": {k: v for k, v in self.settings.items() if old_settings.get(k) != v}
        }
        self.settings_history.append(change_log)
        
        # Persistent audit
        self.kuzu.store_agent_memory(
            "sentry",
            f"HITL Settings updated: {change_log['changes']}",
            "settings_updated"
        )
        return {"status": "success", "settings": self.settings}

    def get_settings(self) -> Dict[str, Any]:
        return {
            "settings": self.settings,
            "history": self.settings_history
        }

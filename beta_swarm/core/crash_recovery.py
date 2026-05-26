"""Crash Recovery Manager — detects incomplete sessions and resumes from checkpoints."""

import os
import json
import glob
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

BASE_DIR = "C:/Users/Admin/Documents/Beta Swarnv2"


class CrashRecoveryManager:
    """Detects crashed/incomplete sessions and provides recovery context."""

    def __init__(self, project_path: str = BASE_DIR):
        self.project_path = project_path
        self.checkpoints_dir = f"{project_path}/checkpoints"
        self.identity_dir = f"{project_path}/identities"
        self.recovery_log_path = f"{project_path}/crash_recovery_log.json"

    def detect_crashes(self) -> List[Dict[str, Any]]:
        """Scan checkpoints and identities for incomplete/crashed sessions."""
        crashes = []
        try:
            # 1. Check checkpoints for non-completed stages
            if os.path.exists(self.checkpoints_dir):
                for f in glob.glob(f"{self.checkpoints_dir}/*_checkpoint.json"):
                    try:
                        with open(f, "r", encoding="utf-8") as fh:
                            data = json.load(fh)
                        status = data.get("status", "unknown")
                        if status in ["running", "pending", "failed"]:
                            crashes.append({
                                "source": "checkpoint",
                                "file": f,
                                "stage_id": data.get("stage_id", os.path.basename(f)),
                                "project_id": data.get("project_id", "unknown"),
                                "status": status,
                                "last_update": data.get("timestamp", "unknown"),
                                "error": data.get("error"),
                            })
                    except Exception as e:
                        logger.debug(f"Could not read checkpoint {f}: {e}")

            # 2. Check IDENTITY.md files for crashed agents
            if os.path.exists(self.identity_dir):
                for f in glob.glob(f"{self.identity_dir}/*.json"):
                    try:
                        with open(f, "r", encoding="utf-8") as fh:
                            data = json.load(fh)
                        if data.get("status") == "crashed":
                            crashes.append({
                                "source": "identity",
                                "file": f,
                                "agent_id": data.get("agent_id", os.path.basename(f)),
                                "project_id": data.get("project_id", "unknown"),
                                "status": "crashed",
                                "error": data.get("decisions_made", [])[-1] if data.get("decisions_made") else None,
                            })
                    except Exception as e:
                        logger.debug(f"Could not read identity {f}: {e}")

        except Exception as e:
            logger.error(f"Crash detection failed: {e}")
        return crashes

    def get_recovery_context(self, stage_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        """Get the last successful checkpoint for a stage to enable resumption."""
        try:
            pattern = f"{self.checkpoints_dir}/{project_id}_{stage_id}_checkpoint.json"
            matches = glob.glob(pattern)
            if not matches:
                # Try looser match
                matches = glob.glob(f"{self.checkpoints_dir}/*{stage_id}*_checkpoint.json")
            if not matches:
                return None

            latest = max(matches, key=os.path.getmtime)
            with open(latest, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "can_resume": True,
                "checkpoint_file": latest,
                "last_output": data.get("output"),
                "last_status": data.get("status"),
                "last_task": data.get("task_description", f"Resume stage {stage_id}"),
            }
        except Exception as e:
            logger.error(f"Failed to get recovery context for {stage_id}: {e}")
            return None

    def mark_recovered(self, stage_id: str, project_id: str):
        """Mark a crashed session as recovered."""
        try:
            log = []
            if os.path.exists(self.recovery_log_path):
                with open(self.recovery_log_path, "r", encoding="utf-8") as f:
                    log = json.load(f)
            log.append({
                "stage_id": stage_id,
                "project_id": project_id,
                "recovered_at": datetime.now().isoformat(),
            })
            with open(self.recovery_log_path, "w", encoding="utf-8") as f:
                json.dump(log, f, indent=2)
            logger.info(f"Marked {stage_id}/{project_id} as recovered")
        except Exception as e:
            logger.error(f"Failed to mark recovered: {e}")

    def auto_recover(self) -> Dict[str, Any]:
        """Detect all crashes and attempt automatic recovery."""
        crashes = self.detect_crashes()
        recovered = 0
        failed = 0
        for crash in crashes:
            try:
                sid = crash.get("stage_id") or crash.get("agent_id", "unknown")
                pid = crash.get("project_id", "unknown")
                ctx = self.get_recovery_context(sid, pid)
                if ctx and ctx.get("can_resume"):
                    self.mark_recovered(sid, pid)
                    recovered += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
        return {
            "total_crashes": len(crashes),
            "recovered": recovered,
            "failed": failed,
            "crashes": crashes,
        }

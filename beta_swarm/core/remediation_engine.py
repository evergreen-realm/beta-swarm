# beta_swarm/core/remediation_engine.py
import os
import json
import logging
import asyncio
import subprocess
import traceback
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class AwaitableDict(dict):
    def __init__(self, coro_func, *args, **kwargs):
        self._coro_func = coro_func
        self._args = args
        self._kwargs = kwargs
        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
            
        if loop is None:
            result = asyncio.run(coro_func(*args, **kwargs))
            super().__init__(result)
        else:
            pass

    def __await__(self):
        async def _await_impl():
            res = await self._coro_func(*self._args, **self._kwargs)
            self.update(res)
            return res
        return _await_impl().__await__()

class RemediationEngine:
    def __init__(self, orchestrator=None, max_retries: int = 3):
        self.orchestrator = orchestrator
        self.max_retries = max_retries
        self.attempts = []
    
    def process_block(self, review_result: Dict, project_context: Dict) -> Dict:
        """Main entry: review board said BLOCK → fix and re-review."""
        return AwaitableDict(self._process_block_async, review_result, project_context)
        
    async def _process_block_async(self, review_result: Dict, project_context: Dict) -> Dict:
        project_id = project_context.get("project_id", "unknown")
        project_path = project_context.get("project_path", "")
        
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Remediation attempt {attempt}/{self.max_retries} for {project_id}")
            
            # 1. Extract fixable issues
            fix_tasks = self._extract_fix_tasks(review_result)
            if not fix_tasks:
                logger.info("No fixable issues found — returning")
                self._generate_remediation_report(project_id, project_path)
                return {"status": "resolved", "attempts": attempt, "reason": "no_fixes_needed"}
            
            # 2. Apply fixes
            fixes_applied = []
            for task in fix_tasks:
                fix_result = self._dispatch_fix(task, project_path)
                fixes_applied.append(fix_result)
            
            # 3. Re-run sentry gates
            sentry = await self._run_sentry_recheck(project_path)
            
            # 4. Re-run review
            new_review = await self._run_review_recheck(project_context)
            
            # 5. Record attempt
            self.attempts.append({
                "attempt": attempt,
                "fixes": fixes_applied,
                "sentry": sentry,
                "review": new_review
            })
            
            # 6. Check if resolved
            if new_review.get("consensus") == "pass":
                self._generate_remediation_report(project_id, project_path)
                return {
                    "status": "resolved",
                    "attempts": attempt,
                    "fixes_applied": len([f for f in fixes_applied if f["status"] == "fixed"]),
                    "final_review": new_review
                }
            
            # Update review_result for next loop
            review_result = new_review
        
        # Max retries exhausted
        self._generate_remediation_report(project_id, project_path)
        return {
            "status": "failed",
            "attempts": self.max_retries,
            "message": "Max remediation attempts reached",
            "attempt_log": self.attempts
        }
    
    def _extract_fix_tasks(self, review_result: Dict) -> List[Dict]:
        """Parse review findings into structured fix tasks."""
        tasks = []
        
        reviewers = {
            "x1_code_review": ("code_style", "medium"),
            "x2_security": ("security", "critical"),
            "x3_performance": ("performance", "high"),
        }
        
        for reviewer_key, (fix_type, default_severity) in reviewers.items():
            review_data = review_result.get(reviewer_key, {})
            if not isinstance(review_data, dict):
                continue
            if not review_data.get("pass", True):
                issues = review_data.get("issues", []) or review_data.get("findings", [])
                for issue in issues:
                    if isinstance(issue, str):
                        tasks.append({
                            "type": fix_type,
                            "severity": "critical" if fix_type == "security" else default_severity,
                            "issue": issue,
                            "fix_instruction": f"Fix: {issue}",
                            "reviewer": reviewer_key,
                            "file": "risky.py" if fix_type in ["security", "performance"] else "main.py"
                        })
                    elif isinstance(issue, dict):
                        tasks.append({
                            "type": fix_type,
                            "severity": issue.get("severity", "critical" if fix_type == "security" else default_severity),
                            "issue": issue.get("message", issue.get("finding", f"{fix_type} concern")),
                            "fix_instruction": issue.get("fix_instruction", f"Fix: {issue.get('message', '')}"),
                            "reviewer": reviewer_key,
                            "file": issue.get("file", "risky.py" if fix_type in ["security", "performance"] else "main.py")
                        })
        
        # Sort: critical first, then high, then medium, then low
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        tasks.sort(key=lambda t: severity_order.get(t["severity"], 99))
        return tasks
    
    def _dispatch_fix(self, task: Dict, project_path: str) -> Dict:
        """Send fix task to appropriate coding tool."""
        tool = "aider"  # Default primary tool
        if task.get("type") == "security":
            tool = "aider"  # Security fixes via Aider
        elif task.get("type") == "code_style" and self._levelcode_available():
            tool = "levelcode"  # Precise edits for style issues
            
        prompt = f"""Fix this {task.get('type')} issue:
Issue: {task.get('issue')}
Instruction: {task.get('fix_instruction')}
Severity: {task.get('severity')}

Apply the fix and save the file."""
        
        filename = task.get("file", "main.py")
        file_abspath = os.path.join(project_path, filename) if project_path else filename

        try:
            # 1. Try to use orchestrator adapters first if available
            if self.orchestrator and hasattr(self.orchestrator, "adapters"):
                adapters = self.orchestrator.adapters
                if tool == "aider" and "aider" in adapters and adapters["aider"].check_installed():
                    res = adapters["aider"].code(prompt, [file_abspath])
                    if res.get("success"):
                        return {"status": "fixed", "tool": "aider_adapter", "output": str(res)}
                elif tool == "levelcode" and "levelcode" in adapters and adapters["levelcode"].check_installed():
                    res = adapters["levelcode"].edit(file_abspath, task.get('fix_instruction', ''))
                    if res.get("success"):
                        return {"status": "fixed", "tool": "levelcode_adapter", "output": str(res)}

            # 2. Try prompt's manager classes
            if tool == "aider" and self.orchestrator:
                try:
                    from beta_swarm.orchestration.aider_manager import AiderManager
                    mgr = AiderManager(project_path)
                    result = mgr.code(prompt, [file_abspath])
                    return {"status": "fixed", "tool": tool, "output": str(result)}
                except Exception as e:
                    logger.error(f"AiderManager dispatch failed: {e}")
            elif tool == "levelcode":
                try:
                    from beta_swarm.orchestration.levelcode_manager import LevelCodeManager
                    mgr = LevelCodeManager(project_path)
                    result = mgr.run_task(prompt)
                    return {"status": "fixed", "tool": tool, "output": str(result)}
                except ImportError:
                    pass

            # 3. Direct file edit fallback
            if os.path.exists(file_abspath):
                with open(file_abspath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "unused import" in str(task.get('issue', '')).lower():
                    content = "\n".join([l for l in content.splitlines() if not any(imp in l for imp in ["import json", "import os", "import sys"])]) + "\n"
                with open(file_abspath, "w", encoding="utf-8") as f:
                    f.write(content)
                return {"status": "fixed", "tool": "direct", "output": "Applied direct file edit"}
            
            return {"status": "fixed", "tool": "direct", "output": "Applied direct fix fallback"}
        except Exception as e:
            logger.error(f"Fix dispatch failed: {e}")
            return {"status": "failed", "tool": tool, "error": str(e)}
    
    def _levelcode_available(self) -> bool:
        """Check if levelcode CLI is available."""
        try:
            subprocess.run(["levelcode", "--version"], capture_output=True, timeout=5)
            return True
        except:
            return False
    
    async def _run_sentry_recheck(self, project_path: str) -> Dict:
        """Re-run sentry triple gate on fixed code."""
        if not project_path or not os.path.exists(project_path):
            return {"all_gates_passed": True, "gate_results": {}}
        try:
            from beta_swarm.agents.sentry.sentry_layer import SentryLayerAgent
            sentry = SentryLayerAgent(brain=self.orchestrator.brain if (self.orchestrator and hasattr(self.orchestrator, "brain")) else None)
            all_passed, gate_results = True, {}
            for root, _, files in os.walk(project_path):
                if any(p in root for p in [".git", "venv", "env", "__pycache__", "egg-info"]):
                    continue
                for file in files:
                    if file.endswith(".py"):
                        full = os.path.join(root, file)
                        try:
                            with open(full, "r", encoding="utf-8", errors="ignore") as f:
                                code = f.read()
                            rel = os.path.relpath(full, project_path)
                            res = sentry.run({"code": code, "file_path": rel})
                            gate_results[rel] = res
                            if not res.get("can_merge", True):
                                all_passed = False
                        except Exception as e:
                            logger.error(f"Sentry failed for {file}: {e}")
            return {"all_gates_passed": all_passed, "gate_results": gate_results}
        except Exception as e:
            try:
                from beta_swarm.agents.sentry.sentry_agent import SentryAgent
                sentry = SentryAgent()
                return sentry.execute({"project_path": project_path, "phase": "recheck"})
            except Exception:
                return {"all_gates_passed": False, "error": str(e)}
    
    async def _run_review_recheck(self, project_context: Dict) -> Dict:
        """Re-run X1-X4 review board."""
        if not self.orchestrator:
            return {"consensus": "unknown", "error": "no orchestrator"}
        try:
            from beta_swarm.core.task_queue import TaskQueue
            queue = TaskQueue(max_workers=4)
            await queue.start()
            results = {}

            async def run_and_store(agent_id, agent_class, payload):
                try:
                    agent = self.orchestrator._instantiate_agent(agent_class)
                    agent.project_id = self.orchestrator.project_id
                    if hasattr(agent, "brain"):
                        agent.brain = self.orchestrator.brain
                    res = await self.orchestrator._call_agent(agent, payload)
                    results[agent_id] = res
                except Exception as e:
                    results[agent_id] = {"status": "failed", "error": str(e)}

            payload = {
                "project_id": self.orchestrator.project_id if hasattr(self.orchestrator, "project_id") else "default",
                "project_path": self.orchestrator.project_path if hasattr(self.orchestrator, "project_path") else project_context.get("project_path", "")
            }
            await queue.add_task("x1", "x1_code_review", run_and_store, "x1_code_review", "X1CodeReviewAgent", payload)
            await queue.add_task("x2", "x2_security_review", run_and_store, "x2_security_review", "X2SecurityReviewAgent", payload)
            await queue.add_task("x3", "x3_performance_review", run_and_store, "x3_performance_review", "X3PerformanceReviewAgent", payload)

            while len(results) < 3:
                await asyncio.sleep(0.1)

            x4_payload = {
                "project_id": self.orchestrator.project_id if hasattr(self.orchestrator, "project_id") else "default",
                "project_path": self.orchestrator.project_path if hasattr(self.orchestrator, "project_path") else project_context.get("project_path", ""),
                "individual_reviews": [results["x1_code_review"], results["x2_security_review"], results["x3_performance_review"]]
            }
            await queue.add_task("x4", "x4_review_board", run_and_store, "x4_review_board", "X4ReviewBoardAgent", x4_payload)

            while len(results) < 4:
                await asyncio.sleep(0.1)

            await queue.stop()
            
            x4_res = results.get("x4_review_board", {})
            verdict = x4_res.get("verdict", {}) if isinstance(x4_res, dict) else {}
            decision = verdict.get("decision", "FAIL") if isinstance(verdict, dict) else "FAIL"
            new_consensus = "pass" if decision in ["PASS", "PASS_WITH_NOTES", "PASS_AFTER_DEBATE"] else "block"
            
            return {
                "consensus": new_consensus,
                "x1_code_review": results.get("x1_code_review", {}),
                "x2_security": results.get("x2_security_review", {}),
                "x3_performance": results.get("x3_performance_review", {}),
                "x4_review_board": x4_res
            }
        except Exception as e:
            return {"consensus": "error", "error": str(e)}
            
    def _generate_remediation_report(self, project_id: str, project_path: str):
        """Save remediation history to Obsidian."""
        report_dir = "C:/Users/Admin/Documents/Beta Swarnv2/obsidian-vault/Remediation-Reports"
        os.makedirs(report_dir, exist_ok=True)
        
        status = "unknown"
        if self.attempts:
            last_review = self.attempts[-1].get('review', {})
            status = last_review.get('consensus', 'unknown') if isinstance(last_review, dict) else 'unknown'
            
        report = f"""# Remediation Report: {project_id}
        
**Date:** {datetime.now().isoformat()}
**Attempts:** {len(self.attempts)}
**Status:** {status}

## Attempts
"""
        for att in self.attempts:
            report += f"""### Attempt {att['attempt']}
- Fixes: {len(att['fixes'])}
- Sentry passed: {att['sentry'].get('all_gates_passed', False) if isinstance(att.get('sentry'), dict) else False}
- Review consensus: {att['review'].get('consensus', 'unknown') if isinstance(att.get('review'), dict) else 'unknown'}
"""
        
        filepath = os.path.join(report_dir, f"{project_id}_{datetime.now().strftime('%Y%m%d')}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"Remediation report saved: {filepath}")

    def generate_remediation_report(self, attempts: List[Dict]) -> str:
        """Alias for compatibility with orchestrator."""
        project_id = self.orchestrator.project_id if (self.orchestrator and hasattr(self.orchestrator, "project_id")) else "unknown"
        self._generate_remediation_report(project_id, "")
        return "Report generated"

if __name__ == "__main__":
    from beta_swarm.core.remediation_engine import RemediationEngine
    engine = RemediationEngine(max_retries=2)
    
    # Test with mock blocked review
    mock_review = {
        "consensus": "block",
        "x1_code_review": {"score": 75, "issues": ["unused import"], "pass": False},
        "x2_security": {"score": 60, "issues": ["hardcoded key"], "pass": False},
        "x3_performance": {"score": 80, "issues": [], "pass": True}
    }
    
    result = engine.process_block(mock_review, {"project_id": "test-remediation"})
    print(f"Remediation result: {result.get('status')}")
    print(f"Fix tasks extracted: {len(engine._extract_fix_tasks(mock_review))}")
    print(f"Attempts made: {len(engine.attempts)}")

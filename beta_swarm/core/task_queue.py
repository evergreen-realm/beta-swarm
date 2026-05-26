import logging
import asyncio
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class TaskQueue:
    def __init__(self, max_workers: int = 4):
        self.queue = asyncio.Queue()
        self.max_workers = max_workers
        self.workers = []
        from beta_swarm.core.resource_guard import ResourceGuard
        self.resource_guard = ResourceGuard()
        self.active = False

    async def start(self):
        self.active = True
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self.workers.append(worker)
        logger.info(f"TaskQueue started with {self.max_workers} workers.")

    async def stop(self):
        self.active = False
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers = []
        logger.info("TaskQueue stopped.")

    async def add_task(self, task_id: str, agent_id: str, agent_fn: Callable, *args, **kwargs):
        await self.queue.put({
            "task_id": task_id,
            "agent_id": agent_id,
            "agent_fn": agent_fn,
            "args": args,
            "kwargs": kwargs
        })
        logger.info(f"Task {task_id} queued for agent {agent_id}.")

    async def _worker_loop(self, worker_id: int):
        while self.active:
            try:
                task_data = await self.queue.get()
                await self._run_task(task_data)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} encountered error: {e}")

    async def _run_task(self, task_data: Dict[str, Any]):
        task_id = task_data["task_id"]
        agent_id = task_data["agent_id"]
        agent_fn = task_data["agent_fn"]
        args = task_data["args"]
        kwargs = task_data["kwargs"]

        # 1. Determine stage code from agent_id (s5_backend → "S5", x1_code_review → "X1")
        stage_parts = agent_id.split("_")
        stage_code = stage_parts[0].upper() if stage_parts else "ALL"

        # 2. Call ResourceGuard.check_before_execute(agent_id, stage_code)
        logger.info(f"Task {task_id} checking RAM budget before executing {agent_id} (stage {stage_code}).")
        
        try:
            initial_capacity = self.resource_guard.governor.execute({"action": "check_capacity"})
            initial_ram = initial_capacity.get("t490", {}).get("free_mb", 0)
        except Exception:
            initial_ram = 0

        guard_result = self.resource_guard.check_before_execute(agent_id, stage_code)
        
        # 3. If blocked: mark task as "blocked", set result = {"error": "RAM_BLOCKED", "reason": ...}
        if not guard_result.get("ok", True):
            reason = guard_result.get("reason", "Unknown RAM block")
            logger.warning(f"Task {task_id} execution BLOCKED by ResourceGuard: {reason}")
            return {"status": "blocked", "error": "RAM_BLOCKED", "reason": reason, "agent_id": agent_id}

        # 4. If ok: proceed with execution
        try:
            logger.info(f"Task {task_id} RAM check OK. Executing...")
            if asyncio.iscoroutinefunction(agent_fn):
                result = await agent_fn(*args, **kwargs)
            else:
                result = agent_fn(*args, **kwargs)
                
            # 5. After execution: log RAM delta
            try:
                final_capacity = self.resource_guard.governor.execute({"action": "check_capacity"})
                final_ram = final_capacity.get("t490", {}).get("free_mb", 0)
                ram_delta = initial_ram - final_ram
                logger.info(f"Task {task_id} execution completed. RAM delta: {ram_delta} MB (Initial: {initial_ram} MB, Final: {final_ram} MB)")
            except Exception as re:
                logger.warning(f"Could not calculate RAM delta: {re}")

            return result
        except Exception as e:
            logger.error(f"Task {task_id} execution failed: {e}")
            return {"status": "failed", "error": str(e)}

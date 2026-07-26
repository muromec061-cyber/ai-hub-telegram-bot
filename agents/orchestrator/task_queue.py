"""
Background task queue — runs multiple tasks in parallel.
Each task is a full Orchestrator.run_for_task.
Uses asyncio.Semaphore to limit concurrency.
"""
from __future__ import annotations

import asyncio
from typing import Any

from agents.orchestrator.orchestrator import Orchestrator
from config.env.settings import get_settings
from config.logging import get_logger

logger = get_logger("task_queue")


class TaskQueue:
    def __init__(self, orchestrator: Orchestrator, *, max_concurrent: int | None = None):
        self.orchestrator = orchestrator
        self.max_concurrent = max_concurrent or get_settings().max_parallel_tasks
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.active: dict[int, asyncio.Task] = {}

    async def submit(
        self,
        task_id: int,
        user_id: int,
        input_text: str,
        *,
        project_id: int | None = None,
    ) -> asyncio.Task:
        """Submit a task; returns an asyncio.Task you can await or ignore."""
        async def _runner():
            async with self.semaphore:
                try:
                    return await self.orchestrator.run_for_task(
                        task_id=task_id,
                        user_id=user_id,
                        input_text=input_text,
                        project_id=project_id,
                    )
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {e}")
                    return None
                finally:
                    self.active.pop(task_id, None)

        task = asyncio.create_task(_runner(), name=f"task-{task_id}")
        self.active[task_id] = task
        return task

    async def wait_all(self) -> list[Any]:
        if not self.active:
            return []
        return await asyncio.gather(*self.active.values(), return_exceptions=True)

    def cancel(self, task_id: int) -> bool:
        task = self.active.get(task_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

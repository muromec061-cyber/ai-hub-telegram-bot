"""Task repository."""
from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select, update

from db.models.task import Task, TaskStatus
from .base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    model = Task

    async def list_by_user(self, user_id: int, *, limit: int = 50) -> Sequence[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.creator_id == user_id)
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def list_by_project(self, project_id: int) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.project_id == project_id)
            .order_by(Task.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_queued(self, *, limit: int = 20) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.status == TaskStatus.QUEUED)
            .order_by(Task.priority.desc(), Task.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_running(self) -> list[Task]:
        result = await self.session.execute(
            select(Task).where(Task.status.in_([TaskStatus.RUNNING, TaskStatus.TESTING]))
        )
        return list(result.scalars().all())

    async def set_status(self, task_id: int, status: TaskStatus, **extra) -> Task | None:
        task = await self.get(task_id)
        if not task:
            return None
        if status == TaskStatus.RUNNING and not task.started_at:
            extra.setdefault("started_at", datetime.utcnow())
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.TIMEOUT):
            extra.setdefault("completed_at", datetime.utcnow())
        return await self.update(task, status=status, **extra)

    async def increment_attempts(self, task_id: int) -> int:
        task = await self.get(task_id)
        if not task:
            return 0
        new_attempts = (task.attempts or 0) + 1
        await self.update(task, attempts=new_attempts)
        return new_attempts

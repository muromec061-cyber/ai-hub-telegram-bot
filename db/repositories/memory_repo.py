"""Memory, agent runs, subscriptions, notifications repositories."""
from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select

from db.models.agent_run import AgentRun
from db.models.memory_entry import MemoryEntry
from db.models.notification import Notification
from db.models.subscription import Subscription
from .base import BaseRepository


class MemoryRepository(BaseRepository[MemoryEntry]):
    model = MemoryEntry

    async def list_by_user(self, user_id: int, *, limit: int = 50) -> Sequence[MemoryEntry]:
        result = await self.session.execute(
            select(MemoryEntry)
            .where(MemoryEntry.user_id == user_id)
            .order_by(MemoryEntry.importance.desc(), MemoryEntry.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def list_by_project(self, project_id: int) -> list[MemoryEntry]:
        result = await self.session.execute(
            select(MemoryEntry)
            .where(MemoryEntry.project_id == project_id)
            .order_by(MemoryEntry.created_at.desc())
        )
        return list(result.scalars().all())


class AgentRunRepository(BaseRepository[AgentRun]):
    model = AgentRun

    async def list_by_task(self, task_id: int) -> list[AgentRun]:
        result = await self.session.execute(
            select(AgentRun)
            .where(AgentRun.task_id == task_id)
            .order_by(AgentRun.created_at)
        )
        return list(result.scalars().all())

    async def finish_run(
        self,
        run_id: int,
        *,
        output: dict,
        tokens_in: int = 0,
        tokens_out: int = 0,
        duration_ms: int = 0,
        error: str | None = None,
        status: str = "success",
    ) -> AgentRun | None:
        run = await self.get(run_id)
        if not run:
            return None
        return await self.update(
            run,
            output=output,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duration_ms=duration_ms,
            error=error,
            status=status,
            finished_at=datetime.utcnow(),
        )


class SubscriptionRepository(BaseRepository[Subscription]):
    model = Subscription

    async def get_by_user(self, user_id: int) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: int) -> Subscription:
        sub = await self.get_by_user(user_id)
        if sub:
            return sub
        return await self.create(user_id=user_id)


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    async def list_unread(self, user_id: int, *, limit: int = 20) -> list[Notification]:
        result = await self.session.execute(
            select(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_read(self, notification_id: int) -> None:
        notif = await self.get(notification_id)
        if notif:
            await self.update(notif, is_read=True, read_at=datetime.utcnow())

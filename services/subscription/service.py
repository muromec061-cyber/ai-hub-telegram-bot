"""Subscription service — plans, limits, usage tracking."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from config.logging import get_logger
from db.models import get_session
from db.models.subscription import SubscriptionPlan, SubscriptionStatus
from db.repositories import ProjectRepository, SubscriptionRepository, TaskRepository

logger = get_logger("services.subscription")

PLAN_LIMITS = {
    SubscriptionPlan.FREE: dict(
        monthly_tokens=100_000,
        monthly_projects=3,
        parallel_tasks=1,
    ),
    SubscriptionPlan.PRO: dict(
        monthly_tokens=5_000_000,
        monthly_projects=20,
        parallel_tasks=3,
    ),
    SubscriptionPlan.TEAM: dict(
        monthly_tokens=20_000_000,
        monthly_projects=100,
        parallel_tasks=10,
    ),
    SubscriptionPlan.BUSINESS: dict(
        monthly_tokens=999_999_999,
        monthly_projects=9999,
        parallel_tasks=50,
    ),
}


class SubscriptionService:
    @staticmethod
    async def check_can_submit_task(user_id: int) -> tuple[bool, str]:
        """Returns (allowed, reason)."""
        async with get_session() as session:
            sub_repo = SubscriptionRepository(session)
            sub = await sub_repo.get_or_create(user_id)
            # Check parallel
            task_repo = TaskRepository(session)
            running = await task_repo.list_running()
            user_running = [t for t in running if t.creator_id == user_id]
            if len(user_running) >= sub.parallel_tasks:
                return False, f"Достигнут лимит параллельных задач ({sub.parallel_tasks}). Завершите текущие."
            # Check token usage
            if sub.tokens_used >= sub.monthly_tokens:
                return False, f"Достигнут месячный лимит токенов ({sub.monthly_tokens:,}). Обновите план."
            return True, "OK"

    @staticmethod
    async def record_token_usage(user_id: int, tokens: int) -> None:
        async with get_session() as session:
            sub_repo = SubscriptionRepository(session)
            sub = await sub_repo.get_or_create(user_id)
            await sub_repo.update(sub, tokens_used=sub.tokens_used + tokens)

    @staticmethod
    async def reset_monthly_usage() -> None:
        async with get_session() as session:
            sub_repo = SubscriptionRepository(session)
            subs = await sub_repo.list(limit=10000)
            for sub in subs:
                await sub_repo.update(sub, tokens_used=0)
        logger.info("Monthly usage reset for all subscriptions")

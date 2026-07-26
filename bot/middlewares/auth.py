"""Auth middleware — registers user in DB on every message."""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker

from db.models.user import UserRole
from db.repositories import UserRepository
from config.logging import get_logger

logger = get_logger("middleware.auth")


class AuthMiddleware(BaseMiddleware):
    """Resolves/creates a User record and injects it into handler data."""

    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if not tg_user:
            return await handler(event, data)

        async with self.session_factory() as session:
            repo = UserRepository(session)
            user, created = await repo.get_or_create(
                telegram_id=tg_user.id,
                username=fg_user.username if (fg_user := tg_user) else None,
                full_name=tg_user.full_name or "",
                language_code=tg_user.language_code or "en",
            )
            data["user"] = user
            data["user_created"] = created

        return await handler(event, data)


class AdminMiddleware(BaseMiddleware):
    """Restricts access to admin/owner only."""

    def __init__(self, admin_ids: list[int]):
        self.admin_ids = set(admin_ids)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("user")
        if not user:
            return None
        if user.telegram_id in self.admin_ids or user.role in (UserRole.ADMIN, UserRole.OWNER):
            return await handler(event, data)
        # Silently drop non-admin requests to admin handlers
        return None

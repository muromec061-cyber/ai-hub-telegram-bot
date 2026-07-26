"""User repository."""
from __future__ import annotations

from sqlalchemy import select

from db.models.user import User, UserRole, UserStatus
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        *,
        username: str | None = None,
        full_name: str = "",
        language_code: str = "en",
    ) -> tuple[User, bool]:
        existing = await self.get_by_telegram_id(telegram_id)
        if existing:
            return existing, False
        user = await self.create(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name or username or str(telegram_id),
            language_code=language_code,
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        return user, True

    async def set_role(self, user_id: int, role: UserRole) -> User | None:
        user = await self.get(user_id)
        if not user:
            return None
        return await self.update(user, role=role)

    async def block(self, user_id: int) -> User | None:
        user = await self.get(user_id)
        if not user:
            return None
        return await self.update(user, status=UserStatus.BLOCKED)

    async def list_admins(self) -> list[User]:
        result = await self.session.execute(
            select(User).where(User.role.in_([UserRole.ADMIN, UserRole.OWNER]))
        )
        return list(result.scalars().all())

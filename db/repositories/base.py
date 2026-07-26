"""Base repository with common CRUD operations."""
from __future__ import annotations

from typing import Any, Generic, Sequence, Type, TypeVar

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    model: Type[T]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, pk: Any) -> T | None:
        result = await self.session.execute(select(self.model).where(self.model.id == pk))
        return result.scalar_one_or_none()

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[T]:
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return result.scalars().all()

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(self.model))
        return result.scalar_one() or 0

    async def create(self, **fields: Any) -> T:
        instance = self.model(**fields)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: T, **fields: Any) -> T:
        for key, value in fields.items():
            setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, pk: Any) -> bool:
        result = await self.session.execute(delete(self.model).where(self.model.id == pk))
        return result.rowcount > 0

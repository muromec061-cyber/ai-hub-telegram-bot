"""Project repository."""
from __future__ import annotations

from sqlalchemy import select

from db.models.project import Project, ProjectStatus
from .base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def list_by_owner(self, owner_id: int, *, limit: int = 50) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(Project.owner_id == owner_id)
            .order_by(Project.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_active(self, owner_id: int) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(
                Project.owner_id == owner_id,
                Project.status.in_(
                    [ProjectStatus.DRAFT, ProjectStatus.ACTIVE, ProjectStatus.PAUSED]
                ),
            )
            .order_by(Project.updated_at.desc())
        )
        return list(result.scalars().all())

    async def set_status(self, project_id: int, status: ProjectStatus) -> Project | None:
        proj = await self.get(project_id)
        if not proj:
            return None
        return await self.update(proj, status=status)

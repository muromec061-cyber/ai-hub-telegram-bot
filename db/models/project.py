"""Project model — top-level container for tasks and files."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_type: Mapped[str] = mapped_column(String(64), default="general", index=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), default=ProjectStatus.DRAFT, index=True
    )

    # GitHub integration
    github_repo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    github_repo_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Deployment
    deployed_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cloudflare_deployment_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Metadata
    tech_stack: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    config: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="projects")
    tasks: Mapped[List["Task"]] = relationship(  # noqa: F821
        "Task", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project {self.id} {self.name} ({self.status.value})>"

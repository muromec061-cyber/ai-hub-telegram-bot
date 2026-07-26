"""Task model — atomic unit of work delegated to an agent."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class TaskStatus(str, enum.Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING = "waiting"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    project_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True
    )
    parent_task_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=True
    )
    creator_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    assigned_agent: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.QUEUED, index=True)
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority), default=TaskPriority.NORMAL, index=True
    )

    # Task chain — sequence of subtasks
    chain: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    current_step: Mapped[int] = mapped_column(Integer, default=0)

    # Execution
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Artifacts
    artifacts: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    # e.g. {"files": [...], "urls": [...], "repo_url": "..."}

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project = relationship("Project", back_populates="tasks")
    creator = relationship("User", back_populates="tasks")
    runs: Mapped[list["AgentRun"]] = relationship(  # noqa: F821
        "AgentRun", back_populates="task", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Task {self.id} {self.title[:30]} ({self.status.value})>"

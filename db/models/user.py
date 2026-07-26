"""User model with roles, status, subscription tier."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class UserRole(str, enum.Enum):
    USER = "user"
    PRO = "pro"
    TEAM = "team"
    ADMIN = "admin"
    OWNER = "owner"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    PENDING = "pending"
    DELETED = "deleted"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    language_code: Mapped[Optional[str]] = mapped_column(String(8), default="en")

    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, index=True)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE, index=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Per-user preferences
    model_preference: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    projects: Mapped[List["Project"]] = relationship(  # noqa: F821
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )
    tasks: Mapped[List["Task"]] = relationship(  # noqa: F821
        "Task", back_populates="creator", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.telegram_id} ({self.role.value})>"

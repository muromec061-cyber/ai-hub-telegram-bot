"""Subscription model — plans, billing, entitlements."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SubscriptionPlan(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    BUSINESS = "business"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )

    plan: Mapped[SubscriptionPlan] = mapped_column(Enum(SubscriptionPlan), default=SubscriptionPlan.FREE)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE
    )

    # Limits
    monthly_tokens: Mapped[int] = mapped_column(default=100_000)
    tokens_used: Mapped[int] = mapped_column(default=0)
    monthly_projects: Mapped[int] = mapped_column(default=3)
    projects_used: Mapped[int] = mapped_column(default=0)
    parallel_tasks: Mapped[int] = mapped_column(default=1)

    # Billing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    payment_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    extra: Mapped[dict] = mapped_column(JSON, default=dict)

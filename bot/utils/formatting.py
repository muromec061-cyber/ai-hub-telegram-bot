"""Shared utilities for bot handlers."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from db.models.task import TaskStatus

STATUS_EMOJI = {
    TaskStatus.QUEUED: "⏳",
    TaskStatus.PLANNING: "🧭",
    TaskStatus.RUNNING: "⚙️",
    TaskStatus.WAITING: "⏸",
    TaskStatus.TESTING: "🧪",
    TaskStatus.COMPLETED: "✅",
    TaskStatus.FAILED: "❌",
    TaskStatus.CANCELLED: "🚫",
    TaskStatus.TIMEOUT: "⏰",
}


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def truncate(text: str, n: int = 200) -> str:
    if len(text) <= n:
        return text
    return text[: n - 1] + "…"


def format_duration(start: datetime, end: datetime | None) -> str:
    if not end:
        return "—"
    seconds = int((end - start).total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, m = divmod(minutes, 60)
    return f"{hours}h {m}m"


def format_tokens(n: int) -> str:
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1000:.1f}K"
    return f"{n / 1_000_000:.2f}M"


def is_admin_user(user, admin_ids: list[int]) -> bool:
    from db.models.user import UserRole
    return user.telegram_id in admin_ids or user.role in (UserRole.ADMIN, UserRole.OWNER)


def _get_session_factory(bot):
    """Return the AsyncSession factory stored on the bot's app state."""
    from bot.bot import get_app
    app = get_app()
    return app["session_factory"]

"""Notification service — push, email, webhooks."""
from __future__ import annotations

import asyncio
from typing import Any

import httpx
from aiogram import Bot

from config.logging import get_logger
from db.models import get_session
from db.repositories import NotificationRepository

logger = get_logger("services.notifications")


class NotificationService:
    def __init__(self, bot: Bot | None = None):
        self.bot = bot

    async def notify_user(self, user_id: int, title: str, message: str, *, ntype: str = "info", payload: dict | None = None) -> None:
        """Store in DB and push to Telegram."""
        from db.models.notification import NotificationType
        try:
            type_enum = NotificationType(ntype)
        except ValueError:
            type_enum = NotificationType.INFO

        async with get_session() as session:
            repo = NotificationRepository(session)
            await repo.create(
                user_id=user_id, type=type_enum, title=title, message=message, payload=payload or {},
            )

        if self.bot:
            try:
                await self.bot.send_message(user_id, f"🔔 <b>{title}</b>\n\n{message}")
            except Exception as e:
                logger.error(f"Telegram notify failed: {e}")

    async def send_webhook(self, url: str, payload: dict) -> bool:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(url, json=payload)
                return r.status_code < 400
        except Exception as e:
            logger.error(f"Webhook send failed: {e}")
            return False

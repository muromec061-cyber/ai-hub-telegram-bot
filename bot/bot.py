"""
Main bot module — wires everything together.

Uses ServiceCluster as single source of truth for LLM + OpenClaw + services.
All handlers use the new UI (keyboards, animation, dashboards).
"""
from __future__ import annotations

import asyncio
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from agents import Orchestrator, TaskQueue
from bot.handlers import admin as admin_handler
from bot.handlers import freeform, projects, settings as settings_handler
from bot.handlers import start, tasks
from bot.middlewares import AuthMiddleware
from bot.ui import anim, dashboard, keyboards
from config.env.settings import get_settings
from config.logging import get_logger
from db.models import AsyncSessionLocal, close_db, init_db
from services import ServiceCluster, get_cluster
from services.cloudflare.client import CloudflareService
from services.github.client import GitHubService

logger = get_logger("bot")

_app_instance: dict[str, Any] = {}


def get_app() -> dict[str, Any]:
    if not _app_instance:
        raise RuntimeError("Bot app not initialized. Call setup_bot() first.")
    return _app_instance


def setup_bot() -> dict[str, Any]:
    if _app_instance:
        return _app_instance

    cfg = get_settings()
    cluster = get_cluster()

    bot = Bot(
        token=cfg.telegram.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # FSM storage — MemoryStorage by default; Redis only if REDIS_URL set and reachable
    storage: Any = MemoryStorage()
    use_redis = (
        cfg.app_env != "development"
        and cfg.security.redis_url
        and "redis://" in cfg.security.redis_url
    )
    if use_redis:
        try:
            import redis as _redis_sync
            sync_client = _redis_sync.from_url(cfg.security.redis_url, socket_connect_timeout=2)
            sync_client.ping()
            sync_client.close()
            # Synchronous ping succeeded, build async client
            import redis.asyncio as aioredis
            client = aioredis.from_url(cfg.security.redis_url)
            storage = RedisStorage(redis=client)
            logger.info(f"FSM: Redis at {cfg.security.redis_url}")
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}), using MemoryStorage")
    else:
        logger.info("FSM: MemoryStorage")

    dp = Dispatcher(storage=storage)

    # Middleware
    auth_mw = AuthMiddleware(AsyncSessionLocal)
    dp.message.middleware(auth_mw)
    dp.callback_query.middleware(auth_mw)

    # Routers
    dp.include_router(start.router)
    dp.include_router(projects.router)
    dp.include_router(tasks.router)
    dp.include_router(settings_handler.router)
    dp.include_router(admin_handler.router)
    dp.include_router(freeform.router)

    # Services via cluster
    github = None
    cloudflare = None
    if cfg.github.token:
        github = GitHubService()
    if cfg.cloudflare.api_token:
        cloudflare = CloudflareService()

    # Orchestrator (uses cluster for LLM)
    orchestrator = Orchestrator(
        llm=None,  # orchestrator will use cluster
        base_dir="generated",
        github=github,
        cloudflare=cloudflare,
        notify_callback=_make_notifier(bot),
        cluster=cluster,
    )
    queue = TaskQueue(orchestrator, max_concurrent=cfg.max_parallel_tasks)

    _app_instance["bot"] = bot
    _app_instance["dp"] = dp
    _app_instance["orchestrator"] = orchestrator
    _app_instance["task_queue"] = queue
    _app_instance["session_factory"] = AsyncSessionLocal
    _app_instance["cluster"] = cluster
    _app_instance["github"] = github
    _app_instance["cloudflare"] = cloudflare

    bot._app_state = _app_instance  # type: ignore[attr-defined]

    return _app_instance


def _make_notifier(bot: Bot):
    async def notify(telegram_id: int, text: str):
        try:
            await bot.send_message(telegram_id, text)
        except Exception as e:
            logger.error(f"Notify failed for {telegram_id}: {e}")
    return notify


async def on_startup() -> None:
    logger.info("Starting bot...")
    await init_db()
    app = setup_bot()
    bot = app["bot"]
    cluster = app["cluster"]

    # Health snapshot (best effort)
    try:
        snap = await cluster.health()
        logger.info(f"Cluster health: {snap}")
    except Exception as e:
        logger.warning(f"Cluster health check failed: {e}")

    me = await bot.get_me()
    logger.info(f"Bot @{me.username} ({me.id}) started")


async def on_shutdown() -> None:
    logger.info("Shutting down...")
    app = get_app()
    cluster = app.get("cluster")
    if cluster:
        await cluster.shutdown()
    await app["bot"].session.close()
    await close_db()


async def run_polling() -> None:
    app = setup_bot()
    await on_startup()
    try:
        await app["dp"].start_polling(app["bot"], allowed_updates=["message", "callback_query"])
    finally:
        await on_shutdown()


async def run_webhook(webhook_url: str) -> None:
    app = setup_bot()
    await on_startup()
    try:
        await app["bot"].set_webhook(webhook_url)
        logger.info(f"Webhook set: {webhook_url}")
    finally:
        await on_shutdown()

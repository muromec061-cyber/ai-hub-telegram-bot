"""
Main bot module — wires everything together.
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
from bot.handlers import agent as agent_handler
from bot.handlers import freeform, projects, settings as settings_handler
from bot.handlers import start, tasks
from bot.middlewares import AuthMiddleware
from config.logging import get_logger
from config.env.settings import get_settings
from db.models import AsyncSessionLocal, close_db, init_db
from services import get_cluster
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
    bot = Bot(token=cfg.telegram.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    storage: Any = MemoryStorage()
    use_redis = cfg.app_env != "development" and cfg.security.redis_url and "redis://" in cfg.security.redis_url
    if use_redis:
        try:
            import redis as _redis_sync
            sync_client = _redis_sync.from_url(cfg.security.redis_url, socket_connect_timeout=2)
            sync_client.ping()
            sync_client.close()
            import redis.asyncio as aioredis
            storage = RedisStorage(redis=aioredis.from_url(cfg.security.redis_url))
        except Exception as exc:
            logger.warning(f"Redis unavailable ({exc}), using MemoryStorage")

    dp = Dispatcher(storage=storage)
    auth_mw = AuthMiddleware(AsyncSessionLocal)
    dp.message.middleware(auth_mw)
    dp.callback_query.middleware(auth_mw)

    dp.include_router(start.router)
    dp.include_router(projects.router)
    dp.include_router(tasks.router)
    dp.include_router(settings_handler.router)
    dp.include_router(admin_handler.router)
    dp.include_router(agent_handler.router)
    dp.include_router(freeform.router)

    github = GitHubService() if cfg.github.token else None
    cloudflare = CloudflareService() if cfg.cloudflare.api_token else None

    orchestrator = Orchestrator(
        llm=None,
        base_dir="generated",
        github=github,
        cloudflare=cloudflare,
        notify_callback=_make_notifier(bot),
        cluster=cluster,
    )
    queue = TaskQueue(orchestrator, max_concurrent=cfg.max_parallel_tasks)

    _app_instance.update({
        "bot": bot,
        "dp": dp,
        "orchestrator": orchestrator,
        "task_queue": queue,
        "session_factory": AsyncSessionLocal,
        "cluster": cluster,
        "github": github,
        "cloudflare": cloudflare,
    })
    bot._app_state = _app_instance  # type: ignore[attr-defined]
    return _app_instance


def _make_notifier(bot: Bot):
    async def notify(telegram_id: int, text: str):
        try:
            await bot.send_message(telegram_id, text)
        except Exception as exc:
            logger.error(f"Notify failed for {telegram_id}: {exc}")
    return notify


async def on_startup() -> None:
    await init_db()
    app = setup_bot()
    bot = app["bot"]
    try:
        snap = await app["cluster"].health()
        logger.info(f"Cluster health: {snap}")
    except Exception as exc:
        logger.warning(f"Cluster health check failed: {exc}")
    me = await bot.get_me()
    logger.info(f"Bot @{me.username} ({me.id}) started")


async def on_shutdown() -> None:
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


async def run_webhook(webhook_url: str, port: int | None = None) -> None:
    from aiohttp import web
    app = setup_bot()
    await on_startup()
    bot, dp = app["bot"], app["dp"]
    port = port or int(get_settings().port or 10000)

    async def health(request):
        return web.json_response({"ok": True, "bot": bot._me.username if hasattr(bot, "_me") else "unknown"})

    async def telegram_webhook(request):
        try:
            update_data = await request.json()
        except Exception:
            return web.Response(status=400, text="bad json")
        from aiogram import types
        await dp.feed_update(bot, types.Update(**update_data))
        return web.json_response({"ok": True})

    aio_app = web.Application()
    aio_app.router.add_get("/health", health)
    aio_app.router.add_post("/webhook/telegram", telegram_webhook)
    aio_app.router.add_post("/webhook/{token}", telegram_webhook)
    runner = web.AppRunner(aio_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    if webhook_url:
        try:
            await bot.set_webhook(webhook_url)
        except Exception as exc:
            logger.warning(f"set_webhook failed: {exc}")
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
        await on_shutdown()

"""
Main entry point — runs the Telegram bot (polling mode by default).

Usage:
    python main.py
    python main.py --mode webhook --webhook-url https://example.com/webhook
    python main.py --mode scheduler
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent))

from config.env.settings import get_settings
from config.logging import setup_logging, get_logger


def parse_args():
    p = argparse.ArgumentParser(description="AI Startup Bot")
    p.add_argument("--mode", choices=["polling", "webhook", "scheduler", "mcp"], default="polling")
    p.add_argument("--webhook-url", type=str, default=None)
    return p.parse_args()


async def run_scheduler() -> None:
    """Run background jobs: monthly usage reset, backups, cleanup."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from services.subscription import SubscriptionService
    from services.backup import BackupService

    scheduler = AsyncIOScheduler()
    # Monthly reset
    scheduler.add_job(SubscriptionService.reset_monthly_usage, CronTrigger(day=1, hour=0, minute=0))
    # Daily backup
    scheduler.add_job(BackupService.create_backup, CronTrigger(hour=3, minute=0))
    scheduler.start()
    logger.info("Scheduler started. Waiting for jobs...")

    # Keep alive
    await asyncio.Event().wait()


async def main():
    setup_logging()
    logger = get_logger("main")
    args = parse_args()
    settings = get_settings()
    logger.info(f"App starting in {args.mode} mode, env={settings.app_env}")

    if args.mode == "polling":
        from bot.bot import run_polling
        await run_polling()
    elif args.mode == "webhook":
        from bot.bot import run_webhook
        await run_webhook(args.webhook_url or settings.telegram.webhook_url)
    elif args.mode == "scheduler":
        await run_scheduler()
    elif args.mode == "mcp":
        from services.mcp import MCPServer
        await MCPServer().start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")

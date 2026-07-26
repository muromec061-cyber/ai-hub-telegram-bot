"""
Structured logging using loguru + structlog.
Sends to stdout, file rotation, JSON for production.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import structlog
from loguru import logger as loguru_logger

from config.env.settings import get_settings


def setup_logging() -> None:
    settings = get_settings()
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    loguru_logger.remove()
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    loguru_logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=settings.debug,
    )

    loguru_logger.add(
        log_dir / "app.log",
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        level=settings.log_level,
        format=log_format,
        enqueue=False,
    )

    loguru_logger.add(
        log_dir / "errors.log",
        rotation="50 MB",
        retention="60 days",
        compression="zip",
        level="ERROR",
        format=log_format,
        backtrace=True,
        diagnose=settings.debug,
        enqueue=False,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog, settings.log_level, 20)
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> Any:
    if name:
        return loguru_logger.bind(component=name)
    return loguru_logger


__all__ = ["setup_logging", "get_logger"]

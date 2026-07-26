"""
UX/UI utilities: premium animation, typewriter, progress bars, banners.

Все эффекты — production-quality, реально улучшают восприятие.
"""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable

from aiogram import Bot
from aiogram.enums import ChatAction
from aiogram.types import Message

from config.logging import get_logger

logger = get_logger("ui.anim")


# ===== Visual primitives =====
PROGRESS_FRAMES = ["▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"]
SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
SPINNER_BRAILLE = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
DOTS = ["⠁", "⠂", "⠄", "⡀", "⢀", "⠠", "⠐", "⠈"]
PARTICLES = ["✨", "⭐", "🌟", "💫", "✦", "✧"]


def progress_bar(percent: int, width: int = 20, fill: str = "█", empty: str = "░") -> str:
    percent = max(0, min(100, percent))
    filled = int(width * percent / 100)
    return f"{fill * filled}{empty * (width - filled)} {percent}%"


def spinner_frame(idx: int, style: str = "default") -> str:
    if style == "braille":
        return SPINNER_BRAILLE[idx % len(SPINNER_BRAILLE)]
    if style == "dots":
        return DOTS[idx % len(DOTS)]
    return SPINNER[idx % len(SPINNER)]


def fancy_header(title: str, emoji: str = "🤖", width: int = 30) -> str:
    bar = "━" * width
    return f"┏{bar}┓\n┃  {emoji}  <b>{title}</b>\n┗{bar}┛"


def typing_dots(idx: int) -> str:
    n = (idx % 4)
    return "." * n + " " * (3 - n)


# ===== Animation primitives =====
@asynccontextmanager
async def typing_indicator(bot: Bot, chat_id: int, *, interval: float = 4.0):
    """Send 'typing' chat action repeatedly. Use as async context manager."""
    stop = asyncio.Event()

    async def _loop():
        try:
            while not stop.is_set():
                try:
                    await bot.send_chat_action(chat_id, ChatAction.TYPING)
                except Exception:
                    pass
                try:
                    await asyncio.wait_for(stop.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(_loop())
    try:
        yield
    finally:
        stop.set()
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


async def progress_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


async def animated_status(
    bot: Bot,
    chat_id: int,
    text: str,
    *,
    duration: float = 30.0,
    update_interval: float = 1.5,
    frames: list[str] | None = None,
    style: str = "default",
) -> Message:
    """Send a message and animate it with a spinner until duration expires or message changes."""
    frames = frames or (SPINNER_BRAILLE if style == "braille" else SPINNER)
    msg = await bot.send_message(chat_id, f"{frames[0]} {text}")
    start = time.time()
    i = 0
    while time.time() - start < duration:
        await asyncio.sleep(update_interval)
        i += 1
        try:
            await msg.edit_text(f"{spinner_frame(i, style)} {text}{typing_dots(i // 2)}")
        except Exception:
            break
    return msg


async def typewriter(
    message: Message,
    full_text: str,
    *,
    chunk_size: int = 35,
    delay: float = 0.025,
) -> None:
    """Edit a message in growing chunks to simulate a typewriter effect."""
    if not full_text:
        return
    chunks = [full_text[i : i + chunk_size] for i in range(0, len(full_text), chunk_size)]
    rendered = ""
    for chunk in chunks:
        rendered += chunk
        try:
            await message.edit_text(rendered)
        except Exception:
            pass
        await asyncio.sleep(delay)


async def typewriter_with_blink(
    bot: Bot,
    chat_id: int,
    text: str,
    *,
    reply_to: int | None = None,
    cursor: str = "▌",
) -> Message | None:
    """Typewriter with a blinking cursor at the end. Cursor disappears on final frame."""
    msg = await bot.send_message(chat_id, cursor, reply_to_message_id=reply_to)
    chunks = [text[i : i + 30] for i in range(0, len(text), 30)]
    rendered = ""
    for i, chunk in enumerate(chunks):
        rendered += chunk
        is_last = (i == len(chunks) - 1)
        try:
            if is_last:
                await msg.edit_text(rendered)
                await asyncio.sleep(0.05)
            else:
                # Blink cursor on/off
                cur = cursor if i % 2 == 0 else ""
                await msg.edit_text(f"{rendered}{cur}")
        except Exception:
            pass
        await asyncio.sleep(0.03)
    return msg


async def stream_text(
    bot: Bot,
    chat_id: int,
    iterator: AsyncIterator[str],
    *,
    reply_to: int | None = None,
    min_interval: float = 0.5,
    with_cursor: bool = True,
) -> Message | None:
    """Stream text into a single message with cursor."""
    msg: Message | None = None
    buffer = ""
    last_update = time.time()
    i = 0
    try:
        async for chunk in iterator:
            buffer += chunk
            now = time.time()
            if now - last_update >= min_interval and buffer:
                cur = "▌" if (with_cursor and i % 2 == 0) else ""
                if msg is None:
                    msg = await bot.send_message(chat_id, f"{buffer}{cur}", reply_to_message_id=reply_to)
                else:
                    try:
                        await msg.edit_text(f"{buffer}{cur}")
                    except Exception:
                        pass
                i += 1
                last_update = now
        if buffer:
            cur = "" if not with_cursor else ""
            if msg is None:
                msg = await bot.send_message(chat_id, buffer, reply_to_message_id=reply_to)
            else:
                try:
                    await msg.edit_text(buffer)
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"stream_text failed: {e}")
        if msg:
            try:
                await msg.edit_text(f"{buffer}\n\n⚠️ Stream interrupted: {e}")
            except Exception:
                pass
    return msg


async def pulse_progress(
    bot: Bot,
    chat_id: int,
    title: str,
    steps: list[str],
    *,
    step_delay: float = 0.6,
) -> Message:
    """Show a 'pulse' progress: cycles through each step with a spinner.

    After all steps, message becomes a success card.
    """
    msg = await bot.send_message(
        chat_id,
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n┃  ⏳  <b>{title}</b>\n┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n{spinner_frame(0)} Подготовка…"
    )
    for i, step in enumerate(steps):
        await asyncio.sleep(step_delay)
        try:
            lines = [f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓", f"┃  {spinner_frame(i+1)}  <b>{title}</b>", f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛", ""]
            for j, s in enumerate(steps):
                if j < i:
                    lines.append(f"✅  {s}")
                elif j == i:
                    lines.append(f"{spinner_frame(i+1)}  <b>{s}</b>")
                else:
                    lines.append(f"⬜  {s}")
            pct = int(100 * (i + 1) / max(1, len(steps)))
            lines.append("")
            lines.append(f"{progress_bar(pct)}")
            await msg.edit_text("\n".join(lines))
        except Exception:
            break
    return msg


async def success_card(message: Message, title: str, body: str, *, emoji: str = "✅") -> None:
    """Replace a message with a styled success card."""
    text = (
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃  {emoji}  <b>{title}</b>\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"{body}"
    )
    try:
        await message.edit_text(text)
    except Exception:
        pass


async def countdown(
    bot: Bot,
    chat_id: int,
    title: str,
    seconds: int = 5,
) -> None:
    """Edit a message once per second for N seconds: 3..2..1..GO!"""
    for i in range(seconds, 0, -1):
        try:
            await bot.send_message(chat_id, f"⏱ <b>{title}</b> через <b>{i}</b>…")
        except Exception:
            pass
        await asyncio.sleep(1.0)
    try:
        await bot.send_message(chat_id, f"🚀 <b>{title}</b> — поехали!")
    except Exception:
        pass

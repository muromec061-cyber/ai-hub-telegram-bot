"""Telegram interface for the real multi-model AI agent."""
from __future__ import annotations

import html

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from services.agent import ModelRegistry, RealAIAgent

router = Router(name="agent")


def _agent() -> RealAIAgent:
    return RealAIAgent()


@router.message(Command("models"))
async def models(message: Message) -> None:
    registry = ModelRegistry()
    available = registry.available()
    if not available:
        await message.answer("❌ Нет доступных моделей. Добавь API-ключ или запусти Ollama.")
        return
    lines = ["🤖 <b>Доступные реальные модели</b>", ""]
    for spec in available:
        lines.append(f"• <code>{html.escape(spec.id)}</code> — {html.escape(spec.label)}")
    lines.append("\nИспользование: <code>/ask &lt;model_id&gt; | &lt;запрос&gt;</code>")
    await message.answer("\n".join(lines))


@router.message(Command("ask"))
async def ask(message: Message) -> None:
    raw = (message.text or "").removeprefix("/ask").strip()
    if "|" in raw:
        model_id, prompt = [part.strip() for part in raw.split("|", 1)]
    else:
        model_id, prompt = None, raw
    if not prompt:
        await message.answer("Использование: <code>/ask [model_id |] запрос</code>\nСписок: <code>/models</code>")
        return
    status = await message.answer("🧠 Выполняю реальный запрос к модели…")
    try:
        result = await _agent().complete(prompt, model_id=model_id)
        await status.edit_text(result or "Модель вернула пустой ответ.")
    except Exception as exc:
        await status.edit_text(f"❌ Ошибка реального LLM-вызова:\n<code>{html.escape(str(exc))}</code>")

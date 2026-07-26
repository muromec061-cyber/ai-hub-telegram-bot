"""
Freeform message handler — catch-all with animation and cluster dispatch.

When the user writes any non-command text, we:
1. Show "typing" indicator + animated status message
2. Try to use cluster (LLM + OpenClaw)
3. If goal is a build, route through orchestrator
4. If goal is a question, call LLM directly and stream the answer
"""
from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.types import Message

from bot.ui import anim, dashboard, keyboards
from bot.ui.anim import typing_indicator
from config.logging import get_logger
from db.models import get_session
from db.repositories import ProjectRepository, TaskRepository

logger = get_logger("handlers.freeform")
router = Router(name="freeform")

REPLY_KEYWORDS = {
    "🚀 Новый проект", "📋 Задачи", "📁 Проекты", "🧠 Память",
    "💎 Подписка", "⚙️ Настройки", "🛠 Админ", "❓ Помощь", "❌ Отмена",
}

BUILD_KEYWORDS = (
    "создай", "сделай", "напиши", "разработай", "собери", "построй",
    "запусти", "задеплой", "хочу", "нужен", "нужна", "нужно", "сделать",
    "создать", "разверни", "deploy", "build", "create", "make",
    "telegram bot", "телеграм бот", "telegram-бот", "сайт", "saas", "приложение",
    "app", "website", "landing", "лендинг", "стартап", "startup",
)


def _looks_like_build(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in BUILD_KEYWORDS)


@router.message(F.text & ~F.text.startswith("/"))
async def freeform_handler(message: Message, user, state) -> None:
    text = (message.text or "").strip()
    if not text or len(text) < 2:
        return

    current_state = await state.get_state()
    if current_state:
        return
    if text in REPLY_KEYWORDS:
        return

    # Quick chat — ask LLM directly with typewriter
    if not _looks_like_build(text):
        await _quick_chat(message, user, text)
        return

    # Otherwise: build task with animation
    await _submit_build_task(message, user, text)


async def _quick_chat(message: Message, user, text: str) -> None:
    cluster = message.bot._app_state["cluster"]  # type: ignore[attr-defined]
    try:
        llm = await cluster.get_llm()
    except Exception as e:
        await message.answer(f"⚠️ Не настроен ни один LLM-провайдер.\n\nДобавь ключ в <code>.env</code>:\n  • <code>GROQ_API_KEY</code>\n  • <code>OPENAI_API_KEY</code>\n  • <code>ANTHROPIC_API_KEY</code>\n\nОшибка: <code>{e}</code>")
        return

    status_msg = await message.answer(f"🧠 <b>Думаю…</b>\n\n<code>{text[:200]}</code>")

    async with typing_indicator(message.bot, message.chat.id, interval=4.0):
        anim_task = asyncio.create_task(anim.animated_status(
            message.bot, message.chat.id,
            "Думаю",
            duration=2.0, update_interval=0.6, style="braille",
        ))
        try:
            from services.llm import LLMMessage, LLMRequest
            req = LLMRequest(
                messages=[LLMMessage(role="user", content=text)],
                temperature=0.7, max_tokens=2048,
            )
            response = await llm.complete(req)
            anim_task.cancel()
            try:
                await anim_task
            except Exception:
                pass
            await status_msg.delete()
            # Typewriter with blinking cursor
            await anim.typewriter_with_blink(
                message.bot, message.chat.id,
                response.content or "(пустой ответ)",
            )
        except Exception as e:
            await status_msg.edit_text(f"❌ <b>Ошибка:</b>\n<code>{e}</code>")


async def _submit_build_task(message: Message, user, text: str) -> None:
    from bot.bot import get_app
    app = get_app()

    status_msg = await message.answer(
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃  ⚙️  <b>Создаю задачу…</b>\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"<i>{text[:200]}</i>"
    )

    async with typing_indicator(message.bot, message.chat.id, interval=4.0):
        async with get_session() as session:
            proj_repo = ProjectRepository(session)
            active = await proj_repo.list_active(user.id)
            project_id = active[0].id if active else None
            if not project_id:
                project = await proj_repo.create(
                    owner_id=user.id,
                    name=f"Chat-{message.message_id}",
                    description=text[:500],
                    project_type="general",
                    tags=["freeform"],
                )
                project_id = project.id
            task_repo = TaskRepository(session)
            task = await task_repo.create(
                creator_id=user.id,
                project_id=project_id,
                title=text[:200],
                description=text,
            )
            task_id = task.id

        await app["task_queue"].submit(task_id, user.id, text, project_id=project_id)

    # Animate status with pulse-progress style
    for i in range(3):
        await asyncio.sleep(0.8)
        try:
            await status_msg.edit_text(
                f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
                f"┃  {anim.spinner_frame(i, style='braille')}  <b>Запускаю команду агентов…</b>\n"
                f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
                f"📋 Задача <b>#{task_id}</b>\n"
                f"📁 Проект: <code>{project_id}</code>\n"
                f"{anim.progress_bar((i+1)*33)}\n\n"
                f"<i>{text[:200]}</i>"
            )
        except Exception:
            break

    try:
        await status_msg.delete()
    except Exception:
        pass

    await message.answer(
        f"✅ <b>Задача #{task_id} запущена!</b>\n\n"
        f"📝 <i>{text[:200]}</i>\n\n"
        f"⚙️  Команда агентов приступила.\n"
        f"🔔 Результат придёт уведомлением.\n\n"
        f"📊 Статус: 📋 Задачи → #{task_id}",
        reply_markup=keyboards.main_dashboard(_dummy_user_for_reply(), is_admin=False),
    )


def _dummy_user_for_reply():
    from types import SimpleNamespace
    from db.models.user import UserRole
    return SimpleNamespace(full_name="Friend", role=UserRole.USER, telegram_id=0)

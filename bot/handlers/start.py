"""/start, /help, main menu — redesigned UX."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.ui import dashboard, keyboards
from bot.ui.anim import typing_indicator
from config.env.settings import get_settings
from config.logging import get_logger
from db.models.user import UserRole
from db.models import get_session
from db.repositories import (
    ProjectRepository, SubscriptionRepository, TaskRepository,
)
import asyncio

logger = get_logger("handlers.start")
router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, user, state: FSMContext) -> None:
    await state.clear()
    is_admin = user.role in (UserRole.ADMIN, UserRole.OWNER)
    text = dashboard.welcome_card(user, is_admin=is_admin)
    async with typing_indicator(message.bot, message.chat.id, interval=3.0):
        from bot.ui.anim import pulse_progress, success_card
        msg = await pulse_progress(
            message.bot, message.chat.id,
            title="Инициализация",
            steps=["Загружаю модули", "Подключаю LLM-кластер", "Проверяю OpenClaw", "Готово!"],
            step_delay=0.4,
        )
        await asyncio.sleep(0.3)
        await success_card(msg, "AI-стартап запущен", text, emoji="🚀")
        try:
            await msg.edit_reply_markup(reply_markup=keyboards.main_dashboard(user, is_admin=is_admin))
        except Exception:
            await message.answer(text, reply_markup=keyboards.main_dashboard(user, is_admin=is_admin))
    logger.info(f"User {user.telegram_id} started bot")


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message) -> None:
    text = (
        "📖 <b>Как пользоваться</b>\n\n"
        "🚀 <b>Новый проект</b> — сайт / Telegram-бот / SaaS / скрипт\n"
        "📋 <b>Задачи</b> — текущая работа, история, артефакты\n"
        "📁 <b>Проекты</b> — твои проекты со ссылками на GitHub и live-сайт\n"
        "🧠 <b>Память</b> — что я о тебе помню\n"
        "🤖 <b>Модель AI</b> — переключение между Groq, OpenAI, Cloudflare, Anthropic, Ollama\n"
        "💎 <b>Подписка</b> — Free / Pro / Team / Business\n\n"
        "💡 <b>Совет:</b> просто напиши, что хочешь построить — я пойму."
    )
    await message.answer(text, reply_markup=keyboards.main_dashboard(_dummy_user(), is_admin=False))


def _dummy_user():
    from types import SimpleNamespace
    return SimpleNamespace(full_name="Friend", role=UserRole.USER, telegram_id=0)


@router.message(F.text == "❌ Отмена")
@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено. Возвращаюсь в меню.", reply_markup=keyboards.main_dashboard(_dummy_user(), is_admin=False))


@router.callback_query(keyboards.Nav.filter(F.section == "main"))
async def nav_main(callback, user):
    is_admin = user.role in (UserRole.ADMIN, UserRole.OWNER)
    text = dashboard.welcome_card(user, is_admin=is_admin)
    await callback.message.answer(text, reply_markup=keyboards.main_dashboard(user, is_admin=is_admin))
    await callback.answer()


@router.callback_query(keyboards.Nav.filter(F.section == "help"))
async def nav_help(callback):
    await cmd_help(callback.message)
    await callback.answer()


@router.callback_query(keyboards.Nav.filter(F.section == "stats"))
async def nav_stats(callback, user):
    async with get_session() as session:
        sub_repo = SubscriptionRepository(session)
        sub = await sub_repo.get_or_create(user.id)
        proj_repo = ProjectRepository(session)
        task_repo = TaskRepository(session)
        projects = await proj_repo.list_active(user.id)
        tasks = await task_repo.list_by_user(user.id, limit=200)
        running = [t for t in tasks if t.status.value == "running"]
    text = dashboard.stats_card(user, sub, len(projects), len(tasks), len(running))
    await callback.message.answer(text, reply_markup=keyboards.back_button("main"))
    await callback.answer()


@router.callback_query(keyboards.Nav.filter(F.section == "model_picker"))
async def nav_model_picker(callback, user):
    cluster = callback.bot._app_state["cluster"]  # type: ignore[attr-defined]
    available = await cluster.available_llms()
    active = get_settings().llm.active_llm
    text = (
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃  🤖  <b>Выбор модели AI</b>\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"Сейчас активна: <b>{active}</b>\n\n"
        f"<i>Выбери модель — изменения применятся мгновенно:</i>"
    )
    await callback.message.answer(text, reply_markup=keyboards.model_picker(available, active))
    await callback.answer()


@router.callback_query(F.data.startswith("model:pick:"))
async def model_pick(callback, user):
    provider = callback.data.split(":")[2]
    # Persist user preference
    from db.repositories import UserRepository
    async with get_session() as session:
        await UserRepository(session).update(user, model_preference=provider) if hasattr(user, "model_preference") else None
    # Active switch (in-memory)
    get_settings().llm.active_llm = provider
    # Reset cluster LLM cache
    cluster = callback.bot._app_state["cluster"]  # type: ignore[attr-defined]
    cluster._llm = None
    cluster._llm_name = None
    text = (
        f"✅ <b>Модель переключена:</b> <code>{provider}</code>\n\n"
        f"Новые запросы пойдут через эту модель. Можно продолжать!"
    )
    await callback.message.answer(text, reply_markup=keyboards.main_dashboard(user, user.role in (UserRole.ADMIN, UserRole.OWNER)))
    await callback.answer(f"Модель: {provider}")

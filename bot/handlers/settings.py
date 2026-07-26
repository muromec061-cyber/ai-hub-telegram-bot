"""Settings, subscription, memory — redesigned."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.ui import dashboard, keyboards
from bot.ui.keyboards import Nav
from bot.utils import _get_session_factory
from config.logging import get_logger
from db.models.subscription import SubscriptionPlan, SubscriptionStatus
from db.repositories import MemoryRepository, SubscriptionRepository, UserRepository

logger = get_logger("handlers.settings")
router = Router(name="settings")


PLAN_INFO = {
    SubscriptionPlan.FREE: ("🆓 Free", "100K токенов/мес · 3 проекта · 1 параллельная задача"),
    SubscriptionPlan.PRO: ("⚡ Pro", "5M токенов/мес · 20 проектов · 3 параллельных задачи"),
    SubscriptionPlan.TEAM: ("👥 Team", "20M токенов/мес · 100 проектов · 10 параллельных задач"),
    SubscriptionPlan.BUSINESS: ("🏢 Business", "∞ токенов · ∞ проектов · 50 параллельных задач · SLA"),
}


@router.message(F.text == "⚙️ Настройки")
@router.callback_query(Nav.filter(F.section == "settings"))
async def show_settings(event: Message | CallbackQuery) -> None:
    text = (
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "┃  ⚙️  <b>Настройки</b>\n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
    )
    kb = keyboards.settings_panel()
    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb)
    else:
        await event.message.answer(text, reply_markup=kb)
        await event.answer()


@router.message(F.text == "💎 Подписка")
@router.callback_query(Nav.filter(F.section == "subscription"))
async def show_subscription(event: Message | CallbackQuery, user) -> None:
    async with _get_session_factory(event.bot)() as session:
        sub = await SubscriptionRepository(session).get_or_create(user.id)
    name, desc = PLAN_INFO.get(sub.plan, ("—", ""))
    text = (
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃  💎  <b>Подписка</b>\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"Твой план: <b>{name}</b>\n"
        f"<i>{desc}</i>\n\n"
        f"📊 Использовано: <b>{sub.tokens_used:,}</b> / {sub.monthly_tokens:,} токенов\n"
        f"📁 Проектов: {sub.projects_used} / {sub.monthly_projects}\n"
        f"⚡ Параллельных: {sub.parallel_tasks}\n\n"
        f"Выбери план для перехода:"
    )
    if isinstance(event, Message):
        await event.answer(text, reply_markup=keyboards.subscription_picker())
    else:
        await event.message.answer(text, reply_markup=keyboards.subscription_picker())
        await event.answer()


@router.callback_query(F.data.startswith("sub:pick:"))
async def change_plan(callback: CallbackQuery, user) -> None:
    plan_name = callback.data.split(":")[2]
    plan_map = {
        "free": SubscriptionPlan.FREE,
        "pro": SubscriptionPlan.PRO,
        "team": SubscriptionPlan.TEAM,
        "business": SubscriptionPlan.BUSINESS,
    }
    plan = plan_map.get(plan_name)
    if not plan:
        await callback.answer("Неизвестный план", show_alert=True)
        return

    plan_config = {
        SubscriptionPlan.FREE: dict(monthly_tokens=100_000, monthly_projects=3, parallel_tasks=1),
        SubscriptionPlan.PRO: dict(monthly_tokens=5_000_000, monthly_projects=20, parallel_tasks=3),
        SubscriptionPlan.TEAM: dict(monthly_tokens=20_000_000, monthly_projects=100, parallel_tasks=10),
        SubscriptionPlan.BUSINESS: dict(monthly_tokens=999_999_999, monthly_projects=9999, parallel_tasks=50),
    }
    async with _get_session_factory(callback.bot)() as session:
        sub_repo = SubscriptionRepository(session)
        sub = await sub_repo.get_or_create(user.id)
        await sub_repo.update(sub, plan=plan, status=SubscriptionStatus.ACTIVE, **plan_config[plan])
    await callback.answer(f"План: {plan_name}")
    await callback.message.answer(
        f"✅ <b>Подписка обновлена:</b> {plan_name.upper()}\nНовые лимиты уже действуют.",
        reply_markup=keyboards.back_button("main"),
    )


@router.callback_query(Nav.filter(F.section == "lang"))
async def settings_lang(callback: CallbackQuery) -> None:
    await callback.message.answer("🌐 <b>Язык интерфейса:</b>", reply_markup=keyboards.language_picker())
    await callback.answer()


@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery, user) -> None:
    lang = callback.data.split(":", 1)[1]
    async with _get_session_factory(callback.bot)() as session:
        await UserRepository(session).update(user, language_code=lang)
    await callback.answer(f"Язык: {lang}")
    await callback.message.answer(f"✅ Язык: <b>{lang}</b>", reply_markup=keyboards.back_button("main"))


@router.message(F.text == "🧠 Память")
@router.callback_query(Nav.filter(F.section == "memory"))
async def show_memory(event: Message | CallbackQuery, user) -> None:
    async with _get_session_factory(event.bot)() as session:
        memories = await MemoryRepository(session).list_by_user(user.id, limit=10)
    if not memories:
        text = (
            f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            f"┃  🧠  <b>Память пуста</b>\n"
            f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"Я начну запоминать важное, когда мы поработаем."
        )
    else:
        text = f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n┃  🧠  <b>Что я помню</b> · {len(memories)}\n┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        for m in memories:
            text += f"• <b>{m.title[:60]}</b>\n  <i>{(m.summary or m.content)[:160]}</i>\n  <code>{m.created_at.strftime('%d.%m.%Y')}</code>\n\n"
    if isinstance(event, Message):
        await event.answer(text, reply_markup=keyboards.back_button("main"))
    else:
        await event.message.answer(text, reply_markup=keyboards.back_button("main"))
        await event.answer()


@router.callback_query(Nav.filter(F.section == "memory_manage"))
async def memory_manage(callback: CallbackQuery, user) -> None:
    await show_memory(callback.message, user)
    await callback.answer()


@router.callback_query(Nav.filter(F.section == "notif"))
async def notif_settings(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "🔔 <b>Уведомления</b>\n\n"
        "Сейчас уведомления о завершении задач и деплое включены.\n"
        "(Скоро — granular controls.)",
        reply_markup=keyboards.back_button("settings"),
    )
    await callback.answer()

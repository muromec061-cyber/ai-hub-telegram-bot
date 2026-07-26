"""Admin panel — redesigned with new UI."""
from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.middlewares import AdminMiddleware
from bot.states import AdminPanel
from bot.ui import dashboard, keyboards
from bot.ui.keyboards import AdminAction, Nav
from bot.utils import _get_session_factory
from config.logging import get_logger
from db.models import UserStatus
from db.repositories import ProjectRepository, TaskRepository, UserRepository

logger = get_logger("handlers.admin")
router = Router(name="admin")
router.message.middleware(AdminMiddleware(admin_ids=[]))
router.callback_query.middleware(AdminMiddleware(admin_ids=[]))


@router.message(F.text == "🛠 Админ")
@router.message(Command("admin"))
@router.callback_query(Nav.filter(F.section == "admin"))
async def admin_panel(event: Message | CallbackQuery) -> None:
    text = (
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃  🛠  <b>Админ-панель</b>\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
    )
    if isinstance(event, Message):
        await event.answer(text, reply_markup=keyboards.admin_panel())
    else:
        await event.message.answer(text, reply_markup=keyboards.admin_panel())
        await event.answer()


@router.callback_query(AdminAction.filter())
async def admin_callback(callback: CallbackQuery, user) -> None:
    action = callback.data.split(":")[1]
    sf = _get_session_factory(callback.bot)

    if action == "system":
        async with sf() as session:
            users = await UserRepository(session).count()
            projects = await ProjectRepository(session).count()
            tasks = await TaskRepository(session).count()
        text = (
            f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            f"┃  📊  <b>Системная статистика</b>\n"
            f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"👥 Пользователей: <b>{users}</b>\n"
            f"📁 Проектов: <b>{projects}</b>\n"
            f"📋 Задач: <b>{tasks}</b>\n"
            f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
    elif action == "health":
        cluster = callback.bot._app_state["cluster"]  # type: ignore[attr-defined]
        snap = await cluster.health()
        text = dashboard.admin_health_card(snap)
    elif action == "openclaw":
        cluster = callback.bot._app_state["cluster"]  # type: ignore[attr-defined]
        oc = await cluster.openclaw()
        if not oc:
            text = "🦅 <b>OpenClaw</b>\n\n⚪ Не подключен.\n\nЗапустите OpenClaw sidecar и поставьте <code>OPENCLAW_ENABLED=true</code> + <code>OPENCLAW_GATEWAY_URL</code> в <code>.env</code>.\n\nДокументация: <code>github.com/openclaw/openclaw</code>"
        else:
            health = await oc.health()
            text = f"🦅 <b>OpenClaw</b>\n\nGateway: <code>{oc.gateway_url}</code>\nStatus: <code>{health}</code>"
    elif action == "users":
        async with sf() as session:
            users = await UserRepository(session).list(limit=20)
        text = f"👥 <b>Пользователи</b> (последние 20)\n\n"
        for u in users[:20]:
            dot = "🟢" if u.status == UserStatus.ACTIVE else "🔴"
            text += f"{dot} <code>{u.telegram_id}</code> {u.full_name} — <i>{u.role.value}</i>\n"
    elif action == "tasks":
        async with sf() as session:
            tasks = await TaskRepository(session).list(limit=20)
        text = f"📋 <b>Все задачи</b> (последние 20)\n\n"
        for t in tasks[:20]:
            text += f"#{t.id} <b>{(t.title or '')[:40]}</b> — <i>{t.status.value}</i>\n"
    elif action == "projects":
        async with sf() as session:
            projects = await ProjectRepository(session).list(limit=20)
        text = f"📁 <b>Все проекты</b> (последние 20)\n\n"
        for p in projects[:20]:
            text += f"#{p.id} <b>{p.name}</b> — <i>{p.status.value}</i>\n"
    elif action == "backup":
        from services.backup import BackupService
        result = await BackupService.create_backup()
        text = f"💾 <b>Бэкап</b>\n\n{result}"
    elif action == "logs":
        try:
            with open("logs/errors.log", "r", encoding="utf-8") as f:
                lines = f.readlines()[-30:]
            text = "📜 <b>Последние ошибки</b>\n\n" + "".join(lines[-30:]) if lines else "📜 Лог ошибок пуст."
        except FileNotFoundError:
            text = "📜 Лог ошибок пуст."
    elif action == "security":
        text = (
            "🔐 <b>Безопасность</b>\n\n"
            "✅ JWT-аутентификация\n"
            "✅ Fernet-шифрование\n"
            "✅ Bcrypt для паролей\n"
            "✅ Rate limit per user\n"
            "✅ RBAC (user/pro/team/admin/owner)\n"
            "✅ Audit log всех действий"
        )
    elif action == "broadcast":
        await callback.message.answer("📢 <b>Рассылка</b>\n\nВведи текст сообщения:")
        await AdminPanel.broadcast_message.set()
        await callback.answer()
        return
    else:
        text = "Неизвестное действие."

    await callback.message.answer(text, reply_markup=keyboards.admin_panel())
    await callback.answer()


@router.message(AdminPanel.broadcast_message)
async def admin_broadcast(message: Message, state: FSMContext, user) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пустой текст.")
        return
    await state.clear()

    async with _get_session_factory(message.bot)() as session:
        users = await UserRepository(session).list(limit=10000)

    sent = 0
    failed = 0
    for u in users:
        if u.status != UserStatus.ACTIVE:
            continue
        try:
            await message.bot.send_message(u.telegram_id, f"📢 <b>Объявление</b>\n\n{text}")
            sent += 1
        except Exception:
            failed += 1

    await message.answer(
        f"📢 <b>Рассылка завершена</b>\n\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}",
        reply_markup=keyboards.back_button("main"),
    )

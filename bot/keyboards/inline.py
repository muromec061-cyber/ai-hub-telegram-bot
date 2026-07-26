"""Inline keyboards — main menu, projects, tasks, settings, admin."""
from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class MenuCallback(CallbackData, prefix="menu"):
    action: str
    target_id: int | None = None


class TaskCallback(CallbackData, prefix="task"):
    action: str  # view, cancel, retry, delete
    task_id: int


class ProjectCallback(CallbackData, prefix="proj"):
    action: str
    project_id: int


class AdminCallback(CallbackData, prefix="adm"):
    action: str
    target_id: int | None = None


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚀 Новый проект", callback_data=MenuCallback(action="new_project").pack()),
        InlineKeyboardButton(text="📋 Мои задачи", callback_data=MenuCallback(action="tasks").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="📁 Проекты", callback_data=MenuCallback(action="projects").pack()),
        InlineKeyboardButton(text="🧠 Память", callback_data=MenuCallback(action="memory").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="💎 Подписка", callback_data=MenuCallback(action="subscription").pack()),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data=MenuCallback(action="settings").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data=MenuCallback(action="stats").pack()),
        InlineKeyboardButton(text="❓ Помощь", callback_data=MenuCallback(action="help").pack()),
    )
    return builder.as_markup()


def project_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌐 Сайт", callback_data="ptype:site"),
        InlineKeyboardButton(text="🤖 Telegram-бот", callback_data="ptype:telegram_bot"),
    )
    builder.row(
        InlineKeyboardButton(text="💻 SaaS", callback_data="ptype:saas"),
        InlineKeyboardButton(text="🛠 Утилита / скрипт", callback_data="ptype:tool"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Анализ данных", callback_data="ptype:analysis"),
        InlineKeyboardButton(text="📦 Другое", callback_data="ptype:other"),
    )
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back:main"))
    return builder.as_markup()


def subscription_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🆓 Free", callback_data="sub:free"),
        InlineKeyboardButton(text="⚡ Pro $19/мес", callback_data="sub:pro"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Team $49/мес", callback_data="sub:team"),
        InlineKeyboardButton(text="🏢 Business $199/мес", callback_data="sub:business"),
    )
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back:main"))
    return builder.as_markup()


def settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🌐 Язык", callback_data="set:lang"))
    builder.row(InlineKeyboardButton(text="🤖 Модель AI", callback_data="set:model"))
    builder.row(InlineKeyboardButton(text="🔔 Уведомления", callback_data="set:notif"))
    builder.row(InlineKeyboardButton(text="🗑 Удалить аккаунт", callback_data="set:delete"))
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back:main"))
    return builder.as_markup()


def language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
    )
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back:settings"))
    return builder.as_markup()


def model_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚡ GPT-4o mini (быстро)", callback_data="model:gpt-4o-mini"))
    builder.row(InlineKeyboardButton(text="🧠 GPT-4o (качественно)", callback_data="model:gpt-4o"))
    builder.row(InlineKeyboardButton(text="🦙 Llama 3.1 70B (self-hosted)", callback_data="model:llama3.1:70b"))
    builder.row(InlineKeyboardButton(text="☁️ Cloudflare Workers AI", callback_data="model:cf-llama"))
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back:settings"))
    return builder.as_markup()


def admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data=AdminCallback(action="users").pack()),
        InlineKeyboardButton(text="📊 Система", callback_data=AdminCallback(action="system").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Все задачи", callback_data=AdminCallback(action="tasks").pack()),
        InlineKeyboardButton(text="📁 Все проекты", callback_data=AdminCallback(action="projects").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="💾 Бэкап", callback_data=AdminCallback(action="backup").pack()),
        InlineKeyboardButton(text="📜 Логи", callback_data=AdminCallback(action="logs").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="🔐 Безопасность", callback_data=AdminCallback(action="security").pack()),
        InlineKeyboardButton(text="📢 Рассылка", callback_data=AdminCallback(action="broadcast").pack()),
    )
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back:main"))
    return builder.as_markup()


def task_actions_keyboard(task_id: int, status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if status in ("running", "queued", "testing"):
        builder.row(InlineKeyboardButton(
            text="⛔ Отменить",
            callback_data=TaskCallback(action="cancel", task_id=task_id).pack(),
        ))
    if status in ("failed", "cancelled", "timeout"):
        builder.row(InlineKeyboardButton(
            text="🔄 Повторить",
            callback_data=TaskCallback(action="retry", task_id=task_id).pack(),
        ))
    builder.row(InlineKeyboardButton(
        text="🗑 Удалить",
        callback_data=TaskCallback(action="delete", task_id=task_id).pack(),
    ))
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back:tasks"))
    return builder.as_markup()


def project_actions_keyboard(project_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="➕ Новая задача",
        callback_data=ProjectCallback(action="new_task", project_id=project_id).pack(),
    ))
    builder.row(
        InlineKeyboardButton(text="📋 Задачи", callback_data=ProjectCallback(action="tasks", project_id=project_id).pack()),
        InlineKeyboardButton(text="🚀 Деплой", callback_data=ProjectCallback(action="deploy", project_id=project_id).pack()),
    )
    builder.row(
        InlineKeyboardButton(text="📝 Изменить", callback_data=ProjectCallback(action="edit", project_id=project_id).pack()),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=ProjectCallback(action="delete", project_id=project_id).pack()),
    )
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back:projects"))
    return builder.as_markup()


def confirm_keyboard(action: str, target_id: int | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=f"confirm:{action}:{target_id or 0}"),
        InlineKeyboardButton(text="❌ Нет", callback_data="confirm:cancel"),
    )
    return builder.as_markup()


def back_keyboard(target: str = "main") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="« Назад", callback_data=f"back:{target}"))
    return builder.as_markup()

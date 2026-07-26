"""
Professional UI: redesigned keyboards, dashboards, formatting.

Все клавиатуры — современный стиль с эмодзи, иконками, разделами.
"""
from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ===== Callback factories =====
class Nav(CallbackData, prefix="nav"):
    section: str
    item_id: int | None = None


class TaskAction(CallbackData, prefix="ta"):
    action: str
    task_id: int


class ProjectAction(CallbackData, prefix="pa"):
    action: str
    project_id: int


class AdminAction(CallbackData, prefix="aa"):
    section: str
    item_id: int | None = None


# ===== Main dashboard =====
def main_dashboard(user, is_admin: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🚀  Новый проект", callback_data=Nav(section="new_project").pack()),
        InlineKeyboardButton(text="📋  Мои задачи", callback_data=Nav(section="tasks").pack()),
    )
    b.row(
        InlineKeyboardButton(text="📁  Проекты", callback_data=Nav(section="projects").pack()),
        InlineKeyboardButton(text="🧠  Память", callback_data=Nav(section="memory").pack()),
    )
    b.row(
        InlineKeyboardButton(text="🤖  Модель AI", callback_data=Nav(section="model_picker").pack()),
        InlineKeyboardButton(text="💎  Подписка", callback_data=Nav(section="subscription").pack()),
    )
    b.row(
        InlineKeyboardButton(text="⚙️  Настройки", callback_data=Nav(section="settings").pack()),
        InlineKeyboardButton(text="📊  Статистика", callback_data=Nav(section="stats").pack()),
    )
    if is_admin:
        b.row(InlineKeyboardButton(text="🛠  Админ-панель", callback_data=Nav(section="admin").pack()))
    b.row(InlineKeyboardButton(text="❓  Помощь", callback_data=Nav(section="help").pack()))
    return b.as_markup()


# ===== Project type picker =====
def project_type_picker() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🌐  Сайт / лендинг", callback_data="ptype:site"),
        InlineKeyboardButton(text="🤖  Telegram-бот", callback_data="ptype:telegram_bot"),
    )
    b.row(
        InlineKeyboardButton(text="💻  SaaS-приложение", callback_data="ptype:saas"),
        InlineKeyboardButton(text="🛠  Утилита / скрипт", callback_data="ptype:tool"),
    )
    b.row(
        InlineKeyboardButton(text="📊  Анализ данных", callback_data="ptype:analysis"),
        InlineKeyboardButton(text="📦  Другое", callback_data="ptype:other"),
    )
    b.row(InlineKeyboardButton(text="« Отмена", callback_data=Nav(section="main").pack()))
    return b.as_markup()


# ===== Project card =====
def project_card(project, has_github: bool = False, has_deploy: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text="➕  Новая задача",
        callback_data=ProjectAction(action="new_task", project_id=project.id).pack(),
    ))
    b.row(
        InlineKeyboardButton(text="📋  Задачи", callback_data=ProjectAction(action="tasks", project_id=project.id).pack()),
        InlineKeyboardButton(text="🚀  Задеплоить", callback_data=ProjectAction(action="deploy", project_id=project.id).pack()),
    )
    if has_github:
        b.row(InlineKeyboardButton(text="📦  Открыть на GitHub", url=project.github_repo_url))
    if has_deploy:
        b.row(InlineKeyboardButton(text="🌐  Открыть сайт", url=project.deployed_url))
    b.row(
        InlineKeyboardButton(text="✏️  Переименовать", callback_data=ProjectAction(action="rename", project_id=project.id).pack()),
        InlineKeyboardButton(text="🗑  Удалить", callback_data=ProjectAction(action="delete", project_id=project.id).pack()),
    )
    b.row(InlineKeyboardButton(text="« К проектам", callback_data=Nav(section="projects").pack()))
    return b.as_markup()


def project_list(projects) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    type_emoji = {
        "site": "🌐", "telegram_bot": "🤖", "saas": "💻",
        "tool": "🛠", "analysis": "📊", "general": "📦",
    }
    for p in projects[:15]:
        emoji = type_emoji.get(p.project_type, "📦")
        status_dot = {"active": "🟢", "draft": "🟡", "paused": "🟠", "completed": "✅", "failed": "🔴", "archived": "⚫"}.get(p.status.value, "•")
        b.row(InlineKeyboardButton(
            text=f"{status_dot} {emoji}  {p.name[:30]}",
            callback_data=ProjectAction(action="view", project_id=p.id).pack(),
        ))
    b.row(
        InlineKeyboardButton(text="🚀  Создать проект", callback_data=Nav(section="new_project").pack()),
    )
    b.row(InlineKeyboardButton(text="« В меню", callback_data=Nav(section="main").pack()))
    return b.as_markup()


# ===== Tasks =====
def task_list(tasks) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    status_emoji = {
        "queued": "⏳", "planning": "🧭", "running": "⚙️",
        "testing": "🧪", "completed": "✅", "failed": "❌",
        "cancelled": "🚫", "timeout": "⏰",
    }
    for t in tasks[:20]:
        emoji = status_emoji.get(t.status.value, "•")
        title = (t.title or "")[:32]
        b.row(InlineKeyboardButton(
            text=f"{emoji}  #{t.id}  {title}",
            callback_data=TaskAction(action="view", task_id=t.id).pack(),
        ))
    b.row(InlineKeyboardButton(text="« В меню", callback_data=Nav(section="main").pack()))
    return b.as_markup()


def task_card(task) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if task.status.value in ("running", "queued", "testing", "planning"):
        b.row(InlineKeyboardButton(
            text="⛔  Отменить",
            callback_data=TaskAction(action="cancel", task_id=task.id).pack(),
        ))
    if task.status.value in ("failed", "cancelled", "timeout"):
        b.row(InlineKeyboardButton(
            text="🔄  Повторить",
            callback_data=TaskAction(action="retry", task_id=task.id).pack(),
        ))
    b.row(InlineKeyboardButton(
        text="🗑  Удалить",
        callback_data=TaskAction(action="delete", task_id=task.id).pack(),
    ))
    if task.result and isinstance(task.result, dict):
        art = task.result.get("artifacts", {})
        if art.get("github_url"):
            b.row(InlineKeyboardButton(text="📦  GitHub", url=art["github_url"]))
        if art.get("deployed_url"):
            b.row(InlineKeyboardButton(text="🌐  Live", url=art["deployed_url"]))
    b.row(InlineKeyboardButton(text="« К задачам", callback_data=Nav(section="tasks").pack()))
    return b.as_markup()


# ===== Model picker =====
def model_picker(available: list[dict], active: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for m in available:
        marker = "●" if m["id"] == active else "○"
        b.row(InlineKeyboardButton(
            text=f"{marker}  {m['name']}",
            callback_data=f"model:pick:{m['id']}",
        ))
    b.row(InlineKeyboardButton(text="« В меню", callback_data=Nav(section="main").pack()))
    return b.as_markup()


# ===== Subscription =====
def subscription_picker() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🆓  Free · 100K tokens", callback_data="sub:pick:free"))
    b.row(InlineKeyboardButton(text="⚡  Pro · 5M tokens · $19/мес", callback_data="sub:pick:pro"))
    b.row(InlineKeyboardButton(text="👥  Team · 20M tokens · $49/мес", callback_data="sub:pick:team"))
    b.row(InlineKeyboardButton(text="🏢  Business · ∞ · $199/мес", callback_data="sub:pick:business"))
    b.row(InlineKeyboardButton(text="« В меню", callback_data=Nav(section="main").pack()))
    return b.as_markup()


# ===== Settings =====
def settings_panel() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🌐  Язык интерфейса", callback_data=Nav(section="lang").pack()))
    b.row(InlineKeyboardButton(text="🔔  Уведомления", callback_data=Nav(section="notif").pack()))
    b.row(InlineKeyboardButton(text="🧠  Долговременная память", callback_data=Nav(section="memory_manage").pack()))
    b.row(InlineKeyboardButton(text="🗑  Удалить аккаунт", callback_data="set:confirm_delete"))
    b.row(InlineKeyboardButton(text="« В меню", callback_data=Nav(section="main").pack()))
    return b.as_markup()


def language_picker() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🇷🇺  Русский", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇬🇧  English", callback_data="lang:en"),
    )
    b.row(InlineKeyboardButton(text="« Настройки", callback_data=Nav(section="settings").pack()))
    return b.as_markup()


# ===== Admin =====
def admin_panel() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="📊  Система", callback_data=AdminAction(section="system").pack()),
        InlineKeyboardButton(text="👥  Пользователи", callback_data=AdminAction(section="users").pack()),
    )
    b.row(
        InlineKeyboardButton(text="📋  Все задачи", callback_data=AdminAction(section="tasks").pack()),
        InlineKeyboardButton(text="📁  Все проекты", callback_data=AdminAction(section="projects").pack()),
    )
    b.row(
        InlineKeyboardButton(text="💾  Бэкап", callback_data=AdminAction(section="backup").pack()),
        InlineKeyboardButton(text="📜  Логи", callback_data=AdminAction(section="logs").pack()),
    )
    b.row(
        InlineKeyboardButton(text="🔐  Безопасность", callback_data=AdminAction(section="security").pack()),
        InlineKeyboardButton(text="📢  Рассылка", callback_data=AdminAction(section="broadcast").pack()),
    )
    b.row(
        InlineKeyboardButton(text="🤖  OpenClaw", callback_data=AdminAction(section="openclaw").pack()),
        InlineKeyboardButton(text="🏥  Health", callback_data=AdminAction(section="health").pack()),
    )
    b.row(InlineKeyboardButton(text="« В меню", callback_data=Nav(section="main").pack()))
    return b.as_markup()


def back_button(target: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=f"« Назад", callback_data=Nav(section=target).pack()))
    return b.as_markup()

"""
Text-formatted dashboards — full visual redesign.

Все "экраны" бота используют эти шаблоны. Консистентный стиль:
- Большие заголовки с эмодзи
- Карточки с обрамлением
- Прогресс-бары
- Иконки статусов
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from db.models.project import Project, ProjectStatus
from db.models.task import Task, TaskStatus
from db.models.user import User

DIVIDER = "─" * 32
THIN = "·" * 32

STATUS_DOT = {
    "active": "🟢", "draft": "🟡", "paused": "🟠",
    "completed": "✅", "failed": "🔴", "archived": "⚫",
    "queued": "⏳", "planning": "🧭", "running": "⚙️",
    "testing": "🧪", "cancelled": "🚫", "timeout": "⏰",
    "blocked": "⛔", "pending": "🟡",
}

TYPE_EMOJI = {
    "site": "🌐", "telegram_bot": "🤖", "saas": "💻",
    "tool": "🛠", "analysis": "📊", "general": "📦",
    "other": "📦",
}


def welcome_card(user: User, is_admin: bool = False) -> str:
    role = "👑 Owner" if user.role.value == "owner" else (
        "🛠 Admin" if user.role.value == "admin" else (
            "👥 Team" if user.role.value == "team" else (
                "⚡ Pro" if user.role.value == "pro" else "🆓 Free"
            )
        )
    )
    hour = datetime.utcnow().hour
    greet = "Доброй ночи" if hour < 6 else "Доброе утро" if hour < 12 else "Добрый день" if hour < 18 else "Добрый вечер"
    return (
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃  <b>{greet}, {user.full_name}!</b>\n"
        f"┃  <i>AI-стартап-команда к твоим услугам</i>\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"👤 <b>Аккаунт:</b> {role}\n"
        f"🆔 <code>{user.telegram_id}</code>\n"
        f"{DIVIDER}\n\n"
        f"🚀 <b>Что я могу прямо сейчас:</b>\n"
        f"  • Создать сайт, Telegram-бота, SaaS\n"
        f"  • Написать и протестировать код\n"
        f"  • Задеплоить на Cloudflare / GitHub\n"
        f"  • Запомнить твои предпочтения\n"
        f"  • Работать 24/7 без перерыва\n\n"
        f"💡 <b>Совет:</b> просто напиши, что хочешь построить — "
        f"я сам выберу нужного агента.\n\n"
        f"👇 <i>Выбирай раздел:</i>"
    )


def projects_card(projects: list[Project]) -> str:
    if not projects:
        return (
            f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            f"┃  📁  <b>Проектов пока нет</b>\n"
            f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"🚀 Нажми <b>«Новый проект»</b>, чтобы начать."
        )
    lines = [
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
        f"┃  📁  <b>Твои проекты</b> · {len(projects)}",
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
        "",
    ]
    for i, p in enumerate(projects[:15], 1):
        emoji = TYPE_EMOJI.get(p.project_type, "📦")
        dot = STATUS_DOT.get(p.status.value, "•")
        created = p.created_at.strftime("%d.%m") if p.created_at else ""
        lines.append(f"<b>{i}.</b> {dot} {emoji} <b>{p.name}</b>  <i>· {created}</i>")
        if p.description:
            lines.append(f"     <i>{p.description[:60]}{'…' if len(p.description) > 60 else ''}</i>")
        if p.deployed_url:
            lines.append(f"     🌐 <code>{p.deployed_url}</code>")
    return "\n".join(lines)


def project_card(project: Project) -> str:
    emoji = TYPE_EMOJI.get(project.project_type, "📦")
    dot = STATUS_DOT.get(project.status.value, "•")
    lines = [
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
        f"┃  {dot} {emoji}  <b>{project.name}</b>",
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
        "",
    ]
    if project.description:
        lines.append(f"📝 <b>Описание:</b>\n{project.description[:400]}")
        lines.append("")
    lines.append(f"🏷  <b>Тип:</b> {project.project_type}")
    lines.append(f"📊  <b>Статус:</b> {dot} {project.status.value}")
    lines.append(f"📅  <b>Создан:</b> {project.created_at.strftime('%d.%m.%Y %H:%M') if project.created_at else '—'}")
    if project.github_repo_url:
        lines.append(f"📦  <b>Repo:</b> <code>{project.github_repo_url}</code>")
    if project.deployed_url:
        lines.append(f"🌐  <b>Live:</b> <code>{project.deployed_url}</code>")
    if project.tags:
        lines.append(f"🏷  <b>Теги:</b> {', '.join(project.tags[:8])}")
    return "\n".join(lines)


def tasks_card(tasks: list[Task]) -> str:
    if not tasks:
        return (
            f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            f"┃  📋  <b>Задач пока нет</b>\n"
            f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
        )
    lines = [
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
        f"┃  📋  <b>Твои задачи</b> · {len(tasks)}",
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
        "",
    ]
    for t in tasks[:20]:
        dot = STATUS_DOT.get(t.status.value, "•")
        title = (t.title or "(без названия)")[:50]
        when = t.created_at.strftime("%d.%m %H:%M") if t.created_at else ""
        lines.append(f"{dot} <b>#{t.id}</b>  {title}")
        lines.append(f"     <i>{t.status.value} · {when}</i>")
    return "\n".join(lines)


def task_card(task: Task, runs: Iterable | None = None) -> str:
    dot = STATUS_DOT.get(task.status.value, "•")
    lines = [
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
        f"┃  {dot}  <b>Задача #{task.id}</b>",
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
        "",
        f"📝 <b>Описание:</b>\n{task.description[:500]}",
        "",
    ]
    lines.append(f"📊  <b>Статус:</b> {dot} <code>{task.status.value}</code>")
    lines.append(f"🔥  <b>Приоритет:</b> {task.priority.value}")
    lines.append(f"🔁  <b>Попыток:</b> {task.attempts}/{task.max_attempts}")
    lines.append(f"📅  <b>Создана:</b> {task.created_at.strftime('%d.%m.%Y %H:%M') if task.created_at else '—'}")
    if task.started_at:
        lines.append(f"▶️  <b>Старт:</b> {task.started_at.strftime('%d.%m %H:%M:%S')}")
    if task.completed_at:
        lines.append(f"⏹  <b>Финиш:</b> {task.completed_at.strftime('%d.%m %H:%M:%S')}")
    if task.error:
        lines.append(f"\n❌ <b>Ошибка:</b>\n<code>{task.error[:400]}</code>")
    if task.result and isinstance(task.result, dict):
        art = task.result.get("artifacts", {})
        if art:
            lines.append(f"\n📦 <b>Артефакты:</b>")
            if art.get("github_url"):
                lines.append(f"  • Repo: <code>{art['github_url']}</code>")
            if art.get("deployed_url"):
                lines.append(f"  • Live: <code>{art['deployed_url']}</code>")
            if art.get("files"):
                lines.append(f"  • Файлов: {len(art['files'])}")
    if runs:
        runs = list(runs)
        if runs:
            lines.append(f"\n🤖 <b>Агент-раны ({len(runs)}):</b>")
            for r in runs[-5:]:
                lines.append(f"  • <b>{r.agent_name}</b> — {r.status.value} · {r.duration_ms}ms")
    return "\n".join(lines)


def stats_card(user: User, sub, project_count: int, task_count: int, running_count: int) -> str:
    plan_name = {
        "free": "🆓 Free", "pro": "⚡ Pro", "team": "👥 Team", "business": "🏢 Business"
    }.get(sub.plan.value if sub else "free", "—")
    tokens_pct = 0
    if sub and sub.monthly_tokens:
        tokens_pct = int(100 * sub.tokens_used / sub.monthly_tokens)
    bar = "█" * int(tokens_pct / 5) + "░" * (20 - int(tokens_pct / 5))
    return (
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃  📊  <b>Твоя статистика</b>\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"💎 <b>План:</b> {plan_name}\n"
        f"📁 <b>Проектов:</b> {project_count}\n"
        f"📋 <b>Задач всего:</b> {task_count}\n"
        f"⚙️  <b>В работе сейчас:</b> {running_count}\n\n"
        f"🔥 <b>Токены в этом месяце:</b>\n"
        f"  <code>{bar}</code>  {tokens_pct}%\n"
        f"  {sub.tokens_used:,} / {sub.monthly_tokens:,}"
    )


def admin_health_card(snap: dict) -> str:
    lines = [
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
        f"┃  🏥  <b>Состояние системы</b>",
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
        "",
        f"🤖  <b>LLM:</b> <code>{snap.get('llm', '—')}</code>",
    ]
    oc = snap.get("openclaw")
    if isinstance(oc, dict):
        dot = "🟢" if oc.get("ok") else "🔴"
        lines.append(f"🦅  <b>OpenClaw:</b> {dot} <code>{oc.get('status', oc.get('error', '—'))}</code>")
    elif oc is None:
        lines.append(f"🦅  <b>OpenClaw:</b> ⚪ не подключен")
    lines.append(f"🐙  <b>GitHub:</b> {'🟢' if snap.get('github') else '⚪'}")
    lines.append(f"☁️  <b>Cloudflare:</b> {'🟢' if snap.get('cloudflare') else '⚪'}")
    return "\n".join(lines)

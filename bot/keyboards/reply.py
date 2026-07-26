"""Reply keyboards — main commands shown as buttons."""
from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def main_reply_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🚀 Новый проект"),
        KeyboardButton(text="📋 Задачи"),
    )
    builder.row(
        KeyboardButton(text="📁 Проекты"),
        KeyboardButton(text="🧠 Память"),
    )
    builder.row(
        KeyboardButton(text="💎 Подписка"),
        KeyboardButton(text="⚙️ Настройки"),
    )
    if is_admin:
        builder.row(KeyboardButton(text="🛠 Админ"))
    builder.row(KeyboardButton(text="❓ Помощь"))
    return builder.as_markup(resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)

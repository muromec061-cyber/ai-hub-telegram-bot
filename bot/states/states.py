"""FSM states for multi-step user flows."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ProjectCreation(StatesGroup):
    name = State()
    description = State()
    type = State()
    tech_stack = State()


class NewTask(StatesGroup):
    project = State()
    description = State()


class Settings(StatesGroup):
    language = State()
    model = State()


class AdminPanel(StatesGroup):
    broadcast_message = State()
    user_search = State()

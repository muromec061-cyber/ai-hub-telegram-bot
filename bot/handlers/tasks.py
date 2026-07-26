"""Task handlers — list, view, cancel, retry (redesigned)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.ui import dashboard, keyboards
from bot.ui.keyboards import Nav, TaskAction
from bot.utils import _get_session_factory
from config.logging import get_logger
from db.models.task import TaskStatus
from db.repositories import AgentRunRepository, TaskRepository

logger = get_logger("handlers.tasks")
router = Router(name="tasks")


@router.message(F.text == "📋 Задачи")
@router.callback_query(Nav.filter(F.section == "tasks"))
async def list_tasks(event: Message | CallbackQuery, user) -> None:
    async with _get_session_factory(event.bot)() as session:
        repo = TaskRepository(session)
        tasks = await repo.list_by_user(user.id, limit=20)
    text = dashboard.tasks_card(tasks)
    kb = keyboards.task_list(tasks) if tasks else keyboards.back_button("main")
    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb)
    else:
        await event.message.answer(text, reply_markup=kb)
        await event.answer()


@router.callback_query(TaskAction.filter(F.action == "view"))
async def task_view(callback: CallbackQuery, callback_data: TaskAction, user) -> None:
    async with _get_session_factory(callback.bot)() as session:
        task_repo = TaskRepository(session)
        run_repo = AgentRunRepository(session)
        task = await task_repo.get(callback_data.task_id)
        if not task or task.creator_id != user.id:
            await callback.answer("Задача не найдена", show_alert=True)
            return
        runs = await run_repo.list_by_task(task.id)
    text = dashboard.task_card(task, runs)
    await callback.message.answer(text, reply_markup=keyboards.task_card(task))
    await callback.answer()


@router.callback_query(TaskAction.filter(F.action == "cancel"))
async def task_cancel(callback: CallbackQuery, callback_data: TaskAction, user) -> None:
    async with _get_session_factory(callback.bot)() as session:
        task_repo = TaskRepository(session)
        task = await task_repo.get(callback_data.task_id)
        if not task or task.creator_id != user.id:
            await callback.answer("Задача не найдена", show_alert=True)
            return
        await task_repo.set_status(task.id, TaskStatus.CANCELLED)

    from bot.bot import get_app
    app = get_app()
    if app.get("task_queue"):
        app["task_queue"].cancel(callback_data.task_id)

    await callback.answer("Задача отменена")
    await callback.message.edit_text(
        f"🚫 <b>Задача #{callback_data.task_id} отменена.</b>",
        reply_markup=keyboards.back_button("tasks"),
    )


@router.callback_query(TaskAction.filter(F.action == "retry"))
async def task_retry(callback: CallbackQuery, callback_data: TaskAction, user) -> None:
    async with _get_session_factory(callback.bot)() as session:
        task_repo = TaskRepository(session)
        task = await task_repo.get(callback_data.task_id)
        if not task or task.creator_id != user.id:
            await callback.answer("Задача не найдена", show_alert=True)
            return
        await task_repo.set_status(task.id, TaskStatus.QUEUED, error=None, attempts=0)

    from bot.bot import get_app
    app = get_app()
    if app.get("task_queue"):
        await app["task_queue"].submit(
            callback_data.task_id, user.id, task.description, project_id=task.project_id,
        )

    await callback.answer("Задача перезапущена")
    await callback.message.edit_text(
        f"🔄 <b>Задача #{callback_data.task_id} перезапущена.</b>",
        reply_markup=keyboards.back_button("tasks"),
    )


@router.callback_query(TaskAction.filter(F.action == "delete"))
async def task_delete(callback: CallbackQuery, callback_data: TaskAction, user) -> None:
    async with _get_session_factory(callback.bot)() as session:
        task_repo = TaskRepository(session)
        task = await task_repo.get(callback_data.task_id)
        if not task or task.creator_id != user.id:
            await callback.answer("Задача не найдена", show_alert=True)
            return
        await task_repo.delete(task.id)
    await callback.answer("Удалено")
    await callback.message.edit_text(
        f"🗑 <b>Задача #{callback_data.task_id} удалена.</b>",
        reply_markup=keyboards.back_button("tasks"),
    )

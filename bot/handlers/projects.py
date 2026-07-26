"""Project creation and management — redesigned."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.states import NewTask, ProjectCreation
from bot.ui import anim, dashboard, keyboards
from bot.ui.anim import typing_indicator
from bot.ui.keyboards import Nav, ProjectAction
from bot.utils import _get_session_factory
from config.logging import get_logger
from db.models import ProjectStatus, get_session
from db.models.user import UserRole
from db.repositories import ProjectRepository, TaskRepository

logger = get_logger("handlers.projects")
router = Router(name="projects")


@router.message(F.text == "🚀 Новый проект")
@router.message(Command("new"))
@router.callback_query(Nav.filter(F.section == "new_project"))
async def new_project_start(event: Message | CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProjectCreation.name)
    text = (
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "┃  🚀  <b>Новый проект</b>\n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        "Как назовём проект? <i>(короткое имя, 3-50 символов)</i>"
    )
    if isinstance(event, Message):
        await event.answer(text)
    else:
        await event.message.answer(text)
        await event.answer()


@router.message(ProjectCreation.name)
async def project_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()[:200]
    if not name:
        await message.answer("Имя не может быть пустым. Попробуй ещё раз:")
        return
    await state.update_data(name=name)
    await state.set_state(ProjectCreation.description)
    await message.answer(
        f"Окей, <b>{name}</b>.\n\n"
        f"📝 <b>Опиши, что нужно сделать</b> — подробно:\n\n"
        f"<i>Например: «Сайт-портфолио с тремя страницами: главная, "
        f"проекты, контакты. Тёмная тема, адаптивный дизайн»</i>"
    )


@router.message(ProjectCreation.description)
async def project_description(message: Message, state: FSMContext) -> None:
    description = (message.text or "").strip()[:4000]
    if not description:
        await message.answer("Описание не может быть пустым:")
        return
    await state.update_data(description=description)
    await state.set_state(ProjectCreation.type)
    await message.answer("Выбери тип проекта:", reply_markup=keyboards.project_type_picker())


@router.callback_query(F.data.startswith("ptype:"))
async def project_type_chosen(callback: CallbackQuery, state: FSMContext, user) -> None:
    ptype = callback.data.split(":", 1)[1]
    data = await state.get_data()
    name = data.get("name", f"project-{user.telegram_id}")
    description = data.get("description", "")
    await state.clear()

    async with _get_session_factory(callback.bot)() as session:
        repo = ProjectRepository(session)
        project = await repo.create(
            owner_id=user.id,
            name=name,
            description=description,
            project_type=ptype,
            status=ProjectStatus.ACTIVE,
            tags=[ptype],
        )
        project_id = project.id

    text = (
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃  ✅  <b>Проект создан!</b>\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"📁 <b>{name}</b>\n"
        f"📝 {description[:200]}\n"
        f"🏷 Тип: {ptype}\n\n"
        f"Готов поставить первую задачу?"
    )
    await callback.message.answer(text, reply_markup=keyboards.project_card(project))
    await callback.answer("✅ Проект создан!")


@router.message(F.text == "📁 Проекты")
@router.callback_query(Nav.filter(F.section == "projects"))
async def list_projects(event: Message | CallbackQuery, user) -> None:
    async with _get_session_factory(event.bot)() as session:
        repo = ProjectRepository(session)
        projects = await repo.list_active(user.id)
    text = dashboard.projects_card(projects)
    kb = keyboards.project_list(projects) if projects else keyboards.back_button("main")
    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb)
    else:
        await event.message.answer(text, reply_markup=kb)
        await event.answer()


@router.callback_query(ProjectAction.filter(F.action == "view"))
async def project_view(callback: CallbackQuery, callback_data: ProjectAction, user) -> None:
    async with _get_session_factory(callback.bot)() as session:
        proj_repo = ProjectRepository(session)
        task_repo = TaskRepository(session)
        project = await proj_repo.get(callback_data.project_id)
        if not project or project.owner_id != user.id:
            await callback.answer("Проект не найден", show_alert=True)
            return
        tasks = await task_repo.list_by_project(project.id)
    text = dashboard.project_card(project)
    if tasks:
        text += f"\n\n📋 <b>Задач:</b> {len(tasks)}"
    await callback.message.answer(
        text,
        reply_markup=keyboards.project_card(
            project,
            has_github=bool(project.github_repo_url),
            has_deploy=bool(project.deployed_url),
        ),
    )
    await callback.answer()


@router.callback_query(ProjectAction.filter(F.action == "new_task"))
async def new_task_in_project(callback: CallbackQuery, callback_data: ProjectAction, state: FSMContext) -> None:
    await state.set_state(NewTask.project)
    await state.update_data(project_id=callback_data.project_id)
    await callback.message.answer(
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃  ➕  <b>Новая задача</b>\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"Опиши задачу подробно — что должен сделать агент:"
    )
    await callback.answer()


@router.message(NewTask.description)
async def new_task_description(message: Message, state: FSMContext, user) -> None:
    description = (message.text or "").strip()
    if not description:
        await message.answer("Опиши задачу:")
        return
    data = await state.get_data()
    project_id = data.get("project_id")
    await state.clear()

    from bot.bot import get_app
    app = get_app()
    async with _get_session_factory(message.bot)() as session:
        task_repo = TaskRepository(session)
        task = await task_repo.create(
            creator_id=user.id,
            project_id=project_id,
            title=description[:200],
            description=description,
        )
        task_id = task.id

    status_msg = await message.answer("⚙️ Запускаю агентов…")
    await app["task_queue"].submit(task_id, user.id, description, project_id=project_id)

    for i in range(2):
        await anim.progress_sleep(0.8)
        try:
            await status_msg.edit_text(f"{anim.spinner_frame(i)} Запускаю агентов…")
        except Exception:
            break

    try:
        await status_msg.delete()
    except Exception:
        pass

    await message.answer(
        f"✅ <b>Задача #{task_id} поставлена в очередь!</b>\n\n"
        f"📝 <i>{description[:200]}</i>\n\n"
        f"⚙️  Команда агентов приступила к работе.\n"
        f"🔔 Уведомление придёт, когда будет готово.",
        reply_markup=keyboards.main_dashboard(_dummy_user(), is_admin=False),
    )


def _dummy_user():
    from types import SimpleNamespace
    return SimpleNamespace(full_name="Friend", role=UserRole.USER, telegram_id=0)

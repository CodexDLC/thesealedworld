from typing import Any

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from codex_bot.director import Director
from codex_bot.helper.id_inspector import inspect_ids_handler
from loguru import logger as log

router = Router(name="commands_router")


@router.message(CommandStart())
async def cmd_start(message: Message, director: Director) -> None:
    """
    Handles /start command.

    Uses 'Director' to transition to the main 'commands' or 'bot_menu' scene.
    Director automatically handles state changes and passes context to the orchestrator.
    """
    if not message.from_user:
        return

    log.info(f"Start command received from user {message.from_user.id}")

    # Launch the initial scene via Director
    view_dto = await director.set_scene("commands", payload=message.from_user)

    # Note: container is cast to Any to access project-specific services like view_sender
    container: Any = director.container
    if view_dto and hasattr(container, "view_sender"):
        await container.view_sender.send(view_dto)


@router.message(Command("menu"))
async def cmd_menu(message: Message, director: Director) -> None:
    """
    Direct access to the dashboard.

    Bypass manual orchestration and use 'set_scene' for standard transition.
    """
    if not message.from_user:
        return

    log.debug(f"Menu command received from user {message.from_user.id}")

    view_dto = await director.set_scene("bot_menu")

    container: Any = director.container
    if view_dto and hasattr(container, "view_sender"):
        await container.view_sender.send(view_dto)


# --- Developer Tools ---
# You can safely comment out or delete this command in production
router.message(Command("id"))(inspect_ids_handler)
router.channel_post(Command("id"))(inspect_ids_handler)

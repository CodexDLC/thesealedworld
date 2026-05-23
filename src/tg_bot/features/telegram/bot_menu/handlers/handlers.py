from typing import Any

from aiogram import Router
from aiogram.types import CallbackQuery
from codex_bot.director import Director
from loguru import logger as log

from ..resources.callbacks import DashboardCallback

router = Router(name="bot_menu_router")


@router.callback_query(DashboardCallback.filter())
async def handle_dashboard_callback(
    call: CallbackQuery,
    callback_data: DashboardCallback,
    director: Director,
) -> None:
    """
    Unified handler for all dashboard interactions.

    The 'Director' object is automatically injected by DirectorMiddleware.
    """
    if not call.from_user:
        return

    await call.answer()

    log.bind(action=callback_data.action, session_key=director.session_key).info("BotMenuActionTriggered")

    # Access container via director to reach the orchestrator
    container: Any = director.container

    # We use get_feature if available, or direct features access
    orchestrator = getattr(container, "features", {}).get("bot_menu")

    if not orchestrator:
        log.bind(feature_key="bot_menu").error("BotMenuOrchestratorMissing")
        return

    view_dto = await orchestrator.handle_callback(director, payload=callback_data)

    if view_dto and hasattr(container, "view_sender"):
        await container.view_sender.send(view_dto)

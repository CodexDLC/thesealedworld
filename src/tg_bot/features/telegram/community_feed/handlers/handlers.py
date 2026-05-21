from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram_i18n import I18nContext
from codex_bot.director import Director

from ..feature_setting import CommunityFeedStates

if TYPE_CHECKING:
    from ..logic.orchestrator import CommunityFeedOrchestrator

log = logging.getLogger(__name__)

router = Router(name="_router")


@router.message(Command(""))
@router.message(CommunityFeedStates.main)
async def handle__entry(
    message: types.Message,
    director: Director,
    orchestrator: CommunityFeedOrchestrator,
    i18n: I18nContext,
) -> Any:
    """
    Main entry handler for the CommunityFeed feature.
    """
    log.debug(f"CommunityFeed | Command Handler | user_id={message.from_user.id if message.from_user else 'unknown'}")

    # Example of calling the orchestrator for rendering
    view = await orchestrator.handle_entry(director=director)
    return await view.send(message, i18n=i18n)


@router.message(F.chat.type.in_({"group", "supergroup"}), F.text | F.caption)
async def handle_group_message(
    message: types.Message,
    director: Director,
    orchestrator: CommunityFeedOrchestrator,
) -> None:
    """Intercepts and moderates public group messages, then publishes to Redis Stream."""
    log.debug(f"CommunityFeed | Group message from chat={message.chat.id}")
    await orchestrator.process_group_message(message, director.container)

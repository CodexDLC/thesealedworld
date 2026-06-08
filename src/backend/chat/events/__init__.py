from __future__ import annotations

from typing import TYPE_CHECKING, Any

from codex_platform.streams import StreamRouter
from loguru import logger as log

if TYPE_CHECKING:
    from fastapi import FastAPI

router = StreamRouter()
_app: FastAPI | None = None


class ChatEvents:
    SYSTEM_MESSAGE = "chat.system_message"
    # NOTE: ``chat.combat_log_message`` was the legacy event that mirrored
    # combat output into the chat system tab. Stage 1 of the player realtime
    # gateway removes that mirror — combat UI consumes its own DTOs/fragments
    # and the stage-2 ``player.notice`` surface will replace any cross-feature
    # combat notifications. The constant is intentionally absent so new code
    # cannot subscribe.


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on("character_session.location_changed", group="chat")
async def on_location_changed(payload: dict[str, Any]) -> None:
    if _app is None:
        return
    char_id = payload.get("char_id")
    location_id = str(payload.get("current", ""))
    if not char_id or not location_id:
        return
    try:
        # Resolve user UUID from the reverse mapping stored on WS connect
        user_uuid = await _app.state.redis.get(f"chat:char_to_user:{char_id}")
        if user_uuid:
            await _app.state.chat_sessions.set_location(user_uuid, location_id)
    except Exception:
        log.bind(char_id=char_id).exception("ChatLocationUpdateFailed")


@router.on(ChatEvents.SYSTEM_MESSAGE, group="chat")
async def on_system_message(payload: dict[str, Any]) -> None:
    """Receive system notification from main backend, deliver to player(s) via WS."""
    if _app is None:
        log.warning("ChatSystemMessageIgnored")
        return

    content: str = payload.get("content", "")
    character_ids: list[str] = payload.get("character_ids") or []
    if not character_ids and payload.get("character_id"):
        character_ids = [str(payload["character_id"])]

    if not character_ids or not content:
        return

    msg_service = getattr(_app.state, "msg_service", None)
    if msg_service is None:
        from src.backend.chat.services.message_service import MessageService

        msg_service = MessageService(_app.state.chat_manager, _app.state.redis)

    for cid in character_ids:
        try:
            await msg_service.push_system(cid, content)
        except Exception:
            log.bind(char_id=cid).exception("ChatSystemMessagePushFailed")


__all__ = ["ChatEvents", "bind", "router"]

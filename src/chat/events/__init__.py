from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from codex_platform.streams import StreamRouter

if TYPE_CHECKING:
    from fastapi import FastAPI

router = StreamRouter()
_app: FastAPI | None = None
log = logging.getLogger(__name__)


class ChatEvents:
    SYSTEM_MESSAGE = "chat.system_message"


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
        log.exception("Failed to update chat location for char_id=%s", char_id)


@router.on(ChatEvents.SYSTEM_MESSAGE, group="chat")
async def on_system_message(payload: dict[str, Any]) -> None:
    """Receive system notification from main backend, deliver to player(s) via WS."""
    if _app is None:
        log.warning("chat.system_message ignored: app not bound")
        return

    content: str = payload.get("content", "")
    character_ids: list[str] = payload.get("character_ids") or []
    if not character_ids and payload.get("character_id"):
        character_ids = [str(payload["character_id"])]

    if not character_ids or not content:
        return

    msg_service = _app.state.get("msg_service")
    if msg_service is None:
        from src.chat.services.message_service import MessageService

        msg_service = MessageService(_app.state.chat_manager, _app.state.redis)

    for cid in character_ids:
        try:
            await msg_service.push_system(cid, content)
        except Exception:
            log.exception("Failed to push system message to character %s", cid)


__all__ = ["ChatEvents", "bind", "router"]

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from codex_platform.streams import StreamRouter
from loguru import logger as log

if TYPE_CHECKING:
    from fastapi import FastAPI

router = StreamRouter()
_app: FastAPI | None = None


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on("player.notice", group="realtime")
async def on_player_notice(payload: dict[str, Any]) -> None:
    """Deliver a player-facing notice to the recipient's live socket."""
    if _app is None:
        log.warning("RealtimePlayerNoticeIgnored")
        return
    await _app.state.realtime_notice_service.deliver(payload)


__all__ = ["bind", "router"]

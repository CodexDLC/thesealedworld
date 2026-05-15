from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from codex_platform.streams import StreamRouter

from src.backend.core.database.session import get_session_context
from src.backend.features.tavern.integrations import TavernSystemIntegrator
from src.backend.features.tavern.repositories import TavernRoomRepository
from src.backend.features.tavern.services import TavernService

if TYPE_CHECKING:
    from fastapi import FastAPI

router = StreamRouter()
_app: FastAPI | None = None
log = logging.getLogger(__name__)


class TavernEvents:
    ROOM_GRANT_REQUESTED = "tavern.room_grant_requested"
    ROOM_GRANTED = "tavern.room_granted"
    ROOM_GRANT_FAILED = "tavern.room_grant_failed"


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on(TavernEvents.ROOM_GRANT_REQUESTED, group="tavern", reply=True)
async def on_room_grant_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        log.warning("Tavern room grant ignored: app_not_bound cid=%s", cid)
        return

    try:
        char_id = int(payload["char_id"])
        tavern_id = str(payload["tavern_id"])
        room_key = str(payload.get("room_key") or "")
        async with get_session_context() as session:
            service = TavernService(
                integrator=TavernSystemIntegrator(
                    room_repository=TavernRoomRepository(session),
                ),
            )
            room, created = await service.grant_room(
                char_id=char_id,
                tavern_id=tavern_id,
                room_key=room_key,
            )
            await session.commit()
        ack: dict[str, Any] = {
            "status": "ok",
            "char_id": char_id,
            "tavern_id": room.tavern_id,
            "room_id": room.id,
            "room_key": room.room_key,
            "room_status": room.status,
            "created": created,
        }
        await _app.state.events.publish(TavernEvents.ROOM_GRANTED, ack, correlation_id=cid)
    except Exception as exc:  # noqa: BLE001
        log.exception("Tavern room grant failed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(TavernEvents.ROOM_GRANT_FAILED, {"request": payload, **ack})
        except Exception:
            log.exception("Tavern room grant failure event delivery failed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            log.exception("Tavern room grant ack delivery failed: cid=%s", cid)


__all__ = ["TavernEvents", "bind", "router"]

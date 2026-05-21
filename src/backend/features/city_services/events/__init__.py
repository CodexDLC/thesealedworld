from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from codex_core.common.log_context import clear_log_context, set_log_context
from codex_platform.streams import StreamRouter
from loguru import logger

from src.backend.core.database.session import get_session_context
from src.backend.features.city_services.integrations import CityServiceSystemIntegrator
from src.backend.features.city_services.repositories import TavernRoomRepository
from src.backend.features.city_services.services import CityService

if TYPE_CHECKING:
    from fastapi import FastAPI

router = StreamRouter()
_app: FastAPI | None = None


def with_log_context(
    handler: Callable[[dict[str, Any]], Awaitable[None]],
) -> Callable[[dict[str, Any]], Awaitable[None]]:
    async def wrapped(payload: dict[str, Any]) -> None:
        set_log_context(correlation_id=payload.get("correlation_id"))
        try:
            await handler(payload)
        finally:
            clear_log_context()

    return wrapped


class CityServiceEvents:
    TAVERN_ROOM_GRANT_REQUESTED = "tavern.room_grant_requested"
    TAVERN_ROOM_GRANTED = "tavern.room_granted"
    TAVERN_ROOM_GRANT_FAILED = "tavern.room_grant_failed"


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on(CityServiceEvents.TAVERN_ROOM_GRANT_REQUESTED, group="city_services", reply=True)
@with_log_context
async def on_tavern_room_grant_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        logger.warning("CityServiceTavernRoomGrantIgnored")
        return

    try:
        char_id = int(payload["char_id"])
        tavern_id = str(payload["tavern_id"])
        room_key = str(payload.get("room_key") or "")
        async with get_session_context() as session:
            service = CityService(
                integrator=CityServiceSystemIntegrator(
                    room_repository=TavernRoomRepository(session),
                ),
            )
            room, created = await service.grant_tavern_room(
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
        await _app.state.events.publish(CityServiceEvents.TAVERN_ROOM_GRANTED, ack, correlation_id=cid)
    except Exception as exc:  # noqa: BLE001
        logger.exception("CityServiceTavernRoomGrantFailed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(CityServiceEvents.TAVERN_ROOM_GRANT_FAILED, {"request": payload, **ack})
        except Exception:
            logger.exception("CityServiceTavernRoomGrantFailureEventDeliveryFailed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            logger.exception("CityServiceTavernRoomGrantAckDeliveryFailed")


__all__ = ["CityServiceEvents", "bind", "router"]

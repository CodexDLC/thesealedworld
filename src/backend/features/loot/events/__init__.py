from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.core.bus import GameStreamRouter
from src.backend.features.loot.integrations import LOOT_ORDER_REQUESTED, LootIntegration
from src.backend.features.loot.runtime.loot_engine import LootEngine
from src.backend.features.loot.services.loot_service import LootService
from src.backend.infrastructure.loot.managers.loot_manager import LootManager

if TYPE_CHECKING:
    from fastapi import FastAPI

router = GameStreamRouter()
_app: FastAPI | None = None


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on(LOOT_ORDER_REQUESTED, group="loot")
async def on_order_requested(payload: dict[str, Any]) -> None:
    if _app is None:
        logger.warning("Loot order request ignored: app_not_bound")
        return

    session_id = str(payload.get("session_id") or "")
    if not session_id:
        logger.warning("Loot order request ignored: missing_session_id")
        return

    location_id = str(payload.get("location_id") or "unknown")
    battle_type = str(payload.get("battle_type") or "")
    actors = _decode_actors(payload.get("actors_json"))
    if not actors:
        logger.warning("Loot order request ignored: empty_actors session={}", session_id)
        return

    manager = LootManager(_app.state.redis)
    integration = LootIntegration(manager, events=_app.state.events)
    service = LootService(integration, LootEngine())
    corpse_ids_by_actor = await service.order_loot_for_combat(
        session_id=session_id,
        actors=actors,
        location_id=location_id,
        battle_type=battle_type,
    )
    if corpse_ids_by_actor:
        await integration.save_pending_actor_corpses(session_id, corpse_ids_by_actor)

    logger.info(
        "LootOrderStream | session={} generated={} location={}",
        session_id,
        len(corpse_ids_by_actor),
        location_id,
    )


def _decode_actors(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, list):
        return [actor for actor in value if isinstance(actor, dict)]
    try:
        decoded = json.loads(str(value))
    except json.JSONDecodeError:
        logger.warning("Loot order request ignored invalid actors_json")
        return []
    if not isinstance(decoded, list):
        return []
    return [actor for actor in decoded if isinstance(actor, dict)]


__all__ = ["bind", "on_order_requested", "router"]

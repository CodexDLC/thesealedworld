from __future__ import annotations

from typing import Any

from loguru import logger as log

from src.backend.features.loot.integrations.loot_integration import LootIntegration
from src.backend.features.loot.runtime.loot_engine import LootEngine
from src.backend.features.loot.services.loot_service import LootService
from src.backend.infrastructure.loot.managers.loot_manager import LootManager


async def loot_order_task(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    """
    Background task: pre-generate invisible loot corpses at the start of combat.

    Triggered by combat executor on first move (idempotency guard via Redis SET NX).
    Corpses remain invisible until loot.activate_requested is published by victory_finalizer.

    payload:
        session_id  — combat session ID
        actors      — list of actor snapshots (from CombatDataService.get_actors_batch)
        location_id — location where corpses should appear
        battle_type — combat battle type
    """
    session_id: str = str(payload.get("session_id", ""))
    actors: list[dict] = payload.get("actors") or []
    location_id: str = str(payload.get("location_id", "unknown"))
    battle_type: str = str(payload.get("battle_type") or "")

    if not session_id:
        log.error("LootOrderTask | missing session_id in payload")
        return

    log.info("LootOrderTask | session={} location={} actors={}", session_id, location_id, len(actors))

    redis_service = ctx.get("redis_service")
    if redis_service is None:
        log.error("LootOrderTask | redis_service not in context")
        return

    manager = LootManager(redis_service)
    integration = LootIntegration(manager)  # no events needed for generation
    service = LootService(integration, LootEngine())

    corpse_ids_by_actor = await service.order_loot_for_combat(
        session_id=session_id,
        actors=actors,
        location_id=location_id,
        battle_type=battle_type,
    )

    log.info(
        "LootOrderTask | session={} generated {} corpses at {}",
        session_id,
        len(corpse_ids_by_actor),
        location_id,
    )

    # Store actor_id -> corpse_id so victory_finalizer can activate only actually dead actors.
    # Uses a short-lived Redis key (session lifetime ~24h matches invisible corpse TTL).
    if corpse_ids_by_actor:
        client = manager._client()
        key = f"loot:pending:{session_id}"
        import json

        await client.set(key, json.dumps(corpse_ids_by_actor), ex=86400)

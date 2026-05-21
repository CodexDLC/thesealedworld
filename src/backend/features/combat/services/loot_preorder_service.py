from __future__ import annotations

from typing import Any

from loguru import logger

_NON_LOOT_BATTLE_TYPES = {"arena", "pvp", "pvp_arena", "shadow"}


class CombatLootPreorderService:
    """Schedules hidden monster corpses for non-arena combats."""

    def __init__(self, loot_orders: Any | None) -> None:
        self._loot_orders = loot_orders

    async def enqueue(
        self,
        *,
        combat_id: str,
        battle_type: str,
        location_id: str,
        actors: dict[str, dict[str, Any]],
    ) -> None:
        if self._loot_orders is None:
            return
        if not combat_id or battle_type.lower() in _NON_LOOT_BATTLE_TYPES:
            return

        monster_actors = [
            {**actor, "actor_id": str(actor_id)}
            for actor_id, actor in actors.items()
            if (actor.get("meta") or {}).get("type") == "monster"
        ]
        if not monster_actors:
            return

        await self._loot_orders.order_hidden_corpses(
            session_id=combat_id,
            battle_type=battle_type,
            location_id=location_id,
            actors=monster_actors,
        )
        logger.bind(combat_id=combat_id, monster_count=len(monster_actors), location_id=location_id).info(
            "CombatLootPreorderRequested"
        )

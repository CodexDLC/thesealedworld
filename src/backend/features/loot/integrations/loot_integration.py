from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from loguru import logger as log

if TYPE_CHECKING:
    from src.backend.core.bus import GameEventProducer
    from src.backend.infrastructure.loot.managers.loot_manager import LootManager
    from src.shared.schemas.loot import ClaimResultDTO, CorpseDTO, LootContainerDTO


ITEMS_GENERATE_REQUESTED = "items.generate_requested"


class LootIntegration:
    def __init__(
        self, manager: LootManager, events: GameEventProducer | None = None, game_config: Any | None = None
    ) -> None:
        self._manager = manager
        self._events = events
        self._game_config = game_config

    # ------------------------------------------------------------------
    # Corpse lifecycle
    # ------------------------------------------------------------------

    async def persist_corpse(self, corpse: CorpseDTO, location_id: str) -> None:
        invisible_ttl = 86400.0
        if self._game_config is not None:
            invisible_ttl = await self._game_config.get_float("loot", "INVISIBLE_TTL_SEC", default=86400.0)
        await self._manager.save_corpse(corpse, location_id, ttl=invisible_ttl)

    async def activate_corpses(self, corpse_ids: list[str], char_ids: list[int], location_id: str) -> None:
        public_delay = 900.0
        public_window = 3600.0
        if self._game_config is not None:
            public_delay = await self._game_config.get_float("loot", "PUBLIC_DELAY_SEC", default=900.0)
            public_window = await self._game_config.get_float("loot", "PUBLIC_WINDOW_SEC", default=3600.0)

        now = time.time()
        public_at = now + public_delay
        decay_at = public_at + public_window
        ttl = int(public_at - now) + public_window

        for corpse_id in corpse_ids:
            await self._manager.patch_corpse(
                corpse_id,
                {
                    "$.is_visible": True,
                    "$.locked_to": char_ids,
                    "$.timestamps.public_at": public_at,
                    "$.timestamps.decay_at": decay_at,
                },
            )
            await self._manager.set_ttl(corpse_id, ttl)

    async def get_location_loot(self, location_id: str) -> LootContainerDTO:
        return await self._manager.get_location_loot(location_id)

    async def get_corpse(self, corpse_id: str) -> CorpseDTO | None:
        return await self._manager.get_corpse(corpse_id)

    async def mark_items_claimed(self, corpse_id: str, claim: ClaimResultDTO) -> CorpseDTO | None:
        updated = await self._manager.remove_items_from_corpse(
            corpse_id,
            instance_ids=set(claim.instance_ids),
            resource_template_ids=set(claim.resource_deltas.keys()),
        )
        if updated is not None and updated.is_empty:
            empty_ttl = 300.0
            if self._game_config is not None:
                empty_ttl = await self._game_config.get_float("loot", "EMPTY_CORPSE_TTL_SEC", default=300.0)
            await self._manager.set_ttl(corpse_id, empty_ttl)
        return updated

    # ------------------------------------------------------------------
    # Idempotency guard
    # ------------------------------------------------------------------

    async def mark_loot_ordered(self, session_id: str) -> bool:
        return await self._manager.mark_loot_ordered(session_id)

    async def clear_loot_ordered(self, session_id: str) -> None:
        await self._manager.clear_loot_ordered(session_id)

    async def is_loot_ordered(self, session_id: str) -> bool:
        return await self._manager.is_loot_ordered(session_id)

    async def save_pending_actor_corpses(self, session_id: str, corpse_ids_by_actor: dict[str, str]) -> None:
        await self._manager.save_pending_actor_corpses(session_id, corpse_ids_by_actor)

    # ------------------------------------------------------------------
    # Item Service RPC
    # ------------------------------------------------------------------

    async def request_item_instance(
        self,
        base_id: str,
        tier: int,
        source_context: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Request a persisted ItemInstance from Item Service via Redis Streams.
        Sends base_id + exact tier (already rolled with ±1 by LootEngine).
        Rarity, affixes, name — all decided by Item Service.
        """
        if self._events is None:
            log.warning("LootItemInstanceRequestSkipped")
            return None

        payload: dict[str, Any] = {
            "base_id": base_id,
            "rarity_tier": tier,
            "generation_mode": "player",
            "placement_ref": {
                "holder_type": "system",
                "holder_id": "loot",
                "storage_type": "backpack",
            },
            "source": "loot_drop",
            "source_context": source_context or {},
            "request_ai_text": True,
            "return_item": False,
        }

        try:
            response = await self._events.request(ITEMS_GENERATE_REQUESTED, payload, timeout=15.0)
            if isinstance(response, dict) and response.get("status") == "ok":
                ids = response.get("item_ids") or []
                return str(ids[0]) if ids else None
            log.bind(response=response).warning("LootItemRpcNonOk")
            return None
        except Exception:
            log.bind(base_id=base_id).exception("LootItemRpcFailed")
            return None

    # ------------------------------------------------------------------
    # Claim validation
    # ------------------------------------------------------------------

    def can_claim(self, corpse: CorpseDTO, char_id: int) -> bool:
        if not corpse.is_visible:
            return False
        if not corpse.locked_to:
            return True
        return char_id in corpse.locked_to or corpse.is_public

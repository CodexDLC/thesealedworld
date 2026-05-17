from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from loguru import logger as log

if TYPE_CHECKING:
    from src.backend.core.bus import GameEventProducer
    from src.backend.infrastructure.loot.managers.loot_manager import LootManager
    from src.shared.schemas.loot import ClaimResultDTO, CorpseDTO, LootContainerDTO

_PUBLIC_DELAY_SEC = 900
_PUBLIC_WINDOW_SEC = 3600
_INVISIBLE_TTL_SEC = 86400
_EMPTY_CORPSE_TTL_SEC = 300

ITEMS_GENERATE_REQUESTED = "items.generate_requested"


class LootIntegration:
    def __init__(self, manager: LootManager, events: GameEventProducer | None = None) -> None:
        self._manager = manager
        self._events = events

    # ------------------------------------------------------------------
    # Corpse lifecycle
    # ------------------------------------------------------------------

    async def persist_corpse(self, corpse: CorpseDTO, location_id: str) -> None:
        await self._manager.save_corpse(corpse, location_id, ttl=_INVISIBLE_TTL_SEC)

    async def activate_corpses(self, corpse_ids: list[str], char_ids: list[int], location_id: str) -> None:
        now = time.time()
        public_at = now + _PUBLIC_DELAY_SEC
        decay_at = public_at + _PUBLIC_WINDOW_SEC
        ttl = int(public_at - now) + _PUBLIC_WINDOW_SEC

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
            await self._manager.set_ttl(corpse_id, _EMPTY_CORPSE_TTL_SEC)
        return updated

    # ------------------------------------------------------------------
    # Idempotency guard
    # ------------------------------------------------------------------

    async def mark_loot_ordered(self, session_id: str) -> bool:
        return await self._manager.mark_loot_ordered(session_id)

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
            log.warning("LootIntegration | no events producer, cannot request item instance")
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
            "return_item": False,
        }

        try:
            response = await self._events.request(ITEMS_GENERATE_REQUESTED, payload, timeout=15.0)
            if isinstance(response, dict) and response.get("status") == "ok":
                ids = response.get("item_ids") or []
                return str(ids[0]) if ids else None
            log.warning("LootIntegration | item RPC non-ok: {}", response)
            return None
        except Exception as exc:
            log.error("LootIntegration | item RPC failed base_id={}: {}", base_id, exc)
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

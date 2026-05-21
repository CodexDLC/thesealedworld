from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from loguru import logger as log

from src.backend.features.inventory.repositories.items import runtime_item_from_instance
from src.backend.features.inventory.services.inventory_service import InventoryActionError, InventoryService
from src.backend.features.inventory.services.projection import BACKPACK_STORAGE, build_runtime_session
from src.backend.features.items.dto.instance import ItemGenerationRequestDTO, ItemOriginRefDTO, ItemPlacementRefDTO
from src.backend.features.items.events.publisher import ItemEvents
from src.backend.features.items.services.catalog_service import ItemCatalogService

if TYPE_CHECKING:
    from src.backend.core.bus import GameEventProducer
    from src.backend.features.inventory.repositories.items import InventoryItemRepository
    from src.backend.features.inventory.services.session_manager import InventorySessionManager
    from src.shared.schemas.inventory import InventoryRuntimeSessionDTO


@dataclass(slots=True)
class InventoryRewardGrantResult:
    item_ids: list[str]
    equipped_item_ids: list[str]
    backpack_item_ids: list[str]

    def model_dump(self) -> dict[str, Any]:
        return {
            "item_ids": self.item_ids,
            "equipped_item_ids": self.equipped_item_ids,
            "backpack_item_ids": self.backpack_item_ids,
        }


class InventoryRewardService:
    """Inventory-owned reward grant flow.

    Items creates item instances. Inventory owns the final character placement,
    equipment conflict rules, Redis inventory cache, and active character items
    projection.
    """

    def __init__(
        self,
        *,
        repository: InventoryItemRepository,
        inventory_sessions: InventorySessionManager,
        inventory_service: InventoryService,
        events: GameEventProducer,
        catalog: ItemCatalogService | None = None,
    ) -> None:
        self.repository = repository
        self.inventory_sessions = inventory_sessions
        self.inventory_service = inventory_service
        self.events = events
        self.catalog = catalog or ItemCatalogService.load_default()

    async def grant_scenario_rewards(
        self,
        *,
        char_id: int,
        item_ids: list[str] | None = None,
        base_item_ids: list[str] | None = None,
        quest_key: str,
        equip_if_possible: bool = True,
    ) -> InventoryRewardGrantResult:
        item_ids = [item_id for item_id in (item_ids or []) if item_id]
        if not item_ids:
            item_ids = await self._generate_reward_items(char_id, base_item_ids or [], quest_key)
        if not item_ids:
            return InventoryRewardGrantResult(item_ids=[], equipped_item_ids=[], backpack_item_ids=[])

        session = await self._build_session(char_id)
        equipped_item_ids: list[str] = []

        if equip_if_possible:
            for item_id in item_ids:
                if self._equip_reward(session, item_id):
                    equipped_item_ids.append(item_id)

        await self.repository.save_placements(char_id, session.by_id)
        await self.repository.flush()
        await self._refresh_runtime_state(session)

        equipped = set(equipped_item_ids)
        return InventoryRewardGrantResult(
            item_ids=item_ids,
            equipped_item_ids=equipped_item_ids,
            backpack_item_ids=[item_id for item_id in item_ids if item_id not in equipped],
        )

    async def _build_session(self, char_id: int) -> InventoryRuntimeSessionDTO:
        rows = await self.repository.list_character_items(char_id)
        runtime_items = [runtime_item_from_instance(instance, placement) for instance, placement in rows]
        return build_runtime_session(char_id, runtime_items)

    async def _generate_reward_items(self, char_id: int, base_item_ids: list[str], quest_key: str) -> list[str]:
        base_item_ids = [base_id for base_id in base_item_ids if base_id]
        if not base_item_ids:
            return []

        requests = [
            ItemGenerationRequestDTO(
                base_id=base_id,
                rarity_tier=0,
                source=f"scenario:{quest_key}",
                char_id=char_id,
                request_ai_text=False,
                placement_ref=ItemPlacementRefDTO(
                    holder_type="character",
                    holder_id=str(char_id),
                    storage_type=BACKPACK_STORAGE,
                    slot=None,
                ),
                origin_ref=ItemOriginRefDTO(origin_type="scenario", origin_ref=quest_key),
                delivery_mode="forward",
                return_item=False,
            ).model_dump(mode="json")
            for base_id in base_item_ids
        ]
        response = await self.events.request(
            ItemEvents.GENERATE_REQUESTED,
            {"items": requests, "delivery_mode": "forward", "return_items": False},
            timeout=30.0,
        )
        if not isinstance(response, dict) or response.get("status") != "ok":
            raise RuntimeError(f"Inventory reward item generation failed: {response!r}")
        item_ids = [str(item_id) for item_id in response.get("item_ids", [])]
        if len(item_ids) != len(base_item_ids):
            raise RuntimeError(
                "Inventory reward item generation returned an unexpected item count: "
                f"expected={len(base_item_ids)} actual={len(item_ids)}"
            )
        return item_ids

    def _equip_reward(self, session: InventoryRuntimeSessionDTO, item_id: str) -> bool:
        item = session.by_id.get(item_id)
        if item is None:
            log.bind(char_id=session.char_id, item_id=item_id).warning("InventoryRewardItemMissing")
            return False

        slot_id = item.slot or str(item.mechanics.get("slot") or "")
        if not slot_id:
            return False

        try:
            self.inventory_service._equip(session, item_id, slot_id)
        except InventoryActionError:
            log.bind(char_id=session.char_id, item_id=item_id, slot_id=slot_id).info("InventoryRewardKeptInBackpack")
            return False
        return True

    async def _refresh_runtime_state(self, session: InventoryRuntimeSessionDTO) -> None:
        if await self.inventory_sessions.get(session.char_id) is not None:
            await self.inventory_sessions.set(session)
        await self.inventory_service._sync_active_character_items(session, reason="reward_granted")


__all__ = ["InventoryRewardGrantResult", "InventoryRewardService"]

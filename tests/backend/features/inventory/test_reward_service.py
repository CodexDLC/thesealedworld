from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.character.managers.session import CharacterSessionManager
from src.backend.features.inventory.services.inventory_service import InventoryService
from src.backend.features.inventory.services.reward_service import InventoryRewardService
from src.backend.features.inventory.services.session_manager import InventorySessionManager
from src.backend.features.items.events.publisher import ItemEvents
from src.shared.schemas.inventory import InventoryRuntimeItemDTO


class FakeInventoryRepository:
    def __init__(self, items: list[InventoryRuntimeItemDTO]) -> None:
        self.items = {item.item_id: item for item in items}
        self.saved: dict[str, InventoryRuntimeItemDTO] | None = None
        self.flushed = False

    async def list_character_items(self, char_id: int, *, expedition_run_id: str | None = None):
        return [(FakeInstance(item), FakePlacement(item)) for item in self.items.values()]

    async def save_placements(
        self,
        char_id: int,
        items: dict[str, InventoryRuntimeItemDTO],
        *,
        expedition_run_id: str | None = None,
    ) -> None:
        self.saved = items
        self.items = dict(items)

    async def flush(self) -> None:
        self.flushed = True

    async def commit(self) -> None:
        raise AssertionError("Reward service should not commit inside the shared event session")


class FakeInstance:
    def __init__(self, item: InventoryRuntimeItemDTO) -> None:
        self.id = item.item_id
        self.base_id = item.base_id
        self.item_type = item.item_type
        self.rarity = item.rarity
        self.rarity_tier = item.rarity_tier
        self.name = item.name
        self.description = item.description
        self.mechanics = item.mechanics
        self.generation = {"narrative_tags": item.tags}
        self.metadata_ = item.metadata
        self.appearance = item.metadata


class FakePlacement:
    def __init__(self, item: InventoryRuntimeItemDTO) -> None:
        self.holder_type = "character"
        self.storage_type = item.placement
        self.slot = item.slot if item.placement != "backpack" else None


@pytest.mark.asyncio
async def test_reward_service_generates_to_backpack_then_applies_inventory_equip_rules(
    fake_redis_service,
    fake_redis_client,
):
    fake_redis_client.store["game:ac:7"] = {"char_id": 7, "state": "scenario", "items": {}, "sessions": {}}
    fake_redis_client.store["game:inventory:7"] = {
        "char_id": 7,
        "layout": {"equipment": {"main_hand": "old-sword"}, "belt": {}, "backpack": []},
        "by_id": {
            "old-sword": _item("old-sword", "sword", placement="equipped").model_dump(mode="json"),
        },
        "is_dirty": False,
        "version": 1,
        "updated_at": 0.0,
    }
    repository = FakeInventoryRepository(
        [
            _item("old-sword", "sword", placement="equipped"),
            _item("new-sword", "sword", placement="backpack"),
        ]
    )
    events = MagicMock()
    events.request = AsyncMock(return_value={"status": "ok", "item_ids": ["new-sword"]})
    inventory_sessions = InventorySessionManager(fake_redis_service)
    inventory_service = InventoryService(
        repository=repository,
        inventory_sessions=inventory_sessions,
        character_sessions=CharacterSessionManager(fake_redis_service),
    )

    result = await InventoryRewardService(
        repository=repository,
        inventory_sessions=inventory_sessions,
        inventory_service=inventory_service,
        events=events,
    ).grant_scenario_rewards(
        char_id=7,
        base_item_ids=["sword"],
        quest_key="awakening_rift",
    )

    assert result.item_ids == ["new-sword"]
    assert result.equipped_item_ids == ["new-sword"]
    assert result.backpack_item_ids == []
    event_type, payload = events.request.await_args.args[:2]
    assert event_type == ItemEvents.GENERATE_REQUESTED
    assert payload["items"][0]["placement_ref"]["storage_type"] == "backpack"
    assert payload["items"][0]["placement_ref"]["slot"] is None
    assert repository.saved is not None
    assert repository.saved["new-sword"].placement == "equipped"
    assert repository.saved["new-sword"].slot == "main_hand"
    assert repository.saved["old-sword"].placement == "backpack"
    assert repository.saved["old-sword"].slot is None
    assert repository.flushed is True
    assert fake_redis_client.store["game:inventory:7"]["layout"]["equipment"]["main_hand"] == "new-sword"
    assert fake_redis_client.store["game:ac:7"]["items"]["layout"]["equipment"]["main_hand"] == "new-sword"


def _item(item_id: str, base_id: str, *, placement: str) -> InventoryRuntimeItemDTO:
    return InventoryRuntimeItemDTO(
        item_id=item_id,
        base_id=base_id,
        item_type="weapon",
        slot="main_hand" if placement == "equipped" else None,
        valid_slots=["main_hand"],
        placement=placement,
        name=item_id,
        mechanics={"slot": "main_hand", "valid_slots": ["main_hand"], "power": 1},
    )

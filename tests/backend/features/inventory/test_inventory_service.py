from __future__ import annotations

import pytest

from src.backend.features.character.managers.session import CharacterSessionManager
from src.backend.features.inventory.services.inventory_service import InventoryActionForbiddenError, InventoryService
from src.backend.features.inventory.services.session_manager import InventorySessionManager
from src.shared.schemas.inventory import InventoryActionRequestDTO, InventoryRuntimeItemDTO


class FakeInventoryRepository:
    def __init__(self, items: list[InventoryRuntimeItemDTO]) -> None:
        self.items = items
        self.saved: dict[str, InventoryRuntimeItemDTO] | None = None
        self.committed = False

    async def list_character_items(self, char_id: int):
        return [(FakeInstance(item), FakePlacement(item)) for item in self.items]

    async def save_placements(self, char_id: int, items: dict[str, InventoryRuntimeItemDTO]) -> None:
        self.saved = items

    async def commit(self) -> None:
        self.committed = True


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


class FakePlacement:
    def __init__(self, item: InventoryRuntimeItemDTO) -> None:
        self.storage_type = item.placement
        self.slot = item.slot


@pytest.mark.asyncio
async def test_open_window_creates_redis_session_and_active_character_projection(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="exploration")
    service = _service(
        fake_redis_service,
        [
            _item("sword-1", "weapon", slot="main_hand", placement="equipped"),
            _item("cloak-1", "garment", slot="outer_garment", placement="equipped"),
        ],
    )

    window = await service.open_window(7)

    assert window.can_act is True
    assert fake_redis_client.store["game:inventory:7"]["layout"]["equipment"]["main_hand"] == "sword-1"
    assert fake_redis_client.store["game:ac:7"]["items"]["layout"]["equipment"]["outer_garment"] == "cloak-1"
    assert fake_redis_client.ttls["game:inventory:7"] == 3600


@pytest.mark.asyncio
async def test_inventory_action_is_forbidden_in_scenario_state(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="scenario")
    service = _service(fake_redis_service, [_item("sword-1", "weapon", slot="main_hand")])

    with pytest.raises(InventoryActionForbiddenError) as exc:
        await service.apply_action(
            InventoryActionRequestDTO(char_id=7, action="equip", item_id="sword-1", slot_id="main_hand")
        )

    assert exc.value.payload.code == "inventory_action_forbidden"
    assert exc.value.payload.state == "scenario"


@pytest.mark.asyncio
async def test_equip_action_updates_inventory_session_and_active_character_items(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="exploration")
    service = _service(fake_redis_service, [_item("boots-1", "garment", slot="feetwear")])

    await service.apply_action(
        InventoryActionRequestDTO(char_id=7, action="equip", item_id="boots-1", slot_id="feetwear")
    )

    inventory_doc = fake_redis_client.store["game:inventory:7"]
    active_doc = fake_redis_client.store["game:ac:7"]
    assert inventory_doc["is_dirty"] is True
    assert inventory_doc["layout"]["equipment"]["feetwear"] == "boots-1"
    assert active_doc["items"]["layout"]["equipment"]["feetwear"] == "boots-1"


@pytest.mark.asyncio
async def test_move_to_belt_requires_capacity_and_consumable_compatibility(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="exploration")
    service = _service(
        fake_redis_service,
        [
            _item(
                "belt-1",
                "accessory",
                slot="belt_accessory",
                placement="equipped",
                mechanics={"implicit_bonuses": {"quick_slot_capacity": 2}, "valid_slots": ["belt_accessory"]},
            ),
            _item(
                "potion-1",
                "consumable",
                slot=None,
                mechanics={"is_quick_slot_compatible": True, "valid_slots": []},
            ),
        ],
    )

    await service.apply_action(
        InventoryActionRequestDTO(char_id=7, action="move_to_belt", item_id="potion-1", slot_id="belt_slot_2")
    )

    active_doc = fake_redis_client.store["game:ac:7"]
    assert active_doc["items"]["layout"]["belt"]["belt_slot_2"] == "potion-1"


@pytest.mark.asyncio
async def test_close_window_flushes_dirty_session_and_removes_redis_key(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="exploration")
    repository = FakeInventoryRepository([_item("boots-1", "garment", slot="feetwear")])
    service = _service(fake_redis_service, repository.items, repository=repository)

    await service.apply_action(
        InventoryActionRequestDTO(char_id=7, action="equip", item_id="boots-1", slot_id="feetwear")
    )
    await service.close_window(7)

    assert repository.saved is not None
    assert repository.committed is True
    assert "game:inventory:7" not in fake_redis_client.store


def _service(
    fake_redis_service,
    items: list[InventoryRuntimeItemDTO],
    *,
    repository: FakeInventoryRepository | None = None,
) -> InventoryService:
    return InventoryService(
        repository=repository or FakeInventoryRepository(items),
        inventory_sessions=InventorySessionManager(fake_redis_service),
        character_sessions=CharacterSessionManager(fake_redis_service),
    )


def _active_character(fake_redis_client, *, state: str) -> None:
    fake_redis_client.store["game:ac:7"] = {
        "char_id": 7,
        "state": state,
        "bio": {"name": "Ada", "avatar": "/avatar.png"},
        "sessions": {},
        "items": {},
    }


def _item(
    item_id: str,
    item_type: str,
    *,
    slot: str | None,
    placement: str = "backpack",
    mechanics: dict | None = None,
) -> InventoryRuntimeItemDTO:
    mechanics = mechanics or {"valid_slots": [slot] if slot else []}
    return InventoryRuntimeItemDTO(
        item_id=item_id,
        base_id=item_id.split("-")[0],
        item_type=item_type,
        slot=slot if placement != "backpack" else None,
        valid_slots=list(mechanics.get("valid_slots") or ([slot] if slot else [])),
        placement=placement,
        name=item_id,
        mechanics=mechanics,
    )

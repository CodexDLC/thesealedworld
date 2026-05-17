from __future__ import annotations

import pytest

from src.backend.features.character.managers.session import CharacterSessionManager
from src.backend.features.inventory.services.inventory_service import InventoryActionForbiddenError, InventoryService
from src.backend.features.inventory.services.session_manager import InventorySessionManager
from src.shared.schemas.inventory import InventoryActionRequestDTO, InventoryRuntimeItemDTO, WalletDTO


class FakeInventoryRepository:
    def __init__(
        self,
        items: list[InventoryRuntimeItemDTO],
        wallet: WalletDTO | None = None,
        expedition_wallet: WalletDTO | None = None,
    ) -> None:
        self.items = items
        self.wallet = wallet or WalletDTO()
        self.expedition_wallet = expedition_wallet or WalletDTO()
        self.saved: dict[str, InventoryRuntimeItemDTO] | None = None
        self.committed = False

    async def list_character_items(self, char_id: int, *, expedition_run_id: str | None = None):
        return [(FakeInstance(item), FakePlacement(item)) for item in self.items]

    async def get_wallet(self, char_id: int) -> WalletDTO:
        return self.wallet

    async def get_expedition_wallet(self, run_id: str) -> WalletDTO:
        return self.expedition_wallet

    async def save_placements(
        self,
        char_id: int,
        items: dict[str, InventoryRuntimeItemDTO],
        *,
        expedition_run_id: str | None = None,
    ) -> None:
        self.saved = items

    async def save_item_mechanics(self, items: dict[str, InventoryRuntimeItemDTO]) -> None:
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
        self.appearance = item.metadata


class FakePlacement:
    def __init__(self, item: InventoryRuntimeItemDTO) -> None:
        self.holder_type = "expedition" if item.is_unsecured or item.sync_state == "unsecured" else "character"
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
    assert set(fake_redis_client.store["game:ac:7"]["items"]["by_id"]) == {"sword-1", "cloak-1"}
    assert fake_redis_client.ttls["game:inventory:7"] == 3600


@pytest.mark.asyncio
async def test_open_window_calculates_inventory_slots_from_strength_and_belt(
    fake_redis_service,
    fake_redis_client,
):
    _active_character(fake_redis_client, state="exploration", attributes={"strength": 12})
    service = _service(
        fake_redis_service,
        [
            _item(
                "belt-1",
                "accessory",
                slot="belt_accessory",
                placement="equipped",
                mechanics={
                    "power": 6,
                    "implicit_bonuses": {
                        "quick_slot_capacity": 2,
                    },
                    "valid_slots": ["belt_accessory"],
                },
            ),
            _item(
                "ore-1",
                "resource",
                slot=None,
                mechanics={"valid_slots": []},
                metadata={"width_cells": 2, "height_cells": 1},
            ),
        ],
    )

    window = await service.open_window(7)

    assert window.stats.slots_total == 48
    assert window.stats.slots_used == 2
    assert sum(not slot.enabled for slot in window.quick_slots) == 6


@pytest.mark.asyncio
async def test_open_window_maps_real_item_card_fields(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="exploration")
    service = _service(
        fake_redis_service,
        [
            _item(
                "axe-1",
                "weapon",
                slot="main_hand",
                mechanics={"valid_slots": ["main_hand", "off_hand"], "weight_units": 3.5},
                metadata={"width_cells": 4, "height_cells": 2, "quantity": 2, "icon_key": "axe"},
            ),
            _item(
                "helm-1",
                "armor",
                slot="head_armor",
                placement="equipped",
                mechanics={"valid_slots": ["head_armor"]},
                metadata={"volume_units": 5},
            ),
        ],
    )

    window = await service.open_window(7)

    axe = next(row for row in window.visible_rows if row.item_id == "axe-1")
    assert axe.quantity == 2
    assert axe.weight == "3.5"
    assert axe.grid_w == 4
    assert axe.grid_h == 2
    assert axe.equip_target == "main_hand"
    assert axe.valid_slots == ["main_hand", "off_hand"]
    assert axe.icon == "weapon_axe"
    assert all(row.item_id != "helm-1" for row in window.visible_rows)
    assert window.body_zones[0].primary_slot.item.item_id == "helm-1"


@pytest.mark.asyncio
async def test_open_window_uses_distinct_legwear_and_feetwear_icons(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="exploration")
    service = _service(
        fake_redis_service,
        [
            _item("pants-1", "garment", slot="legs_garment"),
            _item("boots-1", "garment", slot="feetwear"),
            _item("greaves-1", "armor", slot="legs_armor"),
        ],
    )

    window = await service.open_window(7)

    rows = {row.item_id: row for row in window.visible_rows}
    assert rows["pants-1"].icon == "legwear"
    assert rows["boots-1"].icon == "feetwear"
    assert rows["greaves-1"].icon == "legs"


@pytest.mark.asyncio
async def test_open_window_uses_weapon_family_icons_and_two_hand_slot(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="exploration")
    service = _service(
        fake_redis_service,
        [
            _item("sword-1", "weapon", slot="main_hand", tags=["sword"]),
            _item("dagger-1", "weapon", slot="main_hand", tags=["dagger"]),
            _item("battle_axe-1", "weapon", slot="main_hand", tags=["axe"]),
            _item("greatsword-1", "weapon", slot="two_hand", placement="equipped", tags=["two_handed"]),
        ],
    )

    window = await service.open_window(7)

    rows = {row.item_id: row for row in window.visible_rows}
    assert rows["sword-1"].icon == "weapon_sword"
    assert rows["dagger-1"].icon == "weapon_dagger"
    assert rows["battle_axe-1"].icon == "weapon_axe"
    assert len(window.weapon_slots) == 1
    assert window.weapon_slots[0].slot_id == "two_hand"
    assert window.weapon_slots[0].label == "Две руки"
    assert window.weapon_slots[0].item.item_id == "greatsword-1"


@pytest.mark.asyncio
async def test_open_window_builds_structured_item_tooltip_without_html(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="exploration")
    service = _service(
        fake_redis_service,
        [
            _item(
                "old-axe",
                "weapon",
                slot="main_hand",
                placement="equipped",
                mechanics={
                    "valid_slots": ["main_hand"],
                    "power": 5,
                    "implicit_bonuses": {"initiative": 1, "parry_chance": 0.04},
                },
                rarity_tier=1,
            ),
            _item(
                "new-axe",
                "weapon",
                slot="main_hand",
                mechanics={
                    "valid_slots": ["main_hand"],
                    "power": 9,
                    "implicit_bonuses": {"initiative": 3, "parry_chance": 0.12, "stamina_regen": -1},
                    "affixes": [
                        {"affix_id": "crit_chance", "value": 0.045, "source": "single:combat_offense"},
                        {
                            "affix_id": "control_resistance_bonus",
                            "value": 0.0125,
                            "source": "single:combat_control",
                        },
                        {
                            "affix_id": "armor_penetration_pct_bonus",
                            "value": 0.0147,
                            "source": "single:combat_offense",
                        },
                    ],
                    "bonuses": {"physical_damage_bonus": 99},
                    "effects": ["void_touched"],
                    "requirements": [{"label": "STR", "value": "12", "current": "14", "met": True}],
                },
                metadata={"flavor_text": "A clean tooltip payload.", "source": "test"},
                rarity="epic",
                rarity_tier=4,
                description="Structured item details.",
                tags=["two_handed"],
            ),
        ],
    )

    window = await service.open_window(7)

    row = next(row for row in window.visible_rows if row.item_id == "new-axe")
    details = row.details
    assert details is not None
    assert row.rarity_tier == 4
    assert row.rarity_label == "Эпический"
    assert details.description == "Structured item details."
    assert details.flavor == "A clean tooltip payload."
    assert details.item_type_label == "Оружие"
    assert any(line.label == "Урон" and line.value == "9" and line.tone == "neutral" for line in details.details)
    assert any(
        line.label == "Парирование" and line.value == "12%" and line.tone == "neutral" for line in details.details
    )
    assert any(
        line.label == "Сопротивление контролю" and line.value == "+1.25%" and line.tier == 4
        for line in details.affixes
    )
    assert any(
        line.label == "Пробитие брони" and line.value == "+1.47%" and line.tier == 4
        for line in details.affixes
    )
    assert any(
        line.label == "Урон" and line.value == "+4" and line.delta == 4 and line.tone == "positive"
        for line in details.comparison
    )
    assert any(
        line.label == "Парирование" and line.value == "+8%" and line.delta == pytest.approx(0.08)
        for line in details.comparison
    )
    assert any(
        line.label == "Пробитие брони" and line.value == "+1.47%" and line.tier == 4
        for line in details.affixes
    )
    assert all(line.label != "Физический урон" for line in details.details)
    assert any(
        line.label == "Урон" and line.value == "+4" and line.delta == 4 and line.tone == "positive"
        for line in details.comparison
    )
    assert any(
        line.label == "Парирование" and line.value == "+8%" and line.delta == pytest.approx(0.08)
        for line in details.comparison
    )
    assert details.effects[0].label == "Void Touched"
    assert details.tags[0].label == "two_handed"
    assert details.requirements[0].met is True
    assert any(field.label == "Источник" and field.value == "test" for field in details.meta)
    assert details.actions[0].action == "equip"
    assert details.actions[0].slot_id == "main_hand"
    dumped = details.model_dump_json()
    assert "<" not in dumped
    assert "item-card" not in dumped


@pytest.mark.asyncio
async def test_open_window_includes_wallet_resources_from_loot_claim(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="exploration")
    service = _service(
        fake_redis_service,
        [],
        repository=FakeInventoryRepository(
            [],
            wallet=WalletDTO(
                currency={"currency_dust": 3},
                resources={"res_torn_pelt": 2, "res_animal_bones": 1},
            ),
        ),
    )

    window = await service.open_window(7)

    rows = {row.item_id: row for row in window.visible_rows}
    assert rows["wallet:currency_dust"].name == "Пыль Резидуу"
    assert rows["wallet:currency_dust"].item_type == "currency"
    assert rows["wallet:currency_dust"].quantity == 3
    assert rows["wallet:res_torn_pelt"].name == "Дырявая шкура"
    assert rows["wallet:res_torn_pelt"].item_type == "resource"
    assert rows["wallet:res_torn_pelt"].quantity == 2
    assert rows["wallet:res_animal_bones"].details.description


@pytest.mark.asyncio
async def test_open_window_includes_active_expedition_resources(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="exploration", risk={"run_id": "run-1"})
    service = _service(
        fake_redis_service,
        [],
        repository=FakeInventoryRepository(
            [],
            wallet=WalletDTO(currency={"currency_dust": 1}),
            expedition_wallet=WalletDTO(
                currency={"currency_dust": 2},
                resources={"res_torn_pelt": 4},
            ),
        ),
    )

    window = await service.open_window(7)

    rows = {row.item_id: row for row in window.visible_rows}
    assert rows["wallet:currency_dust"].quantity == 3
    assert rows["wallet:res_torn_pelt"].name == "Дырявая шкура"
    assert rows["wallet:res_torn_pelt"].quantity == 4


@pytest.mark.asyncio
async def test_open_window_maps_power_label_by_item_role(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="exploration")
    service = _service(
        fake_redis_service,
        [
            _item("sword-1", "weapon", slot="main_hand", mechanics={"valid_slots": ["main_hand"], "power": 7}),
            _item("helm-1", "armor", slot="head_armor", mechanics={"valid_slots": ["head_armor"], "power": 3}),
            _item(
                "tunic-1",
                "garment",
                slot="chest_garment",
                mechanics={"valid_slots": ["chest_garment"], "power": 2},
            ),
        ],
    )

    window = await service.open_window(7)

    rows = {row.item_id: row.details for row in window.visible_rows}
    assert rows["sword-1"] is not None
    assert rows["helm-1"] is not None
    assert rows["tunic-1"] is not None
    assert any(line.label == "Урон" and line.value == "7" for line in rows["sword-1"].details)
    assert any(line.label == "Броня" and line.value == "3" for line in rows["helm-1"].details)
    assert any(line.label == "Защита" and line.value == "2" for line in rows["tunic-1"].details)


@pytest.mark.asyncio
async def test_open_window_shows_belt_power_as_inventory_cells(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="exploration")
    service = _service(
        fake_redis_service,
        [
            _item(
                "belt-1",
                "accessory",
                slot="belt_accessory",
                placement="equipped",
                mechanics={
                    "valid_slots": ["belt_accessory"],
                    "power": 8,
                    "implicit_bonuses": {"quick_slot_capacity": 4},
                },
            ),
        ],
    )

    window = await service.open_window(7)

    details = window.accessory_rows[-1].slots[0].details
    assert details is not None
    assert any(line.label == "Ячейки инвентаря" and line.value == "8" for line in details.details)
    assert any(line.label == "Слоты пояса" and line.value == "4" for line in details.details)


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
    assert "sync_dirty" not in active_doc


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
async def test_unequipping_belt_moves_disabled_quick_items_back_to_backpack(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="exploration")
    service = _service(
        fake_redis_service,
        [
            _item(
                "belt-1",
                "accessory",
                slot="belt_accessory",
                placement="equipped",
                mechanics={"implicit_bonuses": {"quick_slot_capacity": 1}, "valid_slots": ["belt_accessory"]},
            ),
            _item(
                "potion-1",
                "consumable",
                slot="belt_slot_1",
                placement="belt",
                mechanics={"is_quick_slot_compatible": True, "valid_slots": []},
            ),
        ],
    )

    window = await service.apply_action(
        InventoryActionRequestDTO(char_id=7, action="unequip", item_id="belt-1", slot_id="belt_accessory")
    )

    active_doc = fake_redis_client.store["game:ac:7"]
    assert active_doc["items"]["layout"]["belt"]["belt_slot_1"] is None
    assert active_doc["items"]["layout"]["backpack"] == []
    assert "potion-1" not in active_doc["items"]["by_id"]
    assert all(slot.enabled is False for slot in window.quick_slots)


@pytest.mark.asyncio
async def test_remove_from_belt_only_removes_belt_items(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="exploration")
    service = _service(fake_redis_service, [_item("boots-1", "garment", slot="feetwear", placement="equipped")])

    with pytest.raises(ValueError, match="not in the belt"):
        await service.apply_action(
            InventoryActionRequestDTO(char_id=7, action="remove_from_belt", item_id="boots-1", slot_id="belt_slot_1")
        )


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


@pytest.mark.asyncio
async def test_apply_durability_damage_updates_equipped_items(fake_redis_service, fake_redis_client):
    _active_character(fake_redis_client, state="combat_result")
    repository = FakeInventoryRepository(
        [
            _item(
                "sword-1",
                "weapon",
                slot="main_hand",
                placement="equipped",
                mechanics={"valid_slots": ["main_hand"], "durability_current": 10, "durability_max": 12},
            ),
            _item(
                "ore-1",
                "resource",
                slot=None,
                placement="backpack",
                mechanics={"durability_current": 5, "durability_max": 5},
            ),
        ]
    )
    service = _service(fake_redis_service, [], repository=repository)

    result = await service.apply_durability_damage(
        char_id=7,
        amount=0.1,
        scope="equipped",
        reason="combat_completed",
        combat_id="combat-1",
        idempotency_key="combat:combat-1:durability:7:combat_completed",
    )

    assert result["status"] == "ok"
    assert result["changed"] == [{"item_id": "sword-1", "before": 10.0, "after": 9.9}]
    assert repository.saved is not None
    assert repository.saved["sword-1"].mechanics["durability_current"] == 9.9
    assert repository.saved["ore-1"].mechanics["durability_current"] == 5
    assert repository.committed is True
    assert fake_redis_client.store["game:ac:7"]["items"]["by_id"]["sword-1"]["mechanics"]["durability_current"] == 9.9
    assert "combat:combat-1:durability:7:combat_completed" in fake_redis_client.store["game:ac:7"]["processed_events"]

    duplicate = await service.apply_durability_damage(
        char_id=7,
        amount=0.1,
        scope="equipped",
        reason="combat_completed",
        combat_id="combat-1",
        idempotency_key="combat:combat-1:durability:7:combat_completed",
    )

    assert duplicate == {"status": "skipped", "changed": [], "reason": "duplicate_event"}
    assert fake_redis_client.store["game:inventory:7"]["by_id"]["sword-1"]["mechanics"]["durability_current"] == 9.9


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


def _active_character(
    fake_redis_client,
    *,
    state: str,
    attributes: dict | None = None,
    risk: dict | None = None,
) -> None:
    fake_redis_client.store["game:ac:7"] = {
        "char_id": 7,
        "state": state,
        "attributes": attributes or {},
        "risk": risk or {},
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
    metadata: dict | None = None,
    rarity: str = "shared",
    rarity_tier: int = 0,
    description: str = "",
    tags: list[str] | None = None,
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
        description=description,
        rarity=rarity,
        rarity_tier=rarity_tier,
        mechanics=mechanics,
        tags=tags or [],
        metadata=metadata or {},
    )

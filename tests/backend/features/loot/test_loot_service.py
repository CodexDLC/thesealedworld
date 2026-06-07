from __future__ import annotations

import pytest

from src.backend.features.loot.services.loot_service import LootService


class FakeLootIntegration:
    def __init__(self) -> None:
        self.corpses = []
        self.item_requests = []
        self.cleared_orders = []

    async def mark_loot_ordered(self, session_id: str) -> bool:
        return True

    async def clear_loot_ordered(self, session_id: str) -> None:
        self.cleared_orders.append(session_id)

    async def persist_corpse(self, corpse, location_id: str) -> None:
        self.corpses.append((corpse, location_id))

    async def request_item_instance(self, **kwargs):
        self.item_requests.append(kwargs)
        return None


class FakeEngine:
    def build_drop_items(
        self,
        role_profile,
        monster_tier: int,
        role: str,
        battle_type: str,
        *,
        chance_multiplier: float = 1.0,
    ):
        from src.shared.schemas.loot import LootItemDTO

        return [LootItemDTO(template_id="fang", name="Fang", is_resource=True)]

    def build_salvage_items(self, role_profile, monster_tier: int, role: str):
        return []

    def build_spoil_items(self, role_profile, monster_tier: int, role: str):
        return []

    def build_group_bonus_item(self, candidates, *, chance_multiplier: float = 1.0):
        return None


class DropOnlyEngine:
    def build_drop_items(
        self,
        role_profile,
        monster_tier: int,
        role: str,
        battle_type: str,
        *,
        chance_multiplier: float = 1.0,
    ):
        from src.shared.schemas.loot import LootItemDTO

        return [
            LootItemDTO(template_id="res_torn_pelt", name="Torn Pelt", is_resource=True, layer="drop"),
        ]

    def build_salvage_items(self, role_profile, monster_tier: int, role: str):
        raise AssertionError("salvage must not be generated for ordinary post-combat loot")

    def build_spoil_items(self, role_profile, monster_tier: int, role: str):
        raise AssertionError("spoil must not be generated for ordinary post-combat loot")

    def build_group_bonus_item(self, candidates, *, chance_multiplier: float = 1.0):
        return None


class EmptyEngine:
    def build_drop_items(
        self,
        role_profile,
        monster_tier: int,
        role: str,
        battle_type: str,
        *,
        chance_multiplier: float = 1.0,
    ):
        return []

    def build_salvage_items(self, role_profile, monster_tier: int, role: str):
        return []

    def build_spoil_items(self, role_profile, monster_tier: int, role: str):
        return []

    def roll_equipment_tier(self, monster_tier: int, role: str):
        return 0

    def pick_equipment_base_id(
        self,
        eq_profile,
        role: str,
        *,
        chance_multiplier: float = 1.0,
    ):
        return None

    def build_group_bonus_item(self, candidates, *, chance_multiplier: float = 1.0):
        return None


@pytest.mark.asyncio
async def test_order_loot_for_combat_returns_actor_to_corpse_map() -> None:
    integration = FakeLootIntegration()
    service = LootService(integration, FakeEngine())

    pending = await service.order_loot_for_combat(
        session_id="combat-1",
        location_id="forest",
        battle_type="pve",
        actors=[
            {"actor_id": "7", "meta": {"type": "player", "id": "7"}},
            {
                "actor_id": "wolf_1",
                "meta": {"type": "monster", "id": "wolf_1", "name": "Wolf"},
                "source": {"loot_profile_id": "default"},
            },
        ],
    )

    assert set(pending) == {"wolf_1"}
    assert integration.corpses[0][0].id == pending["wolf_1"]
    assert integration.corpses[0][0].is_visible is False
    assert integration.corpses[0][1] == "forest"


@pytest.mark.asyncio
async def test_order_loot_for_combat_materializes_only_plain_drop_items() -> None:
    integration = FakeLootIntegration()
    service = LootService(integration, DropOnlyEngine())

    await service.order_loot_for_combat(
        session_id="combat-1",
        location_id="forest",
        battle_type="pve",
        actors=[
            {
                "actor_id": "wolf_1",
                "meta": {"type": "monster", "id": "wolf_1", "name": "Wolf"},
                "source": {"loot_profile_id": "wolf_pack"},
            },
        ],
    )

    corpse = integration.corpses[0][0]
    assert [item.layer for item in corpse.items] == ["drop"]
    assert [item.template_id for item in corpse.items] == ["res_torn_pelt"]


@pytest.mark.asyncio
async def test_order_loot_for_combat_clears_order_marker_when_no_corpses_are_created() -> None:
    integration = FakeLootIntegration()
    service = LootService(integration, EmptyEngine())

    pending = await service.order_loot_for_combat(
        session_id="combat-empty",
        location_id="forest",
        battle_type="pve",
        actors=[
            {
                "actor_id": "wolf_1",
                "meta": {"type": "monster", "id": "wolf_1", "name": "Wolf"},
                "source": {"loot_profile_id": "default"},
            },
        ],
    )

    assert pending == {}
    assert integration.corpses == []
    assert integration.cleared_orders == ["combat-empty"]


class FakeEquipmentEngine:
    def build_drop_items(
        self,
        role_profile,
        monster_tier: int,
        role: str,
        battle_type: str,
        *,
        chance_multiplier: float = 1.0,
    ):
        from src.shared.schemas.loot import LootItemDTO

        return [LootItemDTO(template_id="shield", name="Shield", is_resource=False)]

    def build_salvage_items(self, role_profile, monster_tier: int, role: str):
        return []

    def build_spoil_items(self, role_profile, monster_tier: int, role: str):
        return []

    def roll_equipment_tier(self, monster_tier: int, role: str):
        return 2

    def pick_equipment_base_id(
        self,
        eq_profile,
        role: str,
        *,
        chance_multiplier: float = 1.0,
    ):
        return "shield"

    def build_group_bonus_item(self, candidates, *, chance_multiplier: float = 1.0):
        return None


@pytest.mark.asyncio
async def test_order_loot_passes_family_level_owner_context_to_item_generation() -> None:
    integration = FakeLootIntegration()
    service = LootService(integration, FakeEquipmentEngine())
    owner_family = {
        "clan_id": "clan-1",
        "family_resource_id": "bandit_gang",
        "clan_name_ru": "Банда Воротной Щепы",
        "loot_culture": {"craft_style": "грубая переделка найденных вещей"},
    }

    await service.order_loot_for_combat(
        session_id="combat-1",
        location_id="52_53",
        battle_type="pve",
        actors=[
            {
                "actor_id": "monster-1",
                "meta": {"type": "monster", "id": "monster-1", "name": "Bandit", "role": "veteran", "tier": 2},
                "source": {
                    "family_id": "bandit_gang",
                    "clan_id": "clan-1",
                    "owner_family": owner_family,
                    "template_id": "bandit_cutthroat",
                },
            },
        ],
    )

    request = integration.item_requests[0]
    assert request["base_id"] == "shield"
    assert request["source_context"]["family_id"] == "bandit_gang"
    assert request["source_context"]["clan_id"] == "clan-1"
    assert request["source_context"]["owner_family"] == owner_family
    assert "member_role" not in request["source_context"]
    assert "variant_key" not in request["source_context"]


class RecordingRiftEngine(EmptyEngine):
    def __init__(self) -> None:
        self.drop_multipliers: list[float] = []
        self.equipment_rolls: list[float] = []
        self.group_bonus_multipliers: list[float] = []

    def build_drop_items(
        self,
        role_profile,
        monster_tier: int,
        role: str,
        battle_type: str,
        *,
        chance_multiplier: float = 1.0,
    ):
        self.drop_multipliers.append(chance_multiplier)
        return []

    def pick_equipment_base_id(
        self,
        eq_profile,
        role: str,
        *,
        chance_multiplier: float = 1.0,
    ):
        self.equipment_rolls.append(chance_multiplier)
        return None

    def build_group_bonus_item(self, candidates, *, chance_multiplier: float = 1.0):
        self.group_bonus_multipliers.append(chance_multiplier)
        return (candidates[0], "shield") if candidates else None


class GrantingLootIntegration(FakeLootIntegration):
    async def request_item_instance(self, **kwargs):
        self.item_requests.append(kwargs)
        return f"item-{len(self.item_requests)}"


@pytest.mark.asyncio
async def test_rift_group_bonus_rolls_once_and_keeps_per_corpse_chances_base() -> None:
    integration = GrantingLootIntegration()
    engine = RecordingRiftEngine()
    service = LootService(integration, engine)

    pending = await service.order_loot_for_combat(
        session_id="rift-combat-1",
        location_id="rift-node",
        battle_type="rift",
        actors=[
            {
                "actor_id": "bandit-1",
                "meta": {"type": "monster", "id": "bandit-1", "name": "Bandit", "role": "minion", "tier": 1},
                "source": {"family_id": "bandit_gang"},
            },
            {
                "actor_id": "bandit-2",
                "meta": {"type": "monster", "id": "bandit-2", "name": "Bandit", "role": "minion", "tier": 1},
                "source": {"family_id": "bandit_gang"},
            },
            {
                "actor_id": "bandit-3",
                "meta": {"type": "monster", "id": "bandit-3", "name": "Bandit", "role": "minion", "tier": 1},
                "source": {"family_id": "bandit_gang"},
            },
        ],
    )

    assert len(pending) == 1
    assert engine.drop_multipliers == [1.0, 1.0, 1.0]
    assert engine.equipment_rolls == [1.0, 1.0, 1.0]
    assert engine.group_bonus_multipliers == [1.2]
    assert integration.item_requests[0]["base_id"] == "shield"
    assert integration.corpses[0][0].items[0].instance_id == "item-1"


class ResourceRiftEngine(RecordingRiftEngine):
    def build_drop_items(
        self,
        role_profile,
        monster_tier: int,
        role: str,
        battle_type: str,
        *,
        chance_multiplier: float = 1.0,
    ):
        from src.shared.schemas.loot import LootItemDTO

        self.drop_multipliers.append(chance_multiplier)
        return [LootItemDTO(template_id="res_dirty_rags", name="Dirty Rags", is_resource=True, layer="drop")]


@pytest.mark.asyncio
async def test_rift_group_bonus_merges_into_existing_resource_corpse() -> None:
    integration = GrantingLootIntegration()
    engine = ResourceRiftEngine()
    service = LootService(integration, engine)

    pending = await service.order_loot_for_combat(
        session_id="rift-combat-2",
        location_id="rift-node",
        battle_type="rift",
        actors=[
            {
                "actor_id": "bandit-1",
                "meta": {"type": "monster", "id": "bandit-1", "name": "Bandit", "role": "minion", "tier": 1},
                "source": {"family_id": "bandit_gang"},
            },
            {
                "actor_id": "bandit-2",
                "meta": {"type": "monster", "id": "bandit-2", "name": "Bandit", "role": "minion", "tier": 1},
                "source": {"family_id": "bandit_gang"},
            },
        ],
    )

    assert len(pending) == 2
    assert len(integration.corpses) == 2
    first_corpse = integration.corpses[0][0]
    assert [item.template_id for item in first_corpse.items] == ["res_dirty_rags", "shield"]

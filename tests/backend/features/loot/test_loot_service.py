from __future__ import annotations

import pytest

from src.backend.features.loot.services.loot_service import LootService


class FakeLootIntegration:
    def __init__(self) -> None:
        self.corpses = []
        self.item_requests = []

    async def mark_loot_ordered(self, session_id: str) -> bool:
        return True

    async def persist_corpse(self, corpse, location_id: str) -> None:
        self.corpses.append((corpse, location_id))

    async def request_item_instance(self, **kwargs):
        self.item_requests.append(kwargs)
        return None


class FakeEngine:
    def build_drop_items(self, role_profile, monster_tier: int, role: str, battle_type: str):
        from src.shared.schemas.loot import LootItemDTO

        return [LootItemDTO(template_id="fang", name="Fang", is_resource=True)]

    def build_salvage_items(self, role_profile, monster_tier: int, role: str):
        return []

    def build_spoil_items(self, role_profile, monster_tier: int, role: str):
        return []


class DropOnlyEngine:
    def build_drop_items(self, role_profile, monster_tier: int, role: str, battle_type: str):
        from src.shared.schemas.loot import LootItemDTO

        return [
            LootItemDTO(template_id="res_torn_pelt", name="Torn Pelt", is_resource=True, layer="drop"),
        ]

    def build_salvage_items(self, role_profile, monster_tier: int, role: str):
        raise AssertionError("salvage must not be generated for ordinary post-combat loot")

    def build_spoil_items(self, role_profile, monster_tier: int, role: str):
        raise AssertionError("spoil must not be generated for ordinary post-combat loot")


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


class FakeEquipmentEngine:
    def build_drop_items(self, role_profile, monster_tier: int, role: str, battle_type: str):
        from src.shared.schemas.loot import LootItemDTO

        return [LootItemDTO(template_id="shield", name="Shield", is_resource=False)]

    def build_salvage_items(self, role_profile, monster_tier: int, role: str):
        return []

    def build_spoil_items(self, role_profile, monster_tier: int, role: str):
        return []

    def roll_equipment_tier(self, monster_tier: int, role: str):
        return 2


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

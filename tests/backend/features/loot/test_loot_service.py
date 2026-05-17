from __future__ import annotations

import pytest

from src.backend.features.loot.services.loot_service import LootService


class FakeLootIntegration:
    def __init__(self) -> None:
        self.corpses = []

    async def mark_loot_ordered(self, session_id: str) -> bool:
        return True

    async def persist_corpse(self, corpse, location_id: str) -> None:
        self.corpses.append((corpse, location_id))

    async def request_item_instance(self, **kwargs):
        return None


class FakeEngine:
    def build_drop_items(self, role_profile, monster_tier: int, role: str, battle_type: str):
        from src.shared.schemas.loot import LootItemDTO

        return [LootItemDTO(template_id="fang", name="Fang", is_resource=True)]

    def build_salvage_items(self, role_profile, monster_tier: int, role: str):
        return []

    def build_spoil_items(self, role_profile, monster_tier: int, role: str):
        return []


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

from __future__ import annotations

from typing import Any

import pytest

from src.backend.features.items.dto.instance import RuntimeItemProjectionDTO
from src.backend.features.monsters.services.anchor_projection_bootstrap import (
    ANCHOR_PROJECTION_REDIS_PREFIX,
    AnchorProjectionBootstrapService,
)


class FakeItemGeneration:
    async def generate_runtime_projections(self, requests):
        projections = []
        for index, request in enumerate(requests):
            base_id = str(request.base_id)
            related_skill = {
                "anchor_stasis_crown_blade": "skill_swords",
                "anchor_entropy_cinder_maul": "skill_macing",
                "anchor_gravity_storm_lance": "skill_polearms",
                "anchor_evolution_bloom_talons": "skill_fencing",
                "anchor_projection_aegis": "skill_heavy_armor",
                "shield": "skill_shield_mastery",
            }[base_id]
            item_type = "armor" if request.target_slot.endswith("_armor") or base_id == "shield" else "weapon"
            projections.append(
                RuntimeItemProjectionDTO(
                    item_id=f"anchor-item-{index}",
                    owner_key=str(request.runtime_metadata["owner_key"]),
                    base_id=base_id,
                    item_type=item_type,
                    slot=str(request.target_slot),
                    combat={
                        "power": 10,
                        "damage_spread": 0.0,
                        "implicit_bonuses": {},
                        "bonuses": {},
                        "triggers": [],
                        "tags": ["shield"] if base_id == "shield" else [],
                        "related_skill": related_skill,
                    },
                    generation={"item_grade": "artifact", "rarity_tier": 7, "affixes": []},
                )
            )
        return projections


class FakeJson:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    async def set(self, key: str, path: str, value: Any) -> None:
        assert path == "$"
        self.values[key] = value


class FakeRedis:
    def __init__(self) -> None:
        self.json_module = FakeJson()


@pytest.mark.unit
async def test_anchor_projection_bootstrap_creates_four_boss_snapshots_and_caches_them() -> None:
    redis = FakeRedis()

    result = await AnchorProjectionBootstrapService(
        item_generation=FakeItemGeneration(),
        redis=redis,
    ).bootstrap()

    assert result["family_id"] == "anchor_sovereigns"
    assert result["redis_cached"] is True
    assert result["members"] == [
        "east_evolution_sovereign",
        "north_stasis_sovereign",
        "south_entropy_sovereign",
        "west_gravity_sovereign",
    ]

    west_key = f"{ANCHOR_PROJECTION_REDIS_PREFIX}:west_gravity_sovereign"
    west_snapshot = redis.json_module.values[west_key]
    assert west_snapshot["meta"]["name"] == "Проекция Западной Гравитации"
    assert west_snapshot["combat"]["loadout"]["layout"]["main_hand"] == "skill_polearms"
    assert west_snapshot["combat"]["loadout"]["layout"]["tactical_style"] == "skill_one_handed"
    assert west_snapshot["combat"]["skills"]["skill_polearms"] == 1.0
    assert west_snapshot["status"]["hp"]["max"] > 0

    east_snapshot = redis.json_module.values[f"{ANCHOR_PROJECTION_REDIS_PREFIX}:east_evolution_sovereign"]
    assert east_snapshot["combat"]["loadout"]["layout"]["tactical_style"] == "skill_dual_wield"


@pytest.mark.unit
async def test_anchor_projection_bootstrap_rebuilds_snapshots_from_resources_without_persistence() -> None:
    redis = FakeRedis()
    service = AnchorProjectionBootstrapService(
        item_generation=FakeItemGeneration(),
        redis=redis,
    )
    first = await service.bootstrap()

    result = await service.bootstrap()

    assert result["clan_id"] == first["clan_id"]
    assert result["members"] == first["members"]
    assert result["redis_cached"] is True
    assert f"{ANCHOR_PROJECTION_REDIS_PREFIX}:index" in redis.json_module.values

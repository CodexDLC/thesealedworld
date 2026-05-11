from dataclasses import dataclass
from typing import Any

from src.backend.features.monsters.dto import MonsterGenerationContext
from src.backend.features.monsters.services.world_population_service import WorldMonsterPopulationService


@dataclass(slots=True)
class FakeZone:
    id: str
    biome_id: str
    tier: int
    flags: dict[str, Any]


@dataclass(slots=True)
class FakeNode:
    zone_id: str
    flags: dict[str, Any]
    content: dict[str, Any]
    zone: FakeZone


class FakeEncounterService:
    def __init__(self) -> None:
        self.calls: list[tuple[MonsterGenerationContext, str]] = []

    def get_available_family_ids(self, context: MonsterGenerationContext) -> list[str]:
        del context
        return ["bandit_gang", "goblin_tribe", "rat_swarm"]

    async def ensure_clan_for_context(self, context: MonsterGenerationContext, family_id: str) -> object:
        self.calls.append((context, family_id))
        return object()


async def test_world_population_builds_unique_unsafe_contexts() -> None:
    zone = FakeZone(id="D4_0_0", biome_id="city_ruins", tier=0, flags={})
    service = FakeEncounterService()
    population = WorldMonsterPopulationService(service)  # type: ignore[arg-type]

    result = await population.ensure_population_for_nodes(
        [
            FakeNode(
                zone_id="D4_0_0",
                zone=zone,
                flags={"threat_tier": 1, "anchor_influence": {"tier": 2, "tags": ["mana_leak"]}},
                content={"environment_tags": ["city_ruins"]},
            ),
            FakeNode(
                zone_id="D4_0_0",
                zone=zone,
                flags={"threat_tier": 1, "anchor_influence": {"tier": 2, "tags": ["mana_leak"]}},
                content={"environment_tags": ["city_ruins"]},
            ),
            FakeNode(
                zone_id="D4_1_1",
                zone=FakeZone(id="D4_1_1", biome_id="hub_district", tier=0, flags={"is_safe_zone": True}),
                flags={},
                content={"environment_tags": ["safe_zone"]},
            ),
        ]
    )

    assert result.contexts == 1
    assert result.clans == 3
    expected_context = MonsterGenerationContext(
        zone_id="D4_0_0",
        biome_id="city_ruins",
        tier=2,
        tags=["city_ruins", "mana_leak"],
        difficulty="mid",
    )
    assert service.calls == [
        (expected_context, "bandit_gang"),
        (expected_context, "goblin_tribe"),
        (expected_context, "rat_swarm"),
    ]

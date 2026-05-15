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
    zone = FakeZone(id="A1_0_0", biome_id="forest", tier=0, flags={})
    service = FakeEncounterService()
    population = WorldMonsterPopulationService(service)  # type: ignore[arg-type]

    result = await population.ensure_population_for_nodes(
        [
            FakeNode(
                zone_id="A1_0_0",
                zone=zone,
                flags={"threat_tier": 1, "anchor_influence": {"tier": 2, "tags": ["mana_leak"]}},
                content={"environment_tags": ["forest"]},
            ),
            FakeNode(
                zone_id="A1_0_0",
                zone=zone,
                flags={"threat_tier": 1, "anchor_influence": {"tier": 2, "tags": ["mana_leak"]}},
                content={"environment_tags": ["forest"]},
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
        zone_id="A1_0_0",
        biome_id="forest",
        tier=1,
        tags=["forest", "mana_leak"],
        difficulty="mid",
    )
    assert service.calls == [
        (expected_context, "bandit_gang"),
        (expected_context, "goblin_tribe"),
        (expected_context, "rat_swarm"),
    ]


class D4EncounterService:
    def __init__(self) -> None:
        self.calls: list[tuple[MonsterGenerationContext, str]] = []

    def get_available_family_ids(self, context: MonsterGenerationContext) -> list[str]:
        families = ["bandit_gang", "goblin_tribe", "rat_swarm", "wolf_pack"]
        return [family_id for family_id in families if family_id in context.tags]

    async def ensure_clan_for_context(self, context: MonsterGenerationContext, family_id: str) -> object:
        self.calls.append((context, family_id))
        return object()


def _d4_node(zone_id: str, tags: list[str], threat_tier: int = 0, *, is_rift: bool = False) -> FakeNode:
    return FakeNode(
        zone_id=zone_id,
        zone=FakeZone(id=zone_id, biome_id="city_ruins", tier=threat_tier, flags={}),
        flags={
            "threat_tier": threat_tier,
            "is_rift": is_rift,
            "context_tags": tags,
            "rift_profile": {"family_id": "rat_swarm", "context_tags": tags} if is_rift else None,
        },
        content={"environment_tags": ["city_ruins"]},
    )


async def test_world_population_d4_start_region_builds_tiered_clan_contexts() -> None:
    service = D4EncounterService()
    population = WorldMonsterPopulationService(service)  # type: ignore[arg-type]

    result = await population.ensure_population_for_nodes(
        [
            _d4_node("D4_1_0", ["d4_tier0_gate_cross"]),
            _d4_node("D4_0_1", ["d4_tier0_ruined_streets"]),
            _d4_node("D4_0_0", ["d4_corner_pressure", "d4_rift_rat_king", "rat_king_pressure"], 1),
            _d4_node("D4_2_0", ["d4_corner_pressure", "d4_rift_wolf_breach", "wolf_breach_pressure"], 1),
            _d4_node(
                "D4_0_2",
                ["d4_corner_pressure", "d4_rift_bandit_barricade", "bandit_barricade_pressure"],
                1,
            ),
            _d4_node(
                "D4_2_2",
                ["d4_corner_pressure", "d4_rift_goblin_scrapyard", "goblin_scrapyard_pressure"],
                1,
            ),
            _d4_node("D4_0_0", ["d4_rift_rat_king"], 2, is_rift=True),
            _d4_node("D4_2_0", ["d4_rift_wolf_breach"], 2, is_rift=True),
            _d4_node("D4_0_2", ["d4_rift_bandit_barricade"], 2, is_rift=True),
            _d4_node("D4_2_2", ["d4_rift_goblin_scrapyard"], 2, is_rift=True),
            FakeNode(
                zone_id="D4_1_1",
                zone=FakeZone(id="D4_1_1", biome_id="hub_district", tier=0, flags={"is_safe_zone": True}),
                flags={},
                content={"environment_tags": ["safe_zone"]},
            ),
        ]
    )

    assert result.contexts == 6
    assert result.clans == 12
    calls_by_zone = [(context.zone_id, context.tier, family_id) for context, family_id in service.calls]
    assert calls_by_zone == [
        ("D4_tier0_start", 0, "bandit_gang"),
        ("D4_tier0_start", 0, "goblin_tribe"),
        ("D4_tier0_start", 0, "rat_swarm"),
        ("D4_tier0_start", 0, "wolf_pack"),
        ("D4_tier1_corner_pressure", 1, "bandit_gang"),
        ("D4_tier1_corner_pressure", 1, "goblin_tribe"),
        ("D4_tier1_corner_pressure", 1, "rat_swarm"),
        ("D4_tier1_corner_pressure", 1, "wolf_pack"),
        ("D4_0_0", 2, "rat_swarm"),
        ("D4_2_0", 2, "wolf_pack"),
        ("D4_0_2", 2, "bandit_gang"),
        ("D4_2_2", 2, "goblin_tribe"),
    ]

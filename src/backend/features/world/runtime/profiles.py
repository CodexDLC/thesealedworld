from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from src.backend.features.world.runtime.config import HUB_CENTER

if TYPE_CHECKING:
    from src.backend.features.world.runtime.geography import ZoneGeography
    from src.backend.features.world.runtime.threat import AnchorInfluence


CANONICAL_REGION_BIOMES = frozenset(
    {
        "city_ruins",
        "forest",
        "mountains",
        "swamp",
        "grassland",
        "wasteland",
        "jungle",
    }
)

FIRST_RING_REGION_IDS = frozenset({"C3", "C4", "C5", "D3", "D5", "E3", "E4", "E5"})


@dataclass(frozen=True, slots=True)
class NavigationProfile:
    id: str
    min_degree: int
    target_degree: int
    max_degree: int
    road_degree: int
    landmark_degree: int
    dead_end_chance: float
    loop_chance: float
    blocked_edge_tags: tuple[str, ...]

    def model_dump(self) -> dict[str, Any]:
        data = asdict(self)
        data["blocked_edge_tags"] = list(self.blocked_edge_tags)
        return data


NAVIGATION_PROFILES: dict[str, NavigationProfile] = {
    "city_ruins_labyrinth": NavigationProfile(
        id="city_ruins_labyrinth",
        min_degree=1,
        target_degree=2,
        max_degree=3,
        road_degree=3,
        landmark_degree=1,
        dead_end_chance=0.28,
        loop_chance=0.22,
        blocked_edge_tags=("collapsed_wall", "sealed_arch", "rubble_choke", "monolith_partition"),
    ),
    "forest_paths": NavigationProfile(
        id="forest_paths",
        min_degree=2,
        target_degree=3,
        max_degree=3,
        road_degree=3,
        landmark_degree=2,
        dead_end_chance=0.12,
        loop_chance=0.38,
        blocked_edge_tags=("dense_growth", "fallen_trees", "thorn_wall"),
    ),
    "mountain_passes": NavigationProfile(
        id="mountain_passes",
        min_degree=1,
        target_degree=2,
        max_degree=3,
        road_degree=2,
        landmark_degree=1,
        dead_end_chance=0.22,
        loop_chance=0.12,
        blocked_edge_tags=("cliff_face", "rockslide", "broken_ledge"),
    ),
    "swamp_channels": NavigationProfile(
        id="swamp_channels",
        min_degree=1,
        target_degree=2,
        max_degree=3,
        road_degree=2,
        landmark_degree=1,
        dead_end_chance=0.26,
        loop_chance=0.2,
        blocked_edge_tags=("deep_mire", "black_water", "reed_wall"),
    ),
    "open_frontier": NavigationProfile(
        id="open_frontier",
        min_degree=2,
        target_degree=3,
        max_degree=3,
        road_degree=3,
        landmark_degree=2,
        dead_end_chance=0.08,
        loop_chance=0.34,
        blocked_edge_tags=("ravine", "old_fence", "broken_ground"),
    ),
    "wasteland_scars": NavigationProfile(
        id="wasteland_scars",
        min_degree=1,
        target_degree=2,
        max_degree=3,
        road_degree=2,
        landmark_degree=1,
        dead_end_chance=0.2,
        loop_chance=0.16,
        blocked_edge_tags=("ash_pit", "glass_ridge", "cracked_plateau"),
    ),
}

BIOME_NAVIGATION_PROFILE = {
    "city_ruins": "city_ruins_labyrinth",
    "forest": "forest_paths",
    "jungle": "forest_paths",
    "mountains": "mountain_passes",
    "swamp": "swamp_channels",
    "grassland": "open_frontier",
    "wasteland": "wasteland_scars",
}


@dataclass(frozen=True, slots=True)
class PopulationProfile:
    id: str
    primary_families: tuple[str, ...]
    secondary_families: tuple[str, ...]
    excluded_families: tuple[str, ...]
    tier_band: tuple[int, int]
    population_tags: tuple[str, ...]

    def model_dump(self) -> dict[str, Any]:
        data = asdict(self)
        data["primary_families"] = list(self.primary_families)
        data["secondary_families"] = list(self.secondary_families)
        data["excluded_families"] = list(self.excluded_families)
        data["tier_band"] = list(self.tier_band)
        data["population_tags"] = list(self.population_tags)
        return data


D4_POPULATION_PROFILE = PopulationProfile(
    id="d4_starting_city_population",
    primary_families=("bandit_gang", "goblin_tribe", "rat_swarm", "wolf_pack"),
    secondary_families=(),
    excluded_families=(),
    tier_band=(0, 2),
    population_tags=("d4_city_ruins", "starter_ring", "sealed_city_gates"),
)

FIRST_RING_POPULATION_PROFILES: dict[str, PopulationProfile] = {
    "C3": PopulationProfile(
        id="c3_cold_highland_frontier",
        primary_families=("wolf_pack", "werewolf_pack"),
        secondary_families=("undead_legion",),
        excluded_families=("golem_foundry",),
        tier_band=(1, 3),
        population_tags=("first_ring", "northwest_pressure", "cold_highlands"),
    ),
    "C4": PopulationProfile(
        id="c4_north_gate_frontier",
        primary_families=("wolf_pack", "spider_colony"),
        secondary_families=("bandit_gang",),
        excluded_families=("golem_foundry",),
        tier_band=(1, 3),
        population_tags=("first_ring", "north_gate_frontier", "stasis_pressure"),
    ),
    "C5": PopulationProfile(
        id="c5_bio_forest_frontier",
        primary_families=("spider_colony", "insect_hive"),
        secondary_families=("living_forest",),
        excluded_families=("undead_legion",),
        tier_band=(1, 3),
        population_tags=("first_ring", "bio_forest", "overgrowth_pressure"),
    ),
    "D3": PopulationProfile(
        id="d3_west_gate_frontier",
        primary_families=("bat_colony", "bandit_gang"),
        secondary_families=("golem_foundry",),
        excluded_families=("living_forest",),
        tier_band=(1, 3),
        population_tags=("first_ring", "west_gate_frontier", "gravity_scars"),
    ),
    "D5": PopulationProfile(
        id="d5_east_gate_frontier",
        primary_families=("spider_colony", "snake_den"),
        secondary_families=("insect_hive", "living_forest"),
        excluded_families=("undead_legion",),
        tier_band=(1, 3),
        population_tags=("first_ring", "east_gate_frontier", "bio_pressure"),
    ),
    "E3": PopulationProfile(
        id="e3_storm_badlands_frontier",
        primary_families=("bat_colony", "orc_clan"),
        secondary_families=("elemental_rift",),
        excluded_families=("living_forest",),
        tier_band=(1, 3),
        population_tags=("first_ring", "storm_badlands", "gravity_fire_mix"),
    ),
    "E4": PopulationProfile(
        id="e4_south_gate_frontier",
        primary_families=("goblin_tribe", "bandit_gang"),
        secondary_families=("snake_den",),
        excluded_families=("living_forest",),
        tier_band=(1, 3),
        population_tags=("first_ring", "south_gate_frontier", "heated_ruins"),
    ),
    "E5": PopulationProfile(
        id="e5_ash_wasteland_frontier",
        primary_families=("goblin_tribe", "orc_clan"),
        secondary_families=("elemental_rift",),
        excluded_families=("living_forest",),
        tier_band=(1, 3),
        population_tags=("first_ring", "ash_wasteland", "entropy_pressure"),
    ),
}


@dataclass(frozen=True, slots=True)
class RegionProfile:
    id: str
    biome_id: str
    biome_mix: dict[str, float]
    region_archetype: str
    tier_band: tuple[int, int]
    navigation_profile_id: str
    population_profile: PopulationProfile
    anchor_influence: dict[str, Any]
    region_tags: tuple[str, ...]
    is_locked_frontier: bool = False

    def model_dump(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "biome_id": self.biome_id,
            "biome_mix": dict(self.biome_mix),
            "region_archetype": self.region_archetype,
            "tier_band": list(self.tier_band),
            "navigation_profile": NAVIGATION_PROFILES[self.navigation_profile_id].model_dump(),
            "population_profile": self.population_profile.model_dump(),
            "anchor_influence": dict(self.anchor_influence),
            "region_tags": list(self.region_tags),
            "is_locked_frontier": self.is_locked_frontier,
        }


@dataclass(frozen=True, slots=True)
class ZoneProfile:
    id: str
    zone_archetype: str
    navigation_profile_id: str
    population_tags: tuple[str, ...]
    landmark_profile: str | None

    def model_dump(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "zone_archetype": self.zone_archetype,
            "navigation_profile": NAVIGATION_PROFILES[self.navigation_profile_id].model_dump(),
            "population_tags": list(self.population_tags),
            "landmark_profile": self.landmark_profile,
        }


def build_region_profile(
    *,
    region_id: str,
    center_x: int,
    center_y: int,
    geography: ZoneGeography,
    influence: AnchorInfluence,
) -> RegionProfile:
    if region_id == "D4":
        anchor_influence = _anchor_influence_dict(influence)
        return RegionProfile(
            id="d4_old_capital",
            biome_id="city_ruins",
            biome_mix={"city_ruins": 1.0},
            region_archetype="former_capital",
            tier_band=(0, 2),
            navigation_profile_id="city_ruins_labyrinth",
            population_profile=D4_POPULATION_PROFILE,
            anchor_influence=anchor_influence,
            region_tags=("ancient_world", "city_ruins", "former_capital", "starter_region", *influence.tags),
        )

    if region_id in FIRST_RING_REGION_IDS:
        biome_id = _first_ring_biome(region_id, geography["primary_biome"])
        profile = FIRST_RING_POPULATION_PROFILES[region_id]
        nav_id = BIOME_NAVIGATION_PROFILE[biome_id]
        return RegionProfile(
            id=f"{region_id.lower()}_locked_frontier",
            biome_id=biome_id,
            biome_mix=_canonical_biome_mix(biome_id, geography["biome_mix"]),
            region_archetype=f"first_ring_{region_id.lower()}",
            tier_band=profile.tier_band,
            navigation_profile_id=nav_id,
            population_profile=profile,
            anchor_influence=_anchor_influence_dict(influence),
            region_tags=("ancient_world", "first_ring", biome_id, *profile.population_tags, *influence.tags),
            is_locked_frontier=True,
        )

    biome_id = _canonical_biome(geography["primary_biome"])
    profile = _default_population_profile(region_id, biome_id, influence)
    return RegionProfile(
        id=f"{region_id.lower()}_wild_region",
        biome_id=biome_id,
        biome_mix=_canonical_biome_mix(biome_id, geography["biome_mix"]),
        region_archetype=f"{biome_id}_wilds",
        tier_band=(max(0, influence.tier), min(7, max(influence.tier + 2, 2))),
        navigation_profile_id=BIOME_NAVIGATION_PROFILE[biome_id],
        population_profile=profile,
        anchor_influence=_anchor_influence_dict(influence),
        region_tags=("ancient_world", biome_id, *profile.population_tags, *influence.tags),
    )


def build_zone_profile(*, region_profile: RegionProfile, zone_id: str, zx: int, zy: int) -> ZoneProfile:
    if region_profile.biome_id == "city_ruins":
        if zone_id == "D4_1_1":
            return ZoneProfile(
                id="d4_hub_district",
                zone_archetype="safe_hub",
                navigation_profile_id="city_ruins_labyrinth",
                population_tags=(),
                landmark_profile="portal_hub",
            )
        if zx == 1 or zy == 1:
            return ZoneProfile(
                id="d4_gate_cross",
                zone_archetype="gate_cross",
                navigation_profile_id="city_ruins_labyrinth",
                population_tags=("d4_tier0_gate_cross",),
                landmark_profile="sealed_city_gate" if zx == 1 or zy == 1 else None,
            )
        return ZoneProfile(
            id="d4_corner_rift_district",
            zone_archetype="corner_rift_district",
            navigation_profile_id="city_ruins_labyrinth",
            population_tags=("d4_corner_pressure",),
            landmark_profile="city_rift",
        )

    edge = zx in (0, 2) or zy in (0, 2)
    return ZoneProfile(
        id=f"{region_profile.biome_id}_{'edge' if edge else 'core'}",
        zone_archetype=f"{region_profile.biome_id}_{'edge' if edge else 'core'}",
        navigation_profile_id=region_profile.navigation_profile_id,
        population_tags=region_profile.population_profile.population_tags,
        landmark_profile="frontier_approach" if region_profile.is_locked_frontier else None,
    )


def _anchor_influence_dict(influence: AnchorInfluence) -> dict[str, Any]:
    return {
        "threat": influence.threat,
        "tier": influence.tier,
        "dominant_anchor": influence.dominant_anchor,
        "anomaly_id": influence.anomaly_id,
        "tags": list(influence.tags),
        "is_inside_city_shield": influence.is_inside_city_shield,
    }


def _first_ring_biome(region_id: str, fallback_biome: str) -> str:
    explicit = {
        "C3": "mountains",
        "C4": "mountains",
        "C5": "forest",
        "D3": "wasteland",
        "D5": "swamp",
        "E3": "wasteland",
        "E4": "grassland",
        "E5": "wasteland",
    }
    return explicit.get(region_id, _canonical_biome(fallback_biome))


def _canonical_biome(biome_id: str) -> str:
    aliases = {
        "meadow": "grassland",
        "savanna": "grassland",
        "hills": "mountains",
        "highlands": "mountains",
        "canyon": "wasteland",
        "badlands": "wasteland",
        "marsh": "swamp",
    }
    biome_id = aliases.get(biome_id, biome_id)
    if biome_id not in CANONICAL_REGION_BIOMES:
        return "wasteland"
    return biome_id


def _canonical_biome_mix(primary: str, raw_mix: dict[str, float]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for biome_id, weight in raw_mix.items():
        canonical = _canonical_biome(str(biome_id))
        totals[canonical] = totals.get(canonical, 0.0) + float(weight)
    if not totals:
        return {primary: 1.0}
    total = sum(totals.values())
    return {biome: round(value / total, 3) for biome, value in sorted(totals.items())}


def _default_population_profile(region_id: str, biome_id: str, influence: AnchorInfluence) -> PopulationProfile:
    by_biome = {
        "forest": (("wolf_pack", "spider_colony"), ("bandit_gang", "goblin_tribe")),
        "jungle": (("spider_colony", "insect_hive"), ("snake_den", "living_forest")),
        "mountains": (("bat_colony", "orc_clan"), ("golem_foundry",)),
        "swamp": (("snake_den", "insect_hive"), ("rat_swarm", "goblin_tribe")),
        "grassland": (("wolf_pack", "bandit_gang"), ("goblin_tribe",)),
        "wasteland": (("orc_clan", "bandit_gang"), ("elemental_rift",)),
    }
    primary, secondary = by_biome.get(biome_id, (("bandit_gang",), ("goblin_tribe",)))
    anchor_tag = influence.dominant_anchor or "neutral_anchor"
    return PopulationProfile(
        id=f"{region_id.lower()}_{biome_id}_population",
        primary_families=primary,
        secondary_families=secondary,
        excluded_families=(),
        tier_band=(max(0, influence.tier), min(7, max(influence.tier + 2, 2))),
        population_tags=(biome_id, anchor_tag),
    )


def is_inside_d4_region(x: int, y: int) -> bool:
    return abs(x - HUB_CENTER["x"]) <= 7 and abs(y - HUB_CENTER["y"]) <= 7

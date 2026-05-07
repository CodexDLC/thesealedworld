from __future__ import annotations

from typing import TypedDict

WORLD_WIDTH = 105
WORLD_HEIGHT = 105
REGION_SIZE = 15
ZONE_SIZE = 5
REGION_ROWS = ["A", "B", "C", "D", "E", "F", "G"]

HUB_CENTER = {"x": 52, "y": 52}
PORTAL_PARAMS = {"power": 2.5, "falloff": 0.03}


class AnchorData(TypedDict):
    x: int
    y: int
    power: float
    falloff: float
    type: str
    narrative_tags: list[str]


ANCHORS: list[AnchorData] = [
    {
        "x": 7,
        "y": 7,
        "power": 1.2,
        "falloff": 0.08,
        "type": "north_prime",
        "narrative_tags": ["frozen", "ice_crystals", "ancient_tech", "stasis"],
    },
    {
        "x": 97,
        "y": 97,
        "power": 1.2,
        "falloff": 0.08,
        "type": "south_prime",
        "narrative_tags": ["magma", "ash", "scorched_earth", "smoke"],
    },
    {
        "x": 7,
        "y": 97,
        "power": 1.2,
        "falloff": 0.08,
        "type": "west_prime",
        "narrative_tags": ["zero_gravity", "floating_rocks", "storm", "lightning"],
    },
    {
        "x": 97,
        "y": 7,
        "power": 1.2,
        "falloff": 0.08,
        "type": "east_prime",
        "narrative_tags": ["biomass", "giant_roots", "poison_spores", "mutation"],
    },
]

INFLUENCE_TAGS: dict[str, dict[tuple[int, int], list[str]]] = {
    "ice": {
        (0, 0): ["unnatural_chill", "hoarfrost_on_runes", "breath_vapor", "still_air"],
        (1, 2): ["frozen_dew", "cold_stone", "thin_ice_crust", "numbing_breeze"],
        (3, 4): ["deep_snow", "frozen_puddles", "ice_shards", "biting_wind"],
        (5, 7): ["absolute_zero", "time_stasis", "floating_ice_monoliths", "crystal_prison"],
    },
    "fire": {
        (0, 0): ["warm_stone_floor", "smell_of_ozone", "dry_throat", "distant_hum"],
        (1, 2): ["heat_haze", "warm_wind", "smell_of_sulfur", "hot_dust"],
        (3, 4): ["smoking_ground", "scorched_grass", "burnt_soil", "falling_ash"],
        (5, 7): ["magma_ocean", "fire_storms", "obsidian_spikes", "melting_reality"],
    },
    "gravity": {
        (0, 0): ["static_tingle", "dust_motes_hovering", "light_steps", "hair_raising"],
        (1, 2): ["floating_pebbles", "distorted_horizon", "electric_hum", "pressure_drop"],
        (3, 4): ["low_gravity", "constant_lightning", "magnetic_wind", "vertigo"],
        (5, 7): ["void_rifts", "inverted_gravity", "shattered_sky", "storm_wall"],
    },
    "bio": {
        (0, 0): ["sweet_sickness_scent", "vibrant_colors", "accelerated_growth", "spores_in_light"],
        (1, 2): ["mossy_patches", "strange_flowers", "thick_air", "insect_hum"],
        (3, 4): ["giant_roots", "glowing_fungi", "thick_pollen", "rapid_mutation"],
        (5, 7): ["flesh_landscape", "giant_beating_hearts", "hive_mind", "mutation_source"],
    },
}

HYBRID_TAGS = {
    frozenset(["ice", "gravity"]): ["hail_storm", "frozen_lightning", "shattering_sky"],
    frozenset(["ice", "bio"]): ["preserved_corpses", "frozen_flowers", "hibernate"],
    frozenset(["fire", "gravity"]): ["plasma_arcs", "flying_lava", "solar_flare"],
    frozenset(["fire", "bio"]): ["boiling_swamp", "rotting_flesh", "steam", "disease"],
}

ANCHOR_ANOMALIES = {
    "north_prime": "stasis",
    "south_prime": "entropy",
    "west_prime": "gravity",
    "east_prime": "bio_mutation",
}

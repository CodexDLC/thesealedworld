"""
spawn_config.py
Глобальная конфигурация распределения популяций и мутаций.
"""

# 1. НАСЕЛЕНИЕ БИОМОВ (ОТКРЫТЫЙ МИР)
BIOME_FAMILIES: dict[str, set[str]] = {
    "city_ruins": {"bandit_gang", "rat_swarm", "goblin_tribe", "werewolf_pack", "spider_colony"},
    "forest": {
        "wolf_pack",
        "bandit_gang",
        "orc_clan",
        "spider_colony",
        "goblin_tribe",
        "werewolf_pack",
        "elemental_rift",
    },
    "swamp": {"rat_swarm", "snake_den", "insect_hive", "ant_colony", "goblin_tribe"},
    "mountains": {"golem_foundry", "elemental_rift", "bat_colony", "orc_clan"},
    "wasteland": {"orc_clan", "bandit_gang", "elemental_rift"},
    "meadow": {"wolf_pack", "goblin_tribe", "bandit_gang"},
    "hills": {"orc_clan", "wolf_pack", "goblin_tribe", "bandit_gang"},
    "canyon": {"bat_colony", "snake_den", "spider_colony", "bandit_gang", "elemental_rift"},
    "grassland": {"wolf_pack", "orc_clan", "bandit_gang"},
    "savanna": {"bat_colony", "snake_den", "insect_hive", "ant_colony"},
    "jungle": {"spider_colony", "snake_den", "insect_hive", "ant_colony"},
    "marsh": {"snake_den", "insect_hive", "rat_swarm"},
    "badlands": {"orc_clan", "bandit_gang", "elemental_rift"},
    "highlands": {"bat_colony", "orc_clan", "wolf_pack", "golem_foundry"},
}

# 2. ГЛОБАЛЬНЫЙ ФИЛЬТР ТИРОВ (TIER AVAILABILITY)
TIER_AVAILABILITY: dict[int, set[str]] = {
    0: {
        "bandit_gang",
        "rat_swarm",
        "wolf_pack",
        "goblin_tribe",
        "snake_den",
        "spider_colony",
        "werewolf_pack",
    },  # Добавлены оборотни
    1: {
        "bandit_gang",
        "rat_swarm",
        "wolf_pack",
        "goblin_tribe",
        "insect_hive",
        "snake_den",
        "spider_colony",
        "ant_colony",
    },
    2: {
        "bandit_gang",
        "wolf_pack",
        "goblin_tribe",
        "spider_colony",
        "orc_clan",
        "snake_den",
        "ant_colony",
        "bat_colony",
        "werewolf_pack",
    },
    3: {"orc_clan", "golem_foundry", "elemental_rift", "bat_colony", "insect_hive", "werewolf_pack", "spider_colony"},
    4: {"orc_clan", "golem_foundry", "elemental_rift", "werewolf_pack", "bat_colony"},
    5: {"orc_clan", "golem_foundry", "elemental_rift", "werewolf_pack"},
    6: {"all_families"},
    7: {"all_families"},
}

# 3. БЕЛЫЙ СПИСОК МУТАЦИЙ (DNA MASK)
MUTATION_TAGS_WHITELIST: set[str] = {
    # --- ICE / NORTH (Влияние Холода) ---
    "unnatural_chill",
    "hoarfrost_on_runes",
    "frozen_dew",
    "thin_ice_crust",
    "ice_shards",
    "deep_snow",
    "frozen_puddles",
    "absolute_zero",
    "time_stasis",
    "crystal_prison",
    "floating_ice_monoliths",
    # --- FIRE / SOUTH (Влияние Огня) ---
    "heat_haze",
    "smell_of_sulfur",
    "falling_ash",
    "scorched_grass",
    "smoking_ground",
    "burnt_soil",
    "magma_ocean",
    "fire_storms",
    "obsidian_spikes",
    "melting_reality",
    # --- GRAVITY / WEST (Влияние Искажения) ---
    "static_tingle",
    "dust_motes_hovering",
    "floating_pebbles",
    "distorted_horizon",
    "low_gravity",
    "constant_lightning",
    "magnetic_wind",
    "void_rifts",
    "inverted_gravity",
    "shattered_sky",
    "storm_wall",
    # --- BIO / EAST (Влияние Жизни/Гнили) ---
    "spores_in_light",
    "accelerated_growth",
    "mossy_patches",
    "strange_flowers",
    "glowing_fungi",
    "giant_roots",
    "rapid_mutation",
    "thick_pollen",
    "flesh_landscape",
    "giant_beating_hearts",
    "hive_mind",
    "mutation_source",
    # --- HYBRIDS (Смешанные зоны) ---
    "hail_storm",
    "frozen_lightning",
    "shattering_sky",
    "preserved_corpses",
    "frozen_flowers",
    "hibernate",
    "plasma_arcs",
    "flying_lava",
    "solar_flare",
    "boiling_swamp",
    "rotting_flesh",
    "disease",
    "steam",
    # --- GENERIC / MAGIC (Общие магические эффекты) ---
    "arcane_glow",
    "cursed_ground",
    "ancient_tech",
    "mana_leak",
}

# 4. КОНФИГУРАЦИЯ СКАЛИРОВАНИЯ ОТ ТИРА
TIER_SCALING_CONFIG: dict[int, dict[str, float]] = {
    0: {"stat_mult": 1.0},
    1: {"stat_mult": 1.2},
    2: {"stat_mult": 1.5},
    3: {"stat_mult": 2.0},
    4: {"stat_mult": 3.0},
    5: {"stat_mult": 4.5},
    6: {"stat_mult": 6.5},
    7: {"stat_mult": 10.0},
}

from __future__ import annotations

STARTER_ACTIVE_FAMILY_IDS: tuple[str, ...] = (
    "bandit_gang",
    "goblin_tribe",
    "rat_swarm",
    "wolf_pack",
)

ANCHOR_BOSS_FAMILY_IDS: tuple[str, ...] = ("anchor_sovereigns",)

FUTURE_FAMILY_VOCABULARY: tuple[str, ...] = (
    "ant_colony",
    "angelic_host",
    "bat_colony",
    "clockwork_army",
    "dark_elf_house",
    "demon_legion",
    "dragon_lair",
    "elemental_rift",
    "golem_foundry",
    "insect_hive",
    "lizardfolk_clan",
    "living_forest",
    "orc_clan",
    "snake_den",
    "spider_colony",
    "undead_legion",
    "vampire_coven",
    "void_spawn",
    "werewolf_pack",
)

WORLD_FAMILY_VOCABULARY: tuple[str, ...] = (
    *STARTER_ACTIVE_FAMILY_IDS,
    *ANCHOR_BOSS_FAMILY_IDS,
    *FUTURE_FAMILY_VOCABULARY,
)


def is_world_family_vocabulary_id(family_id: str) -> bool:
    return family_id in WORLD_FAMILY_VOCABULARY

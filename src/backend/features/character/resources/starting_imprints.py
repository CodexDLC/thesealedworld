from __future__ import annotations

from dataclasses import dataclass

ATTRIBUTE_KEYS: tuple[str, ...] = (
    "strength",
    "agility",
    "endurance",
    "intellect",
    "memory",
    "mental",
    "perception",
    "projection",
    "prediction",
)

DEFAULT_ATTRIBUTE_TAIL_ORDER: tuple[str, ...] = (
    "strength",
    "agility",
    "endurance",
    "perception",
    "prediction",
    "mental",
    "memory",
    "intellect",
    "projection",
)

STARTING_ATTRIBUTE_LADDER: tuple[int, ...] = (17, 16, 15, 14, 13, 12, 11, 10, 9)


@dataclass(frozen=True, slots=True)
class StartingLoadoutPack:
    item_base_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StartingImprintDefinition:
    imprint_key: str
    title: str
    primary_stats: tuple[str, ...]
    combat_style: str
    armor_pack: str
    utility_pack: str
    skill_xp: tuple[tuple[str, float], ...]
    lore_tags: tuple[str, ...] = ()
    description: str = ""


STARTING_COMBAT_STYLES: dict[str, StartingLoadoutPack] = {
    "one_handed_shield": StartingLoadoutPack(
        item_base_ids=("sword", "shield"),
    ),
    "two_handed_impact": StartingLoadoutPack(
        item_base_ids=("warhammer",),
    ),
    "two_handed_reach": StartingLoadoutPack(
        item_base_ids=("quarterstaff",),
    ),
    "sword_buckler": StartingLoadoutPack(
        item_base_ids=("sword", "buckler"),
    ),
    "dual_light": StartingLoadoutPack(
        item_base_ids=("dagger", "main_gauche"),
    ),
    "dagger_light": StartingLoadoutPack(
        item_base_ids=("dagger",),
    ),
    "mace_shield": StartingLoadoutPack(
        item_base_ids=("mace", "shield"),
    ),
    "shortbow_quiver": StartingLoadoutPack(
        item_base_ids=("shortbow", "quiver_poison"),
    ),
    "longbow_quiver": StartingLoadoutPack(
        item_base_ids=("longbow", "quiver_training"),
    ),
}

STARTING_ARMOR_PACKS: dict[str, StartingLoadoutPack] = {
    "heavy_full": StartingLoadoutPack(
        item_base_ids=(
            "plate_chest",
            "helmet",
            "gauntlets",
            "greaves",
            "wool_tunic",
            "fur_pants",
            "travel_boots",
        ),
    ),
    "medium_full": StartingLoadoutPack(
        item_base_ids=(
            "jerkin",
            "leather_cap",
            "reinforced_gloves",
            "breeches",
            "linen_shirt",
            "travel_boots",
        ),
    ),
    "light_full": StartingLoadoutPack(
        item_base_ids=(
            "leather_armor",
            "hood",
            "soft_bracers",
            "scout_leggings",
            "linen_shirt",
            "travel_boots",
        ),
    ),
}

STARTING_UTILITY_PACKS: dict[str, StartingLoadoutPack] = {
    "field_basic": StartingLoadoutPack(item_base_ids=("belt", "winter_cloak", "amulet")),
    "frontline_basic": StartingLoadoutPack(item_base_ids=("belt", "winter_cloak")),
    "mobile_basic": StartingLoadoutPack(item_base_ids=("belt", "amulet")),
}

STARTING_IMPRINTS: dict[str, StartingImprintDefinition] = {
    "starter_guard_01": StartingImprintDefinition(
        imprint_key="starter_guard_01",
        title="Слепок стража",
        primary_stats=("endurance", "strength", "perception", "mental"),
        combat_style="one_handed_shield",
        armor_pack="medium_full",
        utility_pack="field_basic",
        skill_xp=(
            ("skill_swords", 0.15),
            ("skill_shield_mastery", 0.15),
            ("skill_parrying", 0.10),
            ("skill_medium_armor", 0.10),
        ),
        lore_tags=("physical", "defensive", "starter"),
        description="Устойчивый аварийный носитель для линии щита и короткого контакта.",
    ),
    "starter_breaker_01": StartingImprintDefinition(
        imprint_key="starter_breaker_01",
        title="Слепок проломщика",
        primary_stats=("strength", "endurance", "mental", "perception"),
        combat_style="two_handed_impact",
        armor_pack="heavy_full",
        utility_pack="frontline_basic",
        skill_xp=(
            ("skill_macing", 0.15),
            ("skill_two_handed", 0.15),
            ("skill_heavy_armor", 0.10),
            ("skill_tactics", 0.10),
        ),
        lore_tags=("physical", "frontline", "starter"),
        description="Тяжелая оболочка для прямого давления и грубого удержания темпа.",
    ),
    "starter_duelist_01": StartingImprintDefinition(
        imprint_key="starter_duelist_01",
        title="Слепок дуэлянта",
        primary_stats=("agility", "perception", "prediction", "strength"),
        combat_style="sword_buckler",
        armor_pack="light_full",
        utility_pack="mobile_basic",
        skill_xp=(
            ("skill_swords", 0.15),
            ("skill_parrying", 0.15),
            ("skill_tactics", 0.10),
            ("skill_light_armor", 0.10),
        ),
        lore_tags=("physical", "mobile", "starter"),
        description="Быстрый носитель для парирования, реакции и работы на открытой линии.",
    ),
    "starter_dual_blades_01": StartingImprintDefinition(
        imprint_key="starter_dual_blades_01",
        title="Слепок двух клинков",
        primary_stats=("agility", "perception", "prediction", "memory"),
        combat_style="dual_light",
        armor_pack="light_full",
        utility_pack="mobile_basic",
        skill_xp=(
            ("skill_fencing", 0.15),
            ("skill_dual_wield", 0.15),
            ("skill_parrying", 0.10),
            ("skill_light_armor", 0.10),
        ),
        lore_tags=("physical", "dual_wield", "starter"),
        description="Легкий носитель для парного клинка, быстрых разворотов и короткой линии атаки.",
    ),
    "starter_pathfinder_01": StartingImprintDefinition(
        imprint_key="starter_pathfinder_01",
        title="Слепок следопыта",
        primary_stats=("perception", "agility", "prediction", "memory"),
        combat_style="dagger_light",
        armor_pack="light_full",
        utility_pack="mobile_basic",
        skill_xp=(
            ("skill_fencing", 0.15),
            ("skill_scouting", 0.15),
            ("skill_pathfinder", 0.10),
            ("skill_light_armor", 0.10),
        ),
        lore_tags=("physical", "scout", "starter"),
        description="Легкая оболочка для разведки, быстрых решений и боя на короткой дистанции.",
    ),
    "starter_hunter_01": StartingImprintDefinition(
        imprint_key="starter_hunter_01",
        title="Слепок охотника",
        primary_stats=("perception", "agility", "prediction", "memory"),
        combat_style="shortbow_quiver",
        armor_pack="light_full",
        utility_pack="mobile_basic",
        skill_xp=(
            ("skill_archery", 0.15),
            ("skill_scouting", 0.15),
            ("skill_pathfinder", 0.10),
            ("skill_light_armor", 0.10),
        ),
        lore_tags=("physical", "ranged", "hunter", "starter"),
        description="Легкий носитель для охоты, разведки и стрельбы с ядовитыми стрелами.",
    ),
    "starter_archer_01": StartingImprintDefinition(
        imprint_key="starter_archer_01",
        title="Слепок лучника",
        primary_stats=("perception", "agility", "strength", "prediction"),
        combat_style="longbow_quiver",
        armor_pack="light_full",
        utility_pack="mobile_basic",
        skill_xp=(
            ("skill_archery", 0.15),
            ("skill_ranged_combat", 0.15),
            ("skill_tactics", 0.10),
            ("skill_light_armor", 0.10),
        ),
        lore_tags=("physical", "ranged", "archer", "starter"),
        description="Стартовый носитель для чистой дальней линии, прицела и контроля дистанции.",
    ),
    "starter_staff_01": StartingImprintDefinition(
        imprint_key="starter_staff_01",
        title="Слепок опорного бойца",
        primary_stats=("perception", "strength", "endurance", "agility"),
        combat_style="two_handed_reach",
        armor_pack="medium_full",
        utility_pack="field_basic",
        skill_xp=(
            ("skill_polearms", 0.15),
            ("skill_two_handed", 0.15),
            ("skill_medium_armor", 0.10),
            ("skill_pathfinder", 0.10),
        ),
        lore_tags=("physical", "balanced", "starter"),
        description="Сбалансированный носитель для дистанции, контроля линии и выживания.",
    ),
    "starter_heavy_guard_01": StartingImprintDefinition(
        imprint_key="starter_heavy_guard_01",
        title="Слепок тяжелого стража",
        primary_stats=("endurance", "strength", "mental", "memory"),
        combat_style="mace_shield",
        armor_pack="heavy_full",
        utility_pack="frontline_basic",
        skill_xp=(
            ("skill_macing", 0.15),
            ("skill_shield_mastery", 0.15),
            ("skill_heavy_armor", 0.10),
            ("skill_adaptation", 0.10),
        ),
        lore_tags=("physical", "heavy", "starter"),
        description="Плотная защитная оболочка для удержания удара, щита и тяжелой линии.",
    ),
    "starter_tactician_01": StartingImprintDefinition(
        imprint_key="starter_tactician_01",
        title="Слепок тактика",
        primary_stats=("intellect", "memory", "perception", "prediction"),
        combat_style="sword_buckler",
        armor_pack="medium_full",
        utility_pack="field_basic",
        skill_xp=(
            ("skill_tactics", 0.15),
            ("skill_swords", 0.15),
            ("skill_parrying", 0.10),
            ("skill_medium_armor", 0.10),
        ),
        lore_tags=("physical", "tactical", "starter"),
        description="Носитель для расчета, чтения паттернов и симбиотической реакции в бою.",
    ),
    "starter_rift_survivor_01": StartingImprintDefinition(
        imprint_key="starter_rift_survivor_01",
        title="Слепок рифт-выжившего",
        primary_stats=("endurance", "perception", "mental", "memory"),
        combat_style="two_handed_reach",
        armor_pack="medium_full",
        utility_pack="field_basic",
        skill_xp=(
            ("skill_adaptation", 0.15),
            ("skill_pathfinder", 0.15),
            ("skill_scouting", 0.10),
            ("skill_medium_armor", 0.10),
        ),
        lore_tags=("physical", "survival", "starter"),
        description="Аварийный носитель для выживания, маршрутов и осторожного прохода через разлом.",
    ),
}

DEFAULT_STARTING_IMPRINT_KEY = "starter_guard_01"

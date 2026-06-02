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

STARTING_ATTRIBUTE_VALUES: tuple[int, ...] = (9, 10, 11, 12, 13, 14, 15, 16, 17)


def _attribute_values(
    *,
    strength: int,
    agility: int,
    endurance: int,
    intellect: int,
    memory: int,
    mental: int,
    perception: int,
    projection: int,
    prediction: int,
) -> tuple[tuple[str, int], ...]:
    values = {
        "strength": strength,
        "agility": agility,
        "endurance": endurance,
        "intellect": intellect,
        "memory": memory,
        "mental": mental,
        "perception": perception,
        "projection": projection,
        "prediction": prediction,
    }
    if set(values) != set(ATTRIBUTE_KEYS):
        raise ValueError("Manual starting imprint attributes must cover every attribute")
    if sorted(values.values()) != list(STARTING_ATTRIBUTE_VALUES):
        raise ValueError("Manual starting imprint attributes must distribute values 9..17 exactly once")
    return tuple((key, values[key]) for key in ATTRIBUTE_KEYS)


@dataclass(frozen=True, slots=True)
class StartingLoadoutPack:
    item_base_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StartingImprintDefinition:
    imprint_key: str
    title: str
    primary_stats: tuple[str, ...]
    attribute_values: tuple[tuple[str, int], ...]
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
    "polearm_reach": StartingLoadoutPack(
        item_base_ids=("halberd",),
    ),
    "sword_buckler": StartingLoadoutPack(
        item_base_ids=("sword", "buckler"),
    ),
    "dual_light": StartingLoadoutPack(
        item_base_ids=("dagger", "main_gauche"),
    ),
    "dual_fencing_light": StartingLoadoutPack(
        item_base_ids=("stiletto", "stiletto"),
    ),
    "dual_sword_fencing": StartingLoadoutPack(
        item_base_ids=("sword", "stiletto"),
    ),
    "dual_mace_fencing": StartingLoadoutPack(
        item_base_ids=("mace", "main_gauche"),
    ),
    "mace_shield": StartingLoadoutPack(
        item_base_ids=("mace", "kite_shield"),
    ),
    "shortbow_quiver": StartingLoadoutPack(
        item_base_ids=("shortbow", "quiver_frost"),
    ),
    "longbow_quiver": StartingLoadoutPack(
        item_base_ids=("longbow", "quiver_fire"),
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
        title="Слепок мечника со щитом [МЕ/ЩТ/СБ]",
        primary_stats=("endurance", "strength", "agility", "mental"),
        attribute_values=_attribute_values(
            strength=16,
            agility=15,
            endurance=17,
            intellect=9,
            memory=11,
            mental=14,
            perception=13,
            projection=10,
            prediction=12,
        ),
        combat_style="one_handed_shield",
        armor_pack="medium_full",
        utility_pack="field_basic",
        skill_xp=(
            ("skill_swords", 0.20),
            ("skill_shield_mastery", 0.15),
            ("skill_medium_armor", 0.10),
        ),
        lore_tags=("physical", "defensive", "starter"),
        description="Устойчивый аварийный носитель для линии щита и короткого контакта.",
    ),
    "starter_breaker_01": StartingImprintDefinition(
        imprint_key="starter_breaker_01",
        title="Слепок двуручного молота [БУ/ДВ/ТБ]",
        primary_stats=("strength", "endurance", "prediction", "mental"),
        attribute_values=_attribute_values(
            strength=17,
            agility=13,
            endurance=16,
            intellect=9,
            memory=10,
            mental=14,
            perception=12,
            projection=11,
            prediction=15,
        ),
        combat_style="two_handed_impact",
        armor_pack="heavy_full",
        utility_pack="frontline_basic",
        skill_xp=(
            ("skill_macing", 0.20),
            ("skill_two_handed", 0.15),
            ("skill_heavy_armor", 0.10),
        ),
        lore_tags=("physical", "frontline", "starter"),
        description="Тяжелая оболочка для прямого давления и грубого удержания темпа.",
    ),
    "starter_dual_blades_01": StartingImprintDefinition(
        imprint_key="starter_dual_blades_01",
        title="Слепок двух стилетов [ФЕ/ДУ/ЛБ]",
        primary_stats=(
            "agility",
            "perception",
            "prediction",
            "strength",
            "memory",
            "projection",
            "endurance",
            "intellect",
            "mental",
        ),
        attribute_values=_attribute_values(
            strength=14,
            agility=17,
            endurance=11,
            intellect=10,
            memory=13,
            mental=9,
            perception=16,
            projection=12,
            prediction=15,
        ),
        combat_style="dual_fencing_light",
        armor_pack="light_full",
        utility_pack="mobile_basic",
        skill_xp=(
            ("skill_fencing", 0.20),
            ("skill_dual_wield", 0.15),
            ("skill_light_armor", 0.10),
        ),
        lore_tags=("physical", "dual_wield", "starter"),
        description="Легкий носитель двух коротких клинков для темпа, пробития и быстрой атаки.",
    ),
    "starter_dual_sword_01": StartingImprintDefinition(
        imprint_key="starter_dual_sword_01",
        title="Слепок меча и стилета [МЕ/ФЕ/ДУ/СБ]",
        primary_stats=(
            "strength",
            "agility",
            "endurance",
            "perception",
            "memory",
            "prediction",
            "projection",
            "mental",
            "intellect",
        ),
        attribute_values=_attribute_values(
            strength=17,
            agility=16,
            endurance=15,
            intellect=9,
            memory=13,
            mental=10,
            perception=14,
            projection=11,
            prediction=12,
        ),
        combat_style="dual_sword_fencing",
        armor_pack="medium_full",
        utility_pack="field_basic",
        skill_xp=(
            ("skill_swords", 0.10),
            ("skill_fencing", 0.10),
            ("skill_medium_armor", 0.15),
            ("skill_dual_wield", 0.10),
        ),
        lore_tags=("physical", "dual_wield", "medium", "starter"),
        description="Средний носитель меча и короткого клинка для стабильного размена и пробития.",
    ),
    "starter_dual_mace_01": StartingImprintDefinition(
        imprint_key="starter_dual_mace_01",
        title="Слепок булавы и даги [БУ/ФЕ/ДУ/ТБ]",
        primary_stats=(
            "strength",
            "endurance",
            "agility",
            "mental",
            "memory",
            "perception",
            "prediction",
            "projection",
            "intellect",
        ),
        attribute_values=_attribute_values(
            strength=17,
            agility=15,
            endurance=16,
            intellect=9,
            memory=13,
            mental=14,
            perception=12,
            projection=10,
            prediction=11,
        ),
        combat_style="dual_mace_fencing",
        armor_pack="heavy_full",
        utility_pack="frontline_basic",
        skill_xp=(
            ("skill_macing", 0.10),
            ("skill_fencing", 0.10),
            ("skill_heavy_armor", 0.15),
            ("skill_dual_wield", 0.10),
        ),
        lore_tags=("physical", "dual_wield", "heavy", "starter"),
        description="Тяжелый носитель булавы и парирующего клинка для плотного ближнего размена.",
    ),
    "starter_hunter_01": StartingImprintDefinition(
        imprint_key="starter_hunter_01",
        title="Слепок охотника [ЛК/ДБ/ЛБ]",
        primary_stats=(
            "agility",
            "perception",
            "prediction",
            "strength",
            "memory",
            "endurance",
            "projection",
            "mental",
            "intellect",
        ),
        attribute_values=_attribute_values(
            strength=14,
            agility=17,
            endurance=12,
            intellect=9,
            memory=13,
            mental=10,
            perception=16,
            projection=11,
            prediction=15,
        ),
        combat_style="shortbow_quiver",
        armor_pack="light_full",
        utility_pack="mobile_basic",
        skill_xp=(
            ("skill_archery", 0.20),
            ("skill_ranged_combat", 0.15),
            ("skill_light_armor", 0.10),
        ),
        lore_tags=("physical", "ranged", "hunter", "starter"),
        description="Легкий носитель для охоты, разведки и стрельбы ледяными стрелами.",
    ),
    "starter_archer_01": StartingImprintDefinition(
        imprint_key="starter_archer_01",
        title="Слепок лучника [ЛК/ДБ/ЛБ]",
        primary_stats=(
            "agility",
            "perception",
            "strength",
            "prediction",
            "memory",
            "projection",
            "endurance",
            "mental",
            "intellect",
        ),
        attribute_values=_attribute_values(
            strength=15,
            agility=17,
            endurance=11,
            intellect=9,
            memory=13,
            mental=10,
            perception=16,
            projection=12,
            prediction=14,
        ),
        combat_style="longbow_quiver",
        armor_pack="light_full",
        utility_pack="mobile_basic",
        skill_xp=(
            ("skill_archery", 0.20),
            ("skill_ranged_combat", 0.15),
            ("skill_light_armor", 0.10),
        ),
        lore_tags=("physical", "ranged", "archer", "starter"),
        description="Стартовый носитель для чистой дальней линии, прицела и контроля дистанции.",
    ),
    "starter_heavy_guard_01": StartingImprintDefinition(
        imprint_key="starter_heavy_guard_01",
        title="Слепок булавы и щита [БУ/ЩТ/ТБ]",
        primary_stats=("strength", "endurance", "prediction", "mental"),
        attribute_values=_attribute_values(
            strength=17,
            agility=12,
            endurance=16,
            intellect=9,
            memory=11,
            mental=14,
            perception=13,
            projection=10,
            prediction=15,
        ),
        combat_style="mace_shield",
        armor_pack="heavy_full",
        utility_pack="frontline_basic",
        skill_xp=(
            ("skill_macing", 0.20),
            ("skill_shield_mastery", 0.15),
            ("skill_heavy_armor", 0.10),
        ),
        lore_tags=("physical", "heavy", "starter"),
        description="Плотная защитная оболочка для удержания удара, щита и тяжелой линии.",
    ),
    "starter_tactician_01": StartingImprintDefinition(
        imprint_key="starter_tactician_01",
        title="Слепок мечника с баклером [МЕ/ЩТ/СБ]",
        primary_stats=(
            "agility",
            "strength",
            "perception",
            "mental",
            "endurance",
            "prediction",
            "memory",
            "intellect",
            "projection",
        ),
        attribute_values=_attribute_values(
            strength=16,
            agility=17,
            endurance=13,
            intellect=10,
            memory=11,
            mental=14,
            perception=15,
            projection=9,
            prediction=12,
        ),
        combat_style="sword_buckler",
        armor_pack="medium_full",
        utility_pack="field_basic",
        skill_xp=(
            ("skill_swords", 0.20),
            ("skill_shield_mastery", 0.15),
            ("skill_medium_armor", 0.10),
        ),
        lore_tags=("physical", "tactical", "starter"),
        description="Боевой носитель для чтения паттернов, щитовой линии и расчетливого давления.",
    ),
    "starter_rift_survivor_01": StartingImprintDefinition(
        imprint_key="starter_rift_survivor_01",
        title="Слепок алебардиста [ДК/ДВ/СБ]",
        primary_stats=("strength", "endurance", "agility", "perception"),
        attribute_values=_attribute_values(
            strength=17,
            agility=15,
            endurance=16,
            intellect=9,
            memory=12,
            mental=10,
            perception=14,
            projection=11,
            prediction=13,
        ),
        combat_style="polearm_reach",
        armor_pack="medium_full",
        utility_pack="field_basic",
        skill_xp=(
            ("skill_polearms", 0.20),
            ("skill_two_handed", 0.15),
            ("skill_medium_armor", 0.10),
        ),
        lore_tags=("physical", "survival", "starter"),
        description="Боевой выживальщик с древковым оружием для удержания дистанции и прохода через разлом.",
    ),
}

DEFAULT_STARTING_IMPRINT_KEY = "starter_guard_01"

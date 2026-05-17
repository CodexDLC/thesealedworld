from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MonsterEquipmentKind = Literal["weapon", "armor", "shield"]


@dataclass(frozen=True, slots=True)
class MonsterNaturalEquipmentMapping:
    natural_key: str
    base_id: str
    item_kind: MonsterEquipmentKind
    default_slot: str
    name_ru: str | None = None
    material_id: str | None = None
    item_grade: str = "common"
    tags: tuple[str, ...] = ()


NATURAL_EQUIPMENT_MAPPINGS: dict[str, MonsterNaturalEquipmentMapping] = {
    # ── КРЫСЫ: оружие (прогрессия по ролям) ──────────────────────────
    "rat_bite_claws": MonsterNaturalEquipmentMapping(
        natural_key="rat_bite_claws",
        base_id="knife",
        name_ru="Крысиные клыки и когти",
        item_kind="weapon",
        default_slot="main_hand",
        tags=("natural_weapon", "fangs", "claws", "rat"),
    ),
    "rat_veteran_claws": MonsterNaturalEquipmentMapping(
        natural_key="rat_veteran_claws",
        base_id="dagger",
        name_ru="Острые когти крысы",
        item_kind="weapon",
        default_slot="main_hand",
        tags=("natural_weapon", "claws", "rat"),
    ),
    "rat_elite_claws": MonsterNaturalEquipmentMapping(
        natural_key="rat_elite_claws",
        base_id="katar",
        name_ru="Мощные когти крысы",
        item_kind="weapon",
        default_slot="main_hand",
        tags=("natural_weapon", "claws", "rat"),
    ),
    "rat_boss_claws": MonsterNaturalEquipmentMapping(
        natural_key="rat_boss_claws",
        base_id="rapier",
        name_ru="Огромные клыки крысиного короля",
        item_kind="weapon",
        default_slot="main_hand",
        tags=("natural_weapon", "fangs", "claws", "rat"),
    ),
    "rat_left_claws": MonsterNaturalEquipmentMapping(
        natural_key="rat_left_claws",
        base_id="dagger",
        name_ru="Левая лапа крысы",
        item_kind="weapon",
        default_slot="off_hand",
        tags=("natural_weapon", "rat", "claws", "offhand"),
    ),
    # ── КРЫСЫ: броня ─────────────────────────────────────────────────
    "rat_light_hide": MonsterNaturalEquipmentMapping(
        natural_key="rat_light_hide",
        base_id="leather_armor",
        name_ru="Лёгкая звериная шкура",
        item_kind="armor",
        default_slot="chest_armor",
        tags=("natural_armor", "rat", "hide", "light"),
    ),
    "rat_medium_hide": MonsterNaturalEquipmentMapping(
        natural_key="rat_medium_hide",
        base_id="jerkin",
        name_ru="Плотная шкура крысы",
        item_kind="armor",
        default_slot="chest_armor",
        tags=("natural_armor", "rat", "hide", "medium"),
    ),
    "rat_heavy_hide": MonsterNaturalEquipmentMapping(
        natural_key="rat_heavy_hide",
        base_id="plate_chest",
        name_ru="Толстая шкура крупной крысы",
        item_kind="armor",
        default_slot="chest_armor",
        tags=("natural_armor", "rat", "hide", "heavy"),
    ),
    # ── ВОЛКИ: оружие ────────────────────────────────────────────────
    "wolf_young_fangs": MonsterNaturalEquipmentMapping(
        natural_key="wolf_young_fangs",
        base_id="dagger",
        name_ru="Молодые волчьи клыки",
        item_kind="weapon",
        default_slot="main_hand",
        tags=("natural_weapon", "fangs", "wolf"),
    ),
    "wolf_bite_claws": MonsterNaturalEquipmentMapping(
        natural_key="wolf_bite_claws",
        base_id="rapier",
        name_ru="Волчьи клыки и когти",
        item_kind="weapon",
        default_slot="main_hand",
        tags=("natural_weapon", "fangs", "claws", "wolf"),
    ),
    "wolf_elite_fangs": MonsterNaturalEquipmentMapping(
        natural_key="wolf_elite_fangs",
        base_id="rapier",
        name_ru="Мощные клыки хищника",
        item_kind="weapon",
        default_slot="main_hand",
        tags=("natural_weapon", "fangs", "wolf"),
    ),
    "wolf_alpha_fangs": MonsterNaturalEquipmentMapping(
        natural_key="wolf_alpha_fangs",
        base_id="rapier",
        name_ru="Клыки Альфы",
        item_kind="weapon",
        default_slot="main_hand",
        tags=("natural_weapon", "fangs", "claws", "wolf"),
    ),
    # ── ВОЛКИ: броня ─────────────────────────────────────────────────
    "wolf_hide": MonsterNaturalEquipmentMapping(
        natural_key="wolf_hide",
        base_id="leather_armor",
        name_ru="Лёгкая волчья шкура",
        item_kind="armor",
        default_slot="chest_armor",
        tags=("natural_armor", "wolf", "hide", "light"),
    ),
    "wolf_medium_hide": MonsterNaturalEquipmentMapping(
        natural_key="wolf_medium_hide",
        base_id="jerkin",
        name_ru="Плотная волчья шкура",
        item_kind="armor",
        default_slot="chest_armor",
        tags=("natural_armor", "wolf", "hide", "medium"),
    ),
    "wolf_heavy_hide": MonsterNaturalEquipmentMapping(
        natural_key="wolf_heavy_hide",
        base_id="plate_chest",
        name_ru="Толстая шкура матёрого волка",
        item_kind="armor",
        default_slot="chest_armor",
        tags=("natural_armor", "wolf", "hide", "heavy"),
    ),
    # ── ЯКОРНЫЕ БОССЫ: оружие ────────────────────────────────────────
    "anchor_stasis_crown_blade": MonsterNaturalEquipmentMapping(
        natural_key="anchor_stasis_crown_blade",
        base_id="rapier",
        name_ru="Лезвие Северного Стазиса",
        item_kind="weapon",
        default_slot="main_hand",
        tags=("anchor", "stasis", "frost", "boss_weapon", "one_handed"),
    ),
    "anchor_entropy_cinder_maul": MonsterNaturalEquipmentMapping(
        natural_key="anchor_entropy_cinder_maul",
        base_id="warhammer",
        name_ru="Пепельный Молот Южной Энтропии",
        item_kind="weapon",
        default_slot="two_hand",
        tags=("anchor", "entropy", "ash_storm", "boss_weapon", "two_handed"),
    ),
    "anchor_gravity_storm_lance": MonsterNaturalEquipmentMapping(
        natural_key="anchor_gravity_storm_lance",
        base_id="rapier",
        name_ru="Штормовое Копьё Западной Гравитации",
        item_kind="weapon",
        default_slot="main_hand",
        tags=("anchor", "gravity", "lightning", "boss_weapon", "one_handed"),
    ),
    "anchor_evolution_bloom_talons": MonsterNaturalEquipmentMapping(
        natural_key="anchor_evolution_bloom_talons",
        base_id="katar",
        name_ru="Когти Восточной Эволюции",
        item_kind="weapon",
        default_slot="main_hand",
        tags=("anchor", "evolution", "living_jungle", "boss_weapon", "dual_wield"),
    ),
    # ── ЯКОРНЫЕ БОССЫ: броня ─────────────────────────────────────────
    "anchor_projection_aegis": MonsterNaturalEquipmentMapping(
        natural_key="anchor_projection_aegis",
        base_id="plate_chest",
        name_ru="Оболочка Анкорной Проекции",
        item_kind="armor",
        default_slot="chest_armor",
        tags=("anchor", "projection", "natural_armor", "raid_boss"),
    ),
}


def get_natural_equipment_mapping(natural_key: str) -> MonsterNaturalEquipmentMapping:
    mapping = NATURAL_EQUIPMENT_MAPPINGS.get(natural_key)
    if mapping is None:
        raise ValueError(f"Unknown monster natural equipment key: {natural_key}")
    return mapping

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MonsterEquipmentKind = Literal["weapon", "armor", "shield", "ammo", "accessory"]


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
    "rat_offhand_bite": MonsterNaturalEquipmentMapping(
        natural_key="rat_offhand_bite",
        base_id="dagger",
        name_ru="Крысиный укус",
        item_kind="weapon",
        default_slot="off_hand",
        tags=("natural_weapon", "rat", "bite", "fangs", "offhand"),
    ),
    "rat_bone_growth": MonsterNaturalEquipmentMapping(
        natural_key="rat_bone_growth",
        base_id="buckler",
        name_ru="Костяные наросты крысы",
        item_kind="shield",
        default_slot="off_hand",
        tags=("natural_shield", "rat", "bone_growth", "block"),
    ),
    "rat_spiked_growth": MonsterNaturalEquipmentMapping(
        natural_key="rat_spiked_growth",
        base_id="shield",
        name_ru="Шипастые наросты крысы",
        item_kind="shield",
        default_slot="off_hand",
        tags=("natural_shield", "rat", "spikes", "block", "counter"),
    ),
    "rat_poison_spit": MonsterNaturalEquipmentMapping(
        natural_key="rat_poison_spit",
        base_id="shortbow",
        name_ru="Ядовитый плевок крысы",
        item_kind="weapon",
        default_slot="two_hand",
        tags=("natural_weapon", "rat", "poison", "spit", "ranged"),
    ),
    "rat_poison_glands": MonsterNaturalEquipmentMapping(
        natural_key="rat_poison_glands",
        base_id="quiver_training",
        name_ru="Ядовитые железы крысы",
        item_kind="ammo",
        default_slot="quiver",
        tags=("natural_ammo", "rat", "poison", "glands"),
    ),
    "rat_crushing_bite": MonsterNaturalEquipmentMapping(
        natural_key="rat_crushing_bite",
        base_id="warhammer",
        name_ru="Давящий крысиный укус",
        item_kind="weapon",
        default_slot="two_hand",
        tags=("natural_weapon", "rat", "bite", "crushing", "two_handed"),
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
    # ── КРЫСЫ: бижутерия / природный фокус ──────────────────────────
    "rat_plague_gland": MonsterNaturalEquipmentMapping(
        natural_key="rat_plague_gland",
        base_id="amulet",
        name_ru="Заражённая железа крысы",
        item_kind="accessory",
        default_slot="amulet",
        tags=("natural_jewelry", "rat", "plague_gland", "magic_armor"),
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
    "wolf_young_claws": MonsterNaturalEquipmentMapping(
        natural_key="wolf_young_claws",
        base_id="knife",
        name_ru="Молодые волчьи когти",
        item_kind="weapon",
        default_slot="off_hand",
        tags=("natural_weapon", "claws", "wolf", "offhand", "swift"),
    ),
    "wolf_raking_claws": MonsterNaturalEquipmentMapping(
        natural_key="wolf_raking_claws",
        base_id="katar",
        name_ru="Раздирающие волчьи когти",
        item_kind="weapon",
        default_slot="off_hand",
        tags=("natural_weapon", "claws", "wolf", "offhand", "piercing"),
    ),
    "wolf_locking_fangs": MonsterNaturalEquipmentMapping(
        natural_key="wolf_locking_fangs",
        base_id="main_gauche",
        name_ru="Удерживающий волчий захват",
        item_kind="weapon",
        default_slot="off_hand",
        tags=("natural_weapon", "fangs", "wolf", "offhand", "control"),
    ),
    "wolf_braced_mane": MonsterNaturalEquipmentMapping(
        natural_key="wolf_braced_mane",
        base_id="buckler",
        name_ru="Жёсткий волчий загривок",
        item_kind="shield",
        default_slot="off_hand",
        tags=("natural_shield", "wolf", "mane", "block", "counter"),
    ),
    "wolf_bone_shoulders": MonsterNaturalEquipmentMapping(
        natural_key="wolf_bone_shoulders",
        base_id="shield",
        name_ru="Костистые плечи волка",
        item_kind="shield",
        default_slot="off_hand",
        tags=("natural_shield", "wolf", "shoulders", "block", "guard"),
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
    "wolf_pack_mark": MonsterNaturalEquipmentMapping(
        natural_key="wolf_pack_mark",
        base_id="amulet",
        name_ru="Метка волчьей стаи",
        item_kind="accessory",
        default_slot="amulet",
        tags=("natural_jewelry", "wolf", "pack_mark", "magic_armor"),
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

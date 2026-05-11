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
    material_id: str | None = None
    item_grade: str = "common"
    tags: tuple[str, ...] = ()


NATURAL_EQUIPMENT_MAPPINGS: dict[str, MonsterNaturalEquipmentMapping] = {
    "rat_bite_claws": MonsterNaturalEquipmentMapping(
        natural_key="rat_bite_claws",
        base_id="dagger",
        item_kind="weapon",
        default_slot="main_hand",
        tags=("natural_weapon", "rat", "bite", "claws"),
    ),
    "rat_left_claws": MonsterNaturalEquipmentMapping(
        natural_key="rat_left_claws",
        base_id="dagger",
        item_kind="weapon",
        default_slot="off_hand",
        tags=("natural_weapon", "rat", "claws", "offhand"),
    ),
    "rat_light_hide": MonsterNaturalEquipmentMapping(
        natural_key="rat_light_hide",
        base_id="leather_armor",
        item_kind="armor",
        default_slot="chest_armor",
        tags=("natural_armor", "rat", "hide", "light"),
    ),
    "wolf_bite_claws": MonsterNaturalEquipmentMapping(
        natural_key="wolf_bite_claws",
        base_id="katar",
        item_kind="weapon",
        default_slot="main_hand",
        tags=("natural_weapon", "wolf", "bite", "claws"),
    ),
    "wolf_hide": MonsterNaturalEquipmentMapping(
        natural_key="wolf_hide",
        base_id="leather_armor",
        item_kind="armor",
        default_slot="chest_armor",
        tags=("natural_armor", "wolf", "hide", "light"),
    ),
}


def get_natural_equipment_mapping(natural_key: str) -> MonsterNaturalEquipmentMapping:
    mapping = NATURAL_EQUIPMENT_MAPPINGS.get(natural_key)
    if mapping is None:
        raise ValueError(f"Unknown monster natural equipment key: {natural_key}")
    return mapping

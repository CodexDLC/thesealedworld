from typing import Any

from src.backend.features.items.resources.schemas import BaseItemDTO


def _ammo_effect(effect_id: str, *, power: float = 1.0, tags: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": effect_id,
        "params": {"power": power},
        "tags": ["arrow", *(tags or [])],
    }


def _ammo_effect_bundle(*effects: dict[str, Any]) -> dict[str, Any]:
    return {"effects": list(effects)}


QUIVERS_DB = {
    "quiver_training": BaseItemDTO(
        id="quiver_training",
        name_ru="Учебный колчан",
        narrative_description="Простой колчан с ровными тренировочными стрелами для базовой стрельбы.",
        slot="quiver",
        type="ammo",
        related_skill="skill_archery",
        allowed_materials=["woods"],
        base_power=3,
        base_durability=24,
        damage_spread=0.0,
        narrative_tags=["quiver", "arrows", "archery", "training"],
        ammo_charge_base=12,
        ammo_charge_skill_bonus=12,
    ),
    "quiver_fire": BaseItemDTO(
        id="quiver_fire",
        name_ru="Колчан огненных стрел",
        narrative_description="Колчан со стрелами, подготовленными для поджигания цели и сбивания прицела после точного попадания.",
        slot="quiver",
        type="ammo",
        related_skill="skill_archery",
        allowed_materials=["woods"],
        base_power=3,
        base_durability=20,
        damage_spread=0.0,
        narrative_tags=["quiver", "arrows", "archery", "fire", "burn"],
        ammo_charge_base=12,
        ammo_charge_skill_bonus=12,
        ammo_effect_payload=_ammo_effect_bundle(
            _ammo_effect("dot_burn", power=1.0, tags=["fire", "burn"]),
            _ammo_effect("debuff_accuracy", power=1.0, tags=["fire", "accuracy_debuff"]),
        ),
    ),
    "quiver_poison": BaseItemDTO(
        id="quiver_poison",
        name_ru="Колчан ядовитых стрел",
        narrative_description="Колчан со стрелами, обработанными ядом для длительного вреда после попадания.",
        slot="quiver",
        type="ammo",
        related_skill="skill_archery",
        allowed_materials=["woods"],
        base_power=3,
        base_durability=18,
        damage_spread=0.0,
        narrative_tags=["quiver", "arrows", "archery", "poison"],
        ammo_charge_base=12,
        ammo_charge_skill_bonus=12,
        ammo_effect_payload=_ammo_effect("dot_poison", power=1.0, tags=["poison"]),
    ),
    "quiver_broadhead": BaseItemDTO(
        id="quiver_broadhead",
        name_ru="Колчан зазубренных стрел",
        narrative_description="Колчан со стрелами с широкими зазубренными наконечниками, рассчитанными на кровоточащие раны.",
        slot="quiver",
        type="ammo",
        related_skill="skill_archery",
        allowed_materials=["woods"],
        base_power=3,
        base_durability=22,
        damage_spread=0.0,
        narrative_tags=["quiver", "arrows", "archery", "broadhead", "bleed"],
        ammo_charge_base=12,
        ammo_charge_skill_bonus=12,
        ammo_effect_payload=_ammo_effect_bundle(
            _ammo_effect("dot_bleed", power=1.0, tags=["bleed", "physical"]),
            _ammo_effect("debuff_armor", power=1.0, tags=["bleed", "armor_debuff"]),
        ),
    ),
    "quiver_frost": BaseItemDTO(
        id="quiver_frost",
        name_ru="Колчан ледяных стрел",
        narrative_description="Колчан со стрелами, которые наносят холодный урон и сковывают движения цели после точного попадания.",
        slot="quiver",
        type="ammo",
        related_skill="skill_archery",
        allowed_materials=["woods"],
        base_power=3,
        base_durability=20,
        damage_spread=0.0,
        narrative_tags=["quiver", "arrows", "archery", "ice", "debuff"],
        ammo_charge_base=12,
        ammo_charge_skill_bonus=12,
        ammo_effect_payload=_ammo_effect_bundle(
            _ammo_effect("dot_frost", power=1.0, tags=["ice", "frost"]),
            _ammo_effect("debuff_evasion", power=1.0, tags=["ice", "evasion_debuff"]),
        ),
    ),
    "quiver_bodkin": BaseItemDTO(
        id="quiver_bodkin",
        name_ru="Колчан бронебойных стрел",
        narrative_description="Колчан со стрелами с узкими бронебойными наконечниками для работы по защите.",
        slot="quiver",
        type="ammo",
        related_skill="skill_archery",
        allowed_materials=["woods"],
        base_power=3,
        base_durability=24,
        damage_spread=0.0,
        narrative_tags=["quiver", "arrows", "archery", "bodkin", "armor_piercing"],
        ammo_charge_base=12,
        ammo_charge_skill_bonus=12,
        ammo_effect_payload=_ammo_effect("debuff_armor", power=1.0, tags=["bodkin", "armor_debuff"]),
    ),
}

__all__ = ["QUIVERS_DB"]

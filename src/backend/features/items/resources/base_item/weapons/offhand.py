from src.backend.features.items.resources.schemas import BaseItemDTO

OFFHAND_DB = {
    "shield": BaseItemDTO(
        id="shield",
        name_ru="Щит",
        narrative_description="Полноразмерный щит для принятия удара, удержания линии и силового давления плечом.",
        slot="off_hand",
        type="armor",
        defense_type="physical",
        related_skill="skill_shield_mastery",
        allowed_materials=["woods", "ingots"],
        base_power=8,
        base_durability=80,
        damage_spread=0.0,
        narrative_tags=["shield", "block", "protection"],
        implicit_bonuses={
            "shield_block_chance": 0.10,
            "evasion_penalty": -0.25,
        },
        triggers=["block.weapon_shield_bash_on_block"],
    ),
    "buckler": BaseItemDTO(
        id="buckler",
        name_ru="Баклер",
        narrative_description="Небольшой ручной щит для парирования, быстрых сбивов и контратак на близкой дистанции.",
        slot="off_hand",
        type="armor",
        defense_type="physical",
        related_skill="skill_parrying",
        allowed_materials=["woods", "ingots"],
        base_power=3,
        base_durability=50,
        damage_spread=0.0,
        narrative_tags=["buckler", "shield", "parry", "small_shield"],
        implicit_bonuses={
            "evasion_penalty": -0.15,
            "parry_chance": 0.15,
        },
        triggers=["parry.weapon_riposte_on_parry"],
    ),
}

__all__ = ["OFFHAND_DB"]

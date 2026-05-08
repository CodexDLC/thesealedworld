from src.backend.features.items.resources.schemas import BaseItemDTO

POLEARMS_DB = {
    "spear": BaseItemDTO(
        id="spear",
        name_ru="Копье",
        narrative_description="Длинное древковое оружие для удержания дистанции, прямых уколов и работы из-за щита.",
        slot="main_hand",
        type="weapon",
        damage_type="physical",
        related_skill="skill_polearms",
        allowed_materials=["woods", "ingots"],
        base_power=7,
        damage_spread=0.14,
        base_durability=65,
        narrative_tags=["spear", "polearm", "reach", "piercing"],
        implicit_bonuses={
            "accuracy_penalty": 0.10,
            "main_hand_penetration": 0.08,
            "physical_crit_chance": 0.04,
            "parry_chance": 0.04,
        },
        triggers=["crit.piercing_crit"],
    ),
    "quarterstaff": BaseItemDTO(
        id="quarterstaff",
        name_ru="Боевой посох",
        narrative_description="Прочный посох для оборонительного боя, перехватов и быстрых ударов с обеих сторон.",
        slot="two_hand",
        type="weapon",
        damage_type="physical",
        defense_type="physical",
        related_skill="skill_polearms",
        allowed_materials=["woods"],
        base_power=8,
        damage_spread=0.12,
        base_durability=100,
        narrative_tags=["staff", "polearm", "defensive", "monk"],
        implicit_bonuses={
            "accuracy_penalty": 0.08,
            "physical_crit_chance": 0.02,
            "parry_chance": 0.10,
            "counter_attack_chance": 0.08,
        },
        triggers=["crit.stun_on_crit"],
    ),
}

__all__ = ["POLEARMS_DB"]

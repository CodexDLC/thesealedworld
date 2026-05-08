from src.backend.features.items.resources.schemas import BaseItemDTO

ARCHERY_DB = {
    "sling": BaseItemDTO(
        id="sling",
        name_ru="Праща",
        narrative_description="Простое дальнобойное оружие для быстрых бросков камня с хорошей мобильностью и слабой пробивной силой.",
        slot="main_hand",
        type="weapon",
        damage_type="physical",
        related_skill="skill_archery",
        allowed_materials=["leathers", "cloths"],
        base_power=4,
        damage_spread=0.24,
        base_durability=30,
        narrative_tags=["sling", "archery", "ranged", "mobile"],
        implicit_bonuses={
            "accuracy_penalty": 0.14,
            "physical_crit_chance": 0.03,
            "evasion": 0.03,
        },
        triggers=["crit.stun_on_crit"],
    ),
    "shortbow": BaseItemDTO(
        id="shortbow",
        name_ru="Короткий лук",
        narrative_description="Легкий лук для быстрой стрельбы на средней дистанции и маневренного боя.",
        slot="two_hand",
        type="weapon",
        damage_type="physical",
        related_skill="skill_archery",
        allowed_materials=["woods"],
        base_power=7,
        damage_spread=0.14,
        base_durability=40,
        narrative_tags=["bow", "archery", "ranger", "fast"],
        implicit_bonuses={
            "accuracy_penalty": 0.12,
            "physical_crit_chance": 0.04,
            "evasion": 0.03,
        },
        triggers=["control.evasive_shot"],
    ),
}

__all__ = ["ARCHERY_DB"]

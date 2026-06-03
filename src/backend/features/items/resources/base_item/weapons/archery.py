from src.backend.features.items.resources.schemas import BaseItemDTO

ARCHERY_DB = {
    "shortbow": BaseItemDTO(
        id="shortbow",
        name_ru="Короткий лук",
        narrative_description="Легкий лук для быстрой стрельбы на средней дистанции и маневренного боя.",
        slot="two_hand",
        type="weapon",
        damage_type="physical",
        related_skill="skill_archery",
        allowed_materials=["woods"],
        base_power=8,
        damage_spread=0.14,
        base_durability=40,
        narrative_tags=["bow", "archery", "ranger", "fast"],
        implicit_bonuses={
            "main_hand_accuracy_penalty": 0.08,
            "physical_crit_chance": 0.03,
        },
        triggers=["control.weapon_evasive_shot"],
    ),
    "longbow": BaseItemDTO(
        id="longbow",
        name_ru="Длинный лук",
        narrative_description="Высокий лук для прицельной стрельбы с большой дистанции и сильного натяжения.",
        slot="two_hand",
        type="weapon",
        damage_type="physical",
        related_skill="skill_archery",
        allowed_materials=["woods"],
        base_power=11,
        damage_spread=0.16,
        base_durability=46,
        narrative_tags=["bow", "archery", "ranger", "longbow", "precision"],
        implicit_bonuses={
            "main_hand_accuracy_penalty": 0.10,
            "physical_crit_chance": 0.04,
        },
        triggers=["crit.weapon_precision_crit"],
    ),
    "composite_bow": BaseItemDTO(
        id="composite_bow",
        name_ru="Композитный лук",
        narrative_description="Составной лук с жесткими плечами: медленнее короткого, но лучше пробивает защиту.",
        slot="two_hand",
        type="weapon",
        damage_type="physical",
        related_skill="skill_archery",
        allowed_materials=["woods", "leathers"],
        base_power=11,
        damage_spread=0.12,
        base_durability=52,
        narrative_tags=["bow", "archery", "ranger", "composite", "armor_piercing"],
        implicit_bonuses={
            "main_hand_accuracy_penalty": 0.11,
            "physical_crit_chance": 0.05,
        },
        triggers=["crit.weapon_piercing_crit"],
    ),
}

__all__ = ["ARCHERY_DB"]

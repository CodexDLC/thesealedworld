from src.backend.features.items.resources.schemas import BaseItemDTO

SWORDS_DB = {
    "sword": BaseItemDTO(
        id="sword",
        name_ru="Меч",
        narrative_description="Сбалансированное одноручное оружие для рубящих и колющих ударов без явных слабостей.",
        slot="main_hand",
        type="weapon",
        damage_type="physical",
        related_skill="skill_swords",
        allowed_materials=["ingots"],
        base_power=6,
        damage_spread=0.1,
        base_durability=60,
        narrative_tags=["sword", "balanced", "blade"],
        implicit_bonuses={
            "accuracy_penalty": 0.08,
            "physical_crit_chance": 0.05,
            "parry_chance": 0.10,
        },
        triggers=["crit.bleed_on_crit"],
    ),
    "katana": BaseItemDTO(
        id="katana",
        name_ru="Катана",
        narrative_description="Изогнутый двуручный клинок, рассчитанный на быстрый чистый разрез и точный ритм боя.",
        slot="two_hand",
        type="weapon",
        damage_type="physical",
        related_skill="skill_swords",
        allowed_materials=["ingots"],
        base_power=10,
        damage_spread=0.1,
        base_durability=65,
        narrative_tags=["katana", "samurai", "fast_blade"],
        implicit_bonuses={
            "accuracy_penalty": 0.12,
            "physical_crit_chance": 0.15,
            "parry_chance": 0.08,
            "bleed_damage_bonus": 0.20,
        },
        triggers=["crit.bleed_on_crit"],
    ),
}

__all__ = ["SWORDS_DB"]

from src.backend.features.items.resources.schemas import BaseItemDTO

FENCING_DB = {
    "dagger": BaseItemDTO(
        id="dagger",
        name_ru="Кинжал",
        narrative_description="Короткий клинок для быстрых уколов, скрытого ношения и точного добивания вблизи.",
        slot="main_hand",
        extra_slots=["off_hand"],
        type="weapon",
        damage_type="physical",
        related_skill="skill_fencing",
        allowed_materials=["ingots"],
        base_power=3,
        damage_spread=0.08,
        base_durability=40,
        narrative_tags=["dagger", "fencing", "swift", "piercing"],
        implicit_bonuses={
            "accuracy_penalty": 0.04,
            "physical_crit_chance": 0.12,
            "parry_chance": 0.12,
        },
        triggers=["crit.bleed_on_crit"],
    ),
}

__all__ = ["FENCING_DB"]

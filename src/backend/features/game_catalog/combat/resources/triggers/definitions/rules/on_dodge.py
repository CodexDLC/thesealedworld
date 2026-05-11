from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
    default_trigger_proc_event_texts,
)
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import pipeline_mutation
from src.backend.features.game_catalog.combat.resources.triggers.schemas import (
    TriggerCatalogEntryDTO,
    TriggerTechnicalDTO,
)

ON_DODGE_CATALOG: list[TriggerCatalogEntryDTO] = [
    TriggerCatalogEntryDTO(
        key="combat.trigger.dodge.counter_on_dodge",
        technical=TriggerTechnicalDTO(
            trigger_id="counter_on_dodge",
            event="ON_DODGE",
            chance=1.0,
            pipeline_mutations=[pipeline_mutation("chain.trigger_counter_attack")],
            allowed_sources=["weapon", "feint", "style", "monster"],
            display_policy="separate",
            tags=["reaction", "dodge", "counter"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="counter_on_dodge",
            display_name="Контратака (уклонение)",
            short_description="Успешное уклонение активирует контратаку.",
            humanoid_event_texts=CombatEventTextSetDTO(
                dodge_proc=[
                    "{target} уклоняется от {source} и переходит в контратаку.",
                    "{target} скользит мимо удара {source} и отвечает.",
                ],
                counter=["{target} контратакует {source} после уклонения."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Контратака (уклонение)"),
        ),
    ),
]

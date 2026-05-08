from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
    default_trigger_proc_event_texts,
)
from src.backend.features.game_catalog.combat.resources.triggers.schemas import (
    TriggerCatalogEntryDTO,
    TriggerTechnicalDTO,
)

ON_PARRY_CATALOG: list[TriggerCatalogEntryDTO] = [
    TriggerCatalogEntryDTO(
        key="combat.trigger.parry.disarm_on_parry",
        technical=TriggerTechnicalDTO(
            trigger_id="disarm_on_parry",
            event="ON_PARRY",
            chance=0.5,
            mutations={"add_effect": {"id": "disarm"}},
            applied_effect_ids=["disarm"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="disarm_on_parry",
            display_name="Обезоруживание (парирование)",
            short_description="Успешное парирование с шансом обезоруживает врага.",
            humanoid_event_texts=CombatEventTextSetDTO(
                parry_proc=["{target} перехватывает оружие {source}, выбивая его из рук."],
                apply_effect=["{target} накладывает {effect} на {source}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Обезоруживание (парирование)"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.parry.counter_on_parry",
        technical=TriggerTechnicalDTO(
            trigger_id="counter_on_parry",
            event="ON_PARRY",
            chance=1.0,
            mutations={
                "state.allow_counter_on_parry": True,
                "state.check_counter": True,
            },
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="counter_on_parry",
            display_name="Контратака (парирование)",
            short_description="Успешное парирование активирует контратаку.",
            humanoid_event_texts=CombatEventTextSetDTO(
                parry_proc=[
                    "{target} парирует {source} и немедленно отвечает.",
                    "{target} использует момент парирования для контрудара.",
                ],
                counter=["{target} контратакует {source} после парирования."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Контратака (парирование)"),
        ),
    ),
]

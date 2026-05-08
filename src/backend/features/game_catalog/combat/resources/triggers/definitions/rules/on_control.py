from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
    default_trigger_proc_event_texts,
)
from src.backend.features.game_catalog.combat.resources.triggers.schemas import (
    TriggerCatalogEntryDTO,
    TriggerTechnicalDTO,
)

ON_CONTROL_CATALOG: list[TriggerCatalogEntryDTO] = [
    TriggerCatalogEntryDTO(
        key="combat.trigger.control.stun_on_hit",
        technical=TriggerTechnicalDTO(
            trigger_id="stun_on_hit",
            event="ON_CHECK_CONTROL",
            chance=0.5,
            mutations={"add_effect": {"id": "stun"}},
            applied_effect_ids=["stun"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="stun_on_hit",
            display_name="Оглушение (удар)",
            short_description="Успешное попадание с шансом оглушает цель.",
            humanoid_event_texts=CombatEventTextSetDTO(
                hit_proc=["{source} наносит оглушающий удар по {target}."],
                apply_effect=["{target} получает {effect}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Оглушение (удар)"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.control.bleed_on_hit",
        technical=TriggerTechnicalDTO(
            trigger_id="bleed_on_hit",
            event="ON_CHECK_CONTROL",
            chance=1.0,
            mutations={"add_effect": {"id": "dot_bleed"}},
            applied_effect_ids=["dot_bleed"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="bleed_on_hit",
            display_name="Кровотечение (удар)",
            short_description="Успешное попадание вызывает кровотечение.",
            humanoid_event_texts=CombatEventTextSetDTO(
                hit_proc=["{source} наносит рассекающий удар по {target}."],
                apply_effect=["{source} накладывает {effect} на {target}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Кровотечение (удар)"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.control.evasive_shot",
        technical=TriggerTechnicalDTO(
            trigger_id="evasive_shot",
            event="ON_CHECK_CONTROL",
            chance=1.0,
            mutations={"add_effect": {"id": "marker_evasion"}},
            applied_effect_ids=["marker_evasion"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="evasive_shot",
            display_name="Уклонение (выстрел)",
            short_description="Попадание даёт возможность гарантированно уклониться.",
            humanoid_event_texts=CombatEventTextSetDTO(
                hit_proc=["{source} поражает {target} и занимает выгодную позицию."],
                apply_effect=["{source} накладывает {effect} на {target}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Уклонение (выстрел)"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.control.knockdown_on_hit",
        technical=TriggerTechnicalDTO(
            trigger_id="knockdown_on_hit",
            event="ON_CHECK_CONTROL",
            chance=1.0,
            mutations={"add_effect": {"id": "knockdown"}},
            applied_effect_ids=["knockdown"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="knockdown_on_hit",
            display_name="Сбивание с ног (удар)",
            short_description="Попадание сбивает противника с ног.",
            humanoid_event_texts=CombatEventTextSetDTO(
                hit_proc=["{source} сбивает {target} с ног мощным ударом."],
                apply_effect=["{target} получает {effect}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Сбивание с ног (удар)"),
        ),
    ),
]

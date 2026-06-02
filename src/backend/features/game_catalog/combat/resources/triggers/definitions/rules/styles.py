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

STYLE_CATALOG: list[TriggerCatalogEntryDTO] = [
    TriggerCatalogEntryDTO(
        key="combat.trigger.style.2h_ignore",
        technical=TriggerTechnicalDTO(
            trigger_id="style_2h_ignore",
            event="ON_ACCURACY_CHECK",
            chance=0.25,
            pipeline_mutations=[
                pipeline_mutation("target_parry_mult", 0.65),
                pipeline_mutation("target_block_mult", 0.65),
            ],
            allowed_sources=["style"],
            display_policy="merge",
            tags=["style", "defense_pressure", "anti_parry", "anti_block"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="style_2h_ignore",
            display_name="Пробитие (стиль)",
            short_description="Тяжелый замах подавляет парирование и блок.",
            humanoid_event_texts=CombatEventTextSetDTO(
                proc=["{source} пробивает защиту {target} мощным ударом."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Пробитие (стиль)"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.style.shield_reflect",
        technical=TriggerTechnicalDTO(
            trigger_id="style_shield_reflect",
            event="ON_BLOCK",
            chance=0.25,
            pipeline_mutations=[],
            allowed_sources=["style"],
            display_policy="merge",
            tags=["style", "block", "reflect"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="style_shield_reflect",
            display_name="Отражение (стиль)",
            short_description=("При контратакующей ветке щитового блока отмечает ответ щитом."),
            humanoid_event_texts=CombatEventTextSetDTO(
                block_proc=["{target} частично гасит удар {source} щитом."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Отражение (стиль)"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.style.ranged_perfect_backstep",
        technical=TriggerTechnicalDTO(
            trigger_id="style_ranged_perfect_backstep",
            event="ON_PRE_EVASION",
            chance=0.25,
            chance_skill_key="skill_ranged_combat",
            chance_skill_scale=0.0,
            chance_cap=0.25,
            pipeline_mutations=[pipeline_mutation("ranged.next_position_override", "far")],
            allowed_sources=["style"],
            display_policy="merge",
            tags=["style", "ranged_combat", "position", "perfect_backstep"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="style_ranged_perfect_backstep",
            display_name="Идеальный отскок",
            short_description=(
                "С шансом до 25% разрывает дистанцию в текущем размене; на дальней линии дает критический ответ."
            ),
            humanoid_event_texts=CombatEventTextSetDTO(
                dodge_proc=["{target} отрывается от {source} и ловит окно для ответного выстрела."],
                proc=["{target} разрывает дистанцию и удерживает дальнюю линию."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Идеальный отскок"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.style.dual_cross_cut",
        technical=TriggerTechnicalDTO(
            trigger_id="style_dual_cross_cut",
            event="ON_CRIT",
            chance=0.25,
            chance_cap=0.25,
            pipeline_mutations=[],
            allowed_sources=["style"],
            display_policy="separate",
            tags=["style", "dual_wield", "crit", "cross_cut"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="style_dual_cross_cut",
            display_name="Перекрестный срез",
            short_description="При крите две руки могут резко усилить текущий критический удар.",
            humanoid_event_texts=CombatEventTextSetDTO(
                proc=["{source} пересекает линии ударов и глубже раскрывает защиту {target}."],
                crit=["{source} усиливает критический удар перекрестным срезом."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Перекрестный срез"),
        ),
    ),
]

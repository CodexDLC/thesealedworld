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
            pipeline_mutations=[pipeline_mutation("force.dodge")],
            applied_effect_ids=["debuff_ranged_repositioning"],
            allowed_sources=["style"],
            display_policy="merge",
            tags=["style", "ranged_combat", "dodge", "perfect_backstep"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="style_ranged_perfect_backstep",
            display_name="Идеальный отскок",
            short_description=(
                "С шансом до 25% превращает входящую атаку в гарантированный уворот, "
                "но снижает урон следующего размена."
            ),
            humanoid_event_texts=CombatEventTextSetDTO(
                dodge_proc=["{target} делает идеальный отскок от атаки {source}."],
                proc=["{target} делает идеальный отскок."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Идеальный отскок"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.style.offhand_attack",
        technical=TriggerTechnicalDTO(
            trigger_id="style_dual_extra",
            event="ON_ACCURACY_CHECK",
            chance=0.25,
            chance_skill_key="skill_dual_wield",
            chance_skill_scale=0.25,
            chance_cap=0.50,
            pipeline_mutations=[pipeline_mutation("chain.trigger_offhand_attack")],
            allowed_sources=["style"],
            display_policy="separate",
            tags=["style", "dual_wield", "extra_strike"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="style_dual_extra",
            display_name="Удар второй рукой",
            short_description="Шанс начать атаку второй рукой после попадания основной рукой.",
            humanoid_event_texts=CombatEventTextSetDTO(
                proc=["{source} начинает замах второй рукой по {target}."],
                extra_strike=["{source} добавляет удар второй рукой."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Удар второй рукой"),
        ),
    ),
]

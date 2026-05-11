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
        key="combat.trigger.style.1h_flow",
        technical=TriggerTechnicalDTO(
            trigger_id="style_1h_flow",
            event="ON_ACCURACY_CHECK",
            chance=0.25,
            pipeline_mutations=[pipeline_mutation("chain.preserve_feint")],
            allowed_sources=["style"],
            display_policy="merge",
            tags=["style", "resource", "preserve_feint"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="style_1h_flow",
            display_name="Поток (стиль)",
            short_description="С шансом сохраняет темп: возвращает стоимость использованного финта.",
            humanoid_event_texts=CombatEventTextSetDTO(
                proc=["{source} сохраняет темп удара."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Поток (стиль)"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.style.2h_ignore",
        technical=TriggerTechnicalDTO(
            trigger_id="style_2h_ignore",
            event="ON_ACCURACY_CHECK",
            chance=0.25,
            pipeline_mutations=[
                pipeline_mutation("ignore_evasion"),
                pipeline_mutation("ignore_parry"),
                pipeline_mutation("ignore_block"),
            ],
            allowed_sources=["style"],
            display_policy="merge",
            tags=["style", "defense_bypass", "ignore_dodge", "ignore_parry", "ignore_block"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="style_2h_ignore",
            display_name="Пробитие (стиль)",
            short_description="Игнорирует броню и ослабляет защиту врага.",
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
            event="ON_BLOCK_FAIL",
            chance=0.25,
            pipeline_mutations=[pipeline_mutation("partial_absorb_reflect")],
            allowed_sources=["style"],
            display_policy="merge",
            tags=["style", "block", "reflect"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="style_shield_reflect",
            display_name="Отражение (стиль)",
            short_description="При провале блока частично гасит удар и готовит отражение.",
            humanoid_event_texts=CombatEventTextSetDTO(
                block_proc=["{target} частично гасит удар {source} щитом."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Отражение (стиль)"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.style.offhand_attack",
        technical=TriggerTechnicalDTO(
            trigger_id="style_dual_extra",
            event="ON_ACCURACY_CHECK",
            chance=0.25,
            pipeline_mutations=[pipeline_mutation("chain.trigger_offhand_attack")],
            allowed_sources=["style"],
            display_policy="separate",
            tags=["style", "dual_wield", "extra_strike"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="style_dual_extra",
            display_name="Удар второй рукой",
            short_description="Мгновенная атака второй рукой после попадания.",
            humanoid_event_texts=CombatEventTextSetDTO(
                proc=["{source} проводит молниеносный удар второй рукой по {target}."],
                extra_strike=["{source} добавляет удар второй рукой."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Удар второй рукой"),
        ),
    ),
]

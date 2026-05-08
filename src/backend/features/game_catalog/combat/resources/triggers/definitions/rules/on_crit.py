from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
    default_trigger_proc_event_texts,
)
from src.backend.features.game_catalog.combat.resources.triggers.schemas import (
    TriggerCatalogEntryDTO,
    TriggerTechnicalDTO,
)

ON_CRIT_CATALOG: list[TriggerCatalogEntryDTO] = [
    TriggerCatalogEntryDTO(
        key="combat.trigger.crit.bleed_on_crit",
        technical=TriggerTechnicalDTO(
            trigger_id="bleed_on_crit",
            event="ON_CRIT",
            chance=1.0,
            mutations={
                "formula.crit_damage_boost": False,
                "add_effect": {"id": "dot_bleed"},
            },
            applied_effect_ids=["dot_bleed"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="bleed_on_crit",
            display_name="Кровавый крит",
            short_description="Критический удар вскрывает кровотечение.",
            humanoid_long_description=(
                "Критический удар находит незащищённое место и оставляет рваную рану, "
                "из которой начинает сочиться кровь."
            ),
            humanoid_event_texts=CombatEventTextSetDTO(
                crit_proc=[
                    "{source} рассекает {target}; удар открывает кровотечение.",
                    "Крит {source} оставляет {target} с рваной раной.",
                ],
                apply_effect=["{source} накладывает {effect} на {target}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Кровавый крит"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.crit.stun_on_crit",
        technical=TriggerTechnicalDTO(
            trigger_id="stun_on_crit",
            event="ON_CRIT",
            chance=1.0,
            mutations={"add_effect": {"id": "stun"}},
            applied_effect_ids=["stun"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="stun_on_crit",
            display_name="Оглушающий крит",
            short_description="Критический удар оглушает противника.",
            humanoid_long_description="Тяжёлый критический удар ошеломляет цель, нарушая её концентрацию.",
            humanoid_event_texts=CombatEventTextSetDTO(
                crit_proc=[
                    "{source} обрушивает удар на {target}; тот теряет ориентацию.",
                    "Крит {source} оглушает {target}.",
                ],
                apply_effect=["{target} получает {effect}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Оглушающий крит"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.crit.heavy_strike_on_crit",
        technical=TriggerTechnicalDTO(
            trigger_id="heavy_strike_on_crit",
            event="ON_CRIT",
            chance=1.0,
            mutations={
                "formula.crit_damage_boost": True,
                "mods.weapon_effect_value": 3.0,
            },
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="heavy_strike_on_crit",
            display_name="Сокрушительный крит",
            short_description="Критические удары наносят тройной урон.",
            humanoid_event_texts=CombatEventTextSetDTO(
                crit_proc=["{source} вкладывает всю силу в удар по {target}: {damage} урона."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Сокрушительный крит"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.crit.true_crit",
        technical=TriggerTechnicalDTO(
            trigger_id="true_crit",
            event="ON_CRIT",
            chance=1.0,
            mutations={"force.hit_evasion": True},
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="true_crit",
            display_name="Верный крит",
            short_description="От критического удара невозможно уклониться.",
            humanoid_event_texts=CombatEventTextSetDTO(
                crit_proc=["{source} наносит неотвратимый критический удар по {target}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Верный крит"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.crit.unblockable_crit",
        technical=TriggerTechnicalDTO(
            trigger_id="unblockable_crit",
            event="ON_CRIT",
            chance=1.0,
            mutations={"restriction.ignore_block": True},
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="unblockable_crit",
            display_name="Пробивающий крит",
            short_description="Критический удар игнорирует блок щитом.",
            humanoid_event_texts=CombatEventTextSetDTO(
                crit_proc=["{source} пробивает защиту {target} критическим ударом."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Пробивающий крит"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.crit.piercing_crit",
        technical=TriggerTechnicalDTO(
            trigger_id="piercing_crit",
            event="ON_CRIT",
            chance=1.0,
            mutations={"formula.can_pierce": True},
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="piercing_crit",
            display_name="Пронзающий крит",
            short_description="Критический удар игнорирует броню.",
            humanoid_event_texts=CombatEventTextSetDTO(
                crit_proc=["{source} пронзает броню {target} критическим ударом."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Пронзающий крит"),
        ),
    ),
]

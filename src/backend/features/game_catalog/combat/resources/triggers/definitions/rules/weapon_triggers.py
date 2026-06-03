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

WEAPON_TRIGGER_CATALOG: list[TriggerCatalogEntryDTO] = [
    TriggerCatalogEntryDTO(
        key="combat.trigger.weapon.serrated_bleed_crit",
        technical=TriggerTechnicalDTO(
            trigger_id="weapon_serrated_bleed_crit",
            event="ON_CRIT",
            chance=1.0,
            applied_effect_ids=["dot_bleed"],
            allowed_sources=["weapon"],
            display_policy="merge",
            tags=["weapon", "blade", "crit", "bleed"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="weapon_serrated_bleed_crit",
            display_name="Рваный крит",
            short_description="Критический удар клинком открывает кровотечение.",
            humanoid_event_texts=CombatEventTextSetDTO(
                crit_proc=["{source} рассекает {target}; рана начинает кровоточить."],
                apply_effect=["{source} накладывает {effect} на {target}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Рваный крит"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.weapon.serrated_bleed_hit",
        technical=TriggerTechnicalDTO(
            trigger_id="weapon_serrated_bleed_hit",
            event="ON_CHECK_CONTROL",
            chance=1.0,
            applied_effect_ids=["dot_bleed"],
            allowed_sources=["weapon"],
            display_policy="merge",
            tags=["weapon", "blade", "hit", "bleed"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="weapon_serrated_bleed_hit",
            display_name="Рваный порез",
            short_description="Попадание коротким клинком вызывает кровотечение.",
            humanoid_event_texts=CombatEventTextSetDTO(
                hit_proc=["{source} режет {target} коротким клинком."],
                apply_effect=["{source} накладывает {effect} на {target}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Рваный порез"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.weapon.heavy_crit",
        technical=TriggerTechnicalDTO(
            trigger_id="weapon_heavy_crit",
            event="ON_CRIT",
            chance=1.0,
            pipeline_mutations=[
                pipeline_mutation("crit_damage_boost"),
                pipeline_mutation("weapon_effect_value", 2.0),
            ],
            allowed_sources=["weapon"],
            display_policy="merge",
            tags=["weapon", "heavy", "crit", "damage"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="weapon_heavy_crit",
            display_name="Тяжелый крит",
            short_description="Критический удар тяжелым оружием наносит усиленный урон.",
            humanoid_event_texts=CombatEventTextSetDTO(
                crit_proc=["{source} обрушивает тяжелый удар на {target}: {damage} урона."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Тяжелый крит"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.weapon.impact_stun_crit",
        technical=TriggerTechnicalDTO(
            trigger_id="weapon_impact_stun_crit",
            event="ON_CRIT",
            chance=1.0,
            applied_effect_ids=["stun", "force_ranged_close"],
            allowed_sources=["weapon"],
            display_policy="merge",
            tags=["weapon", "impact", "crit", "stun", "anti_archer"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="weapon_impact_stun_crit",
            display_name="Оглушающий удар",
            short_description="Критический удар дробящим оружием оглушает цель.",
            humanoid_event_texts=CombatEventTextSetDTO(
                crit_proc=["{source} сбивает {target} сокрушительным ударом."],
                apply_effect=["{target} получает {effect}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Оглушающий удар"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.weapon.piercing_crit",
        technical=TriggerTechnicalDTO(
            trigger_id="weapon_piercing_crit",
            event="ON_CRIT",
            chance=1.0,
            pipeline_mutations=[pipeline_mutation("ignore_flat_armor")],
            allowed_sources=["weapon"],
            display_policy="merge",
            tags=["weapon", "piercing", "crit", "armor_bypass"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="weapon_piercing_crit",
            display_name="Пронзающий крит",
            short_description="Критический укол проходит через броню.",
            humanoid_event_texts=CombatEventTextSetDTO(
                crit_proc=["{source} находит щель в защите {target}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Пронзающий крит"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.weapon.flat_armor_gap_crit",
        technical=TriggerTechnicalDTO(
            trigger_id="weapon_flat_armor_gap_crit",
            event="ON_CRIT",
            chance=1.0,
            pipeline_mutations=[
                pipeline_mutation("roll_flat_armor_ignore"),
                pipeline_mutation("flat_armor_ignore_chance_bonus", 0.5),
            ],
            allowed_sources=["weapon"],
            display_policy="merge",
            tags=["weapon", "piercing", "crit", "armor_gap"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="weapon_flat_armor_gap_crit",
            display_name="Щель в броне",
            short_description="Критический укол получает шанс пройти мимо плоской брони.",
            humanoid_event_texts=CombatEventTextSetDTO(
                crit_proc=["{source} ищет щель в броне {target}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Щель в броне"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.weapon.flat_armor_bypass_crit",
        technical=TriggerTechnicalDTO(
            trigger_id="weapon_flat_armor_bypass_crit",
            event="ON_CRIT",
            chance=1.0,
            pipeline_mutations=[pipeline_mutation("ignore_flat_armor")],
            allowed_sources=["weapon"],
            display_policy="merge",
            tags=["weapon", "piercing", "crit", "armor_bypass"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="weapon_flat_armor_bypass_crit",
            display_name="Обход брони",
            short_description="Критический укол полностью обходит плоскую броню.",
            humanoid_event_texts=CombatEventTextSetDTO(
                crit_proc=["{source} проводит укол мимо брони {target}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Обход брони"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.weapon.flat_armor_crush_crit",
        technical=TriggerTechnicalDTO(
            trigger_id="weapon_flat_armor_crush_crit",
            event="ON_CRIT",
            chance=1.0,
            pipeline_mutations=[
                pipeline_mutation("boost_flat_armor_penetration"),
                pipeline_mutation("flat_armor_penetration_bonus_pct", 0.5),
            ],
            allowed_sources=["weapon"],
            display_policy="merge",
            tags=["weapon", "heavy", "crit", "armor_crush"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="weapon_flat_armor_crush_crit",
            display_name="Смятие брони",
            short_description="Критический тяжелый удар сильнее подавляет плоскую броню.",
            humanoid_event_texts=CombatEventTextSetDTO(
                crit_proc=["{source} сминает защиту {target} тяжелым ударом."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Смятие брони"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.weapon.precision_crit",
        technical=TriggerTechnicalDTO(
            trigger_id="weapon_precision_crit",
            event="ON_CRIT",
            chance=1.0,
            pipeline_mutations=[pipeline_mutation("ignore_evasion")],
            allowed_sources=["weapon"],
            display_policy="merge",
            tags=["weapon", "precision", "crit", "anti_evasion"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="weapon_precision_crit",
            display_name="Точный крит",
            short_description="Критический удар точного оружия не дает цели уйти движением.",
            humanoid_event_texts=CombatEventTextSetDTO(
                crit_proc=["{source} ловит движение {target} точным критическим ударом."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Точный крит"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.weapon.shieldbreaker_crit",
        technical=TriggerTechnicalDTO(
            trigger_id="weapon_shieldbreaker_crit",
            event="ON_CRIT",
            chance=1.0,
            pipeline_mutations=[pipeline_mutation("ignore_block")],
            allowed_sources=["weapon"],
            display_policy="merge",
            tags=["weapon", "shieldbreaker", "crit", "ignore_block"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="weapon_shieldbreaker_crit",
            display_name="Слом блока",
            short_description="Критический удар обходит блок щитом.",
            humanoid_event_texts=CombatEventTextSetDTO(
                crit_proc=["{source} обводит защиту {target} цепным ударом."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Слом блока"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.weapon.knockdown_hit",
        technical=TriggerTechnicalDTO(
            trigger_id="weapon_knockdown_hit",
            event="ON_CHECK_CONTROL",
            chance=1.0,
            applied_effect_ids=["knockdown", "force_ranged_close"],
            allowed_sources=["weapon"],
            display_policy="merge",
            tags=["weapon", "control", "hit", "knockdown", "anti_archer"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="weapon_knockdown_hit",
            display_name="Срыв опоры",
            short_description="Попадание цепляет движение цели и сбивает ее с ног.",
            humanoid_event_texts=CombatEventTextSetDTO(
                hit_proc=["{source} цепляет опору {target}."],
                apply_effect=["{target} получает {effect}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Срыв опоры"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.weapon.evasive_shot",
        technical=TriggerTechnicalDTO(
            trigger_id="weapon_evasive_shot",
            event="ON_CHECK_CONTROL",
            chance=1.0,
            applied_effect_ids=["marker_evasion"],
            allowed_sources=["weapon"],
            display_policy="merge",
            tags=["weapon", "ranged", "hit", "evasion"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="weapon_evasive_shot",
            display_name="Маневренный выстрел",
            short_description="Попадание из легкого лука дает позиционное преимущество.",
            humanoid_event_texts=CombatEventTextSetDTO(
                hit_proc=["{source} поражает {target} и смещается в выгодную позицию."],
                apply_effect=["{source} накладывает {effect} на {target}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Маневренный выстрел"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.weapon.riposte_on_parry",
        technical=TriggerTechnicalDTO(
            trigger_id="weapon_riposte_on_parry",
            event="ON_PARRY",
            chance=1.0,
            pipeline_mutations=[
                pipeline_mutation("allow_counter_on_parry"),
                pipeline_mutation("state.check_counter"),
            ],
            allowed_sources=["weapon"],
            display_policy="separate",
            tags=["weapon", "parry", "riposte", "counter"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="weapon_riposte_on_parry",
            display_name="Рипост",
            short_description="Парирующее оружие открывает контратаку после успешного парирования.",
            humanoid_event_texts=CombatEventTextSetDTO(
                parry_proc=["{target} парирует и сразу ищет ответную линию."],
                counter=["{target} контратакует {source} после парирования."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Рипост"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.weapon.shield_bash_on_block",
        technical=TriggerTechnicalDTO(
            trigger_id="weapon_shield_bash_on_block",
            event="ON_BLOCK",
            chance=1.0,
            pipeline_mutations=[pipeline_mutation("chain.trigger_extra_strike")],
            allowed_sources=["weapon"],
            display_policy="separate",
            tags=["weapon", "shield", "block", "extra_strike"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="weapon_shield_bash_on_block",
            display_name="Ответ щитом",
            short_description="Успешный блок открывает ответный удар щитом.",
            humanoid_event_texts=CombatEventTextSetDTO(
                block_proc=["{target} принимает удар щитом и отвечает корпусом."],
                extra_strike=["{target} добавляет удар щитом."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Ответ щитом"),
        ),
    ),
]

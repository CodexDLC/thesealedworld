from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.modifier_applications import ModifierApplicationDTO
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import pipeline_mutation
from src.backend.features.game_catalog.combat.resources.effects.schemas import (
    ControlInstructionDTO,
    EffectCatalogEntryDTO,
    EffectTechnicalDTO,
    EffectType,
)

_BUFF_APPLY_BEAST = CombatEventTextSetDTO(
    apply_effect=["{target} получает {effect}."],
    expire_effect=["{effect} {target} иссякает."],
)


def _buff_catalog(
    effect_id: str,
    display_name: str,
    short_description: str,
    modifier_id: str,
    value: float,
    tags: list[str],
    apply_humanoid: list[str],
    expire_humanoid: list[str],
) -> EffectCatalogEntryDTO:
    return EffectCatalogEntryDTO(
        key=f"combat.effect.{effect_id}",
        technical=EffectTechnicalDTO(
            effect_id=effect_id,
            type=EffectType.BUFF,
            duration=3,
            modifier_applications=[
                ModifierApplicationDTO(
                    modifier_id=modifier_id,
                    value_override=value,
                    scope="duration",
                    duration_exchanges=3,
                )
            ],
            tags=tags,
        ),
        descriptive=build_combat_description(
            resource_type="effects",
            resource_id=effect_id,
            icon=f"combat/effects/{effect_id}.svg",
            display_name=display_name,
            short_description=short_description,
            humanoid_event_texts=CombatEventTextSetDTO(
                apply_effect=apply_humanoid,
                expire_effect=expire_humanoid,
                resist=["{target} не нуждается в {effect} — эффект отклонён."],
                cleanse=["{effect} на {target} снят досрочно."],
            ),
            beast_event_texts=_BUFF_APPLY_BEAST,
        ),
    )


_buff_str_catalog = _buff_catalog(
    effect_id="buff_str",
    display_name="Усиление Силы",
    short_description="Увеличивает Силу.",
    modifier_id="strength_add",
    value=1.0,
    tags=["buff", "attribute", "physical"],
    apply_humanoid=["{source} усиливает мощь {target}.", "{target} получает {effect} — сила растёт."],
    expire_humanoid=["Усиление Силы {target} иссякает.", "{target} теряет {effect}."],
)

_buff_dex_catalog = _buff_catalog(
    effect_id="buff_dex",
    display_name="Усиление Ловкости",
    short_description="Увеличивает Ловкость.",
    modifier_id="dexterity_add",
    value=1.0,
    tags=["buff", "attribute", "physical"],
    apply_humanoid=["{source} обостряет реакцию {target}.", "{target} получает {effect}."],
    expire_humanoid=["Усиление Ловкости {target} иссякает.", "{target} теряет {effect}."],
)

_buff_int_catalog = _buff_catalog(
    effect_id="buff_int",
    display_name="Усиление Интеллекта",
    short_description="Увеличивает Интеллект.",
    modifier_id="intelligence_add",
    value=1.0,
    tags=["buff", "attribute", "magical"],
    apply_humanoid=["{source} проясняет разум {target}.", "{target} получает {effect}."],
    expire_humanoid=["Усиление Интеллекта {target} рассеивается.", "{target} теряет {effect}."],
)

_buff_end_catalog = _buff_catalog(
    effect_id="buff_end",
    display_name="Усиление Выносливости",
    short_description="Увеличивает Выносливость.",
    modifier_id="endurance_add",
    value=1.0,
    tags=["buff", "attribute", "physical"],
    apply_humanoid=["{source} укрепляет стойкость {target}.", "{target} получает {effect}."],
    expire_humanoid=["Усиление Выносливости {target} иссякает.", "{target} теряет {effect}."],
)

_buff_armor_catalog = _buff_catalog(
    effect_id="buff_armor",
    display_name="Усиление Брони",
    short_description="Увеличивает Броню.",
    modifier_id="armor_add",
    value=1.0,
    tags=["buff", "defense", "physical"],
    apply_humanoid=["{source} усиливает броню {target}.", "{target} получает {effect} — броня укреплена."],
    expire_humanoid=["Усиление брони {target} иссякает.", "{target} теряет {effect}."],
)

_buff_evasion_catalog = _buff_catalog(
    effect_id="buff_evasion",
    display_name="Усиление Уклонения",
    short_description="Увеличивает шанс уклонения.",
    modifier_id="evasion_add",
    value=0.01,
    tags=["buff", "defense", "air"],
    apply_humanoid=["{source} повышает уклонение {target}.", "{target} получает {effect}."],
    expire_humanoid=["Усиление Уклонения {target} иссякает.", "{target} теряет {effect}."],
)

_buff_accuracy_catalog = _buff_catalog(
    effect_id="buff_accuracy",
    display_name="Усиление Точности",
    short_description="Увеличивает точность.",
    modifier_id="accuracy_add",
    value=0.01,
    tags=["buff", "offense"],
    apply_humanoid=["{source} направляет руку {target}.", "{target} получает {effect} — точность растёт."],
    expire_humanoid=["Усиление Точности {target} иссякает.", "{target} теряет {effect}."],
)

_buff_crit_catalog = _buff_catalog(
    effect_id="buff_crit",
    display_name="Усиление Крита",
    short_description="Увеличивает шанс крита.",
    modifier_id="crit_chance_add",
    value=0.01,
    tags=["buff", "offense"],
    apply_humanoid=["{source} обостряет инстинкт {target}.", "{target} получает {effect}."],
    expire_humanoid=["Усиление Крита {target} иссякает.", "{target} теряет {effect}."],
)

_buff_phys_dmg_catalog = _buff_catalog(
    effect_id="buff_phys_dmg",
    display_name="Усиление Физ. Урона",
    short_description="Увеличивает физический урон.",
    modifier_id="physical_damage_bonus_add",
    value=1.0,
    tags=["buff", "offense", "physical"],
    apply_humanoid=["{source} усиливает удары {target}.", "{target} получает {effect} — урон растёт."],
    expire_humanoid=["Усиление Урона {target} иссякает.", "{target} теряет {effect}."],
)

_prep_counter_on_dodge_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_counter_on_dodge",
    technical=EffectTechnicalDTO(
        effect_id="prep_counter_on_dodge",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[
            pipeline_mutation("force_counter_on_dodge"),
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["dodge"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "tempo", "dodge", "counter"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_counter_on_dodge",
        icon="combat/effects/prep_counter_on_dodge.svg",
        display_name="Ответный шаг",
        short_description="Следующий успешный уворот вызывает контратаку.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} сохраняет темп для ответа на следующий уворот."],
            expire_effect=["{target} тратит подготовленный ответный шаг."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)

_prep_counter_on_parry_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_counter_on_parry",
    technical=EffectTechnicalDTO(
        effect_id="prep_counter_on_parry",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[
            pipeline_mutation("force_counter_on_parry"),
            pipeline_mutation("allow_counter_on_parry"),
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["parry"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "tempo", "parry", "counter"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_counter_on_parry",
        icon="combat/effects/prep_counter_on_parry.svg",
        display_name="Ответное парирование",
        short_description="Следующее успешное парирование вызывает контратаку.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} удерживает оружие для встречного парирования."],
            expire_effect=["{target} переводит подготовленное парирование в ответ."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)

_prep_foresight_parry_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_foresight_parry",
    technical=EffectTechnicalDTO(
        effect_id="prep_foresight_parry",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[
            pipeline_mutation("force.parry"),
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["parry"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "parry", "forced_parry"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_foresight_parry",
        icon="combat/effects/prep_foresight_parry.svg",
        display_name="Предвидение",
        short_description="Следующий входящий удар будет парирован.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} читает линию следующей атаки."],
            expire_effect=["{target} переводит предвидение в парирование."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)

_prep_second_breath_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_second_breath",
    technical=EffectTechnicalDTO(
        effect_id="prep_second_breath",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutation_role="target",
        react_on_outcomes=["parry"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "parry", "heal"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_second_breath",
        icon="combat/effects/prep_second_breath.svg",
        display_name="Второе дыхание",
        short_description="Следующее успешное парирование восстанавливает HP.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} выравнивает дыхание перед встречной защитой."],
            expire_effect=["{target} восстанавливается на успешном парировании."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)

_prep_perfect_riposte_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_perfect_riposte",
    technical=EffectTechnicalDTO(
        effect_id="prep_perfect_riposte",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[
            pipeline_mutation("force_counter_on_parry"),
            pipeline_mutation("allow_counter_on_parry"),
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["parry"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "parry", "heal", "counter"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_perfect_riposte",
        icon="combat/effects/prep_perfect_riposte.svg",
        display_name="Совершенный рипост",
        short_description="Следующее успешное парирование восстанавливает HP и вызывает контратаку.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} удерживает линию для совершенного рипоста."],
            expire_effect=["{target} переводит парирование в восстановление и ответ."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)

_prep_glancing_dodge_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_glancing_dodge",
    technical=EffectTechnicalDTO(
        effect_id="prep_glancing_dodge",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[
            pipeline_mutation("damage_mult", 0.5),
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["hit", "crit", "block"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "dodge", "damage_reduction"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_glancing_dodge",
        icon="combat/effects/prep_glancing_dodge.svg",
        display_name="Скользящий отход",
        short_description="Следующий входящий удар наносит половину урона.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} оставляет корпус в скользящей позиции."],
            expire_effect=["{target} принимает удар вскользь."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)

_prep_counter_cap_on_dodge_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_counter_cap_on_dodge",
    technical=EffectTechnicalDTO(
        effect_id="prep_counter_cap_on_dodge",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[
            pipeline_mutation("counter_to_cap_on_dodge"),
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["dodge"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "dodge", "counter_cap"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_counter_cap_on_dodge",
        icon="combat/effects/prep_counter_cap_on_dodge.svg",
        display_name="Окно ответа",
        short_description="Следующий успешный уворот проверяет контратаку по капу.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} ищет окно для ответа на следующем увороте."],
            expire_effect=["{target} тратит найденное окно для ответа."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)

_prep_brace_guard_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_brace_guard",
    technical=EffectTechnicalDTO(
        effect_id="prep_brace_guard",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[
            pipeline_mutation("damage_mult", 0.75),
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["hit", "crit", "block"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "block", "damage_reduction"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_brace_guard",
        icon="combat/effects/prep_brace_guard.svg",
        display_name="Глухая защита",
        short_description="Следующий входящий удар наносит меньше урона.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} собирает стойку в глухую защиту."],
            expire_effect=["{target} принимает удар на подготовленную защиту."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)


_prep_active_defense_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_active_defense",
    technical=EffectTechnicalDTO(
        effect_id="prep_active_defense",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[
            pipeline_mutation("force.block"),
            pipeline_mutation("force_shield_defense_branch"),
            pipeline_mutation("shield_guard_power_mult", 1.25),
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["hit", "crit", "block"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "block", "shield", "damage_reduction"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_active_defense",
        icon="combat/effects/prep_active_defense.svg",
        display_name="Активная защита",
        short_description="Следующий входящий удар принудительно принимается защитной веткой щита.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} поднимает щит в активную защиту."],
            expire_effect=["{target} гасит удар активной защитой."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)


_prep_full_defense_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_full_defense",
    technical=EffectTechnicalDTO(
        effect_id="prep_full_defense",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[
            pipeline_mutation("force.block"),
            pipeline_mutation("force_shield_defense_branch"),
            pipeline_mutation("shield_guard_power_mult", 2.5),
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["hit", "crit", "block"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "block", "shield", "damage_cap"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_full_defense",
        icon="combat/effects/prep_full_defense.svg",
        display_name="Полная защита",
        short_description="Следующий входящий удар принудительно уходит в усиленную защитную ветку щита.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} закрывается полной защитой."],
            expire_effect=["{target} сводит удар к минимуму полной защитой."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)


_prep_absolute_defense_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_absolute_defense",
    technical=EffectTechnicalDTO(
        effect_id="prep_absolute_defense",
        type=EffectType.BUFF,
        duration=1,
        pipeline_mutations=[
            pipeline_mutation("force.block"),
            pipeline_mutation("force_shield_defense_branch"),
            pipeline_mutation("shield_guard_power_mult", 2.5),
            pipeline_mutation("incoming_damage_cap", 1),
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["hit", "crit", "block"],
        consume_on_reaction=False,
        tags=["buff", "preparation", "block", "shield", "damage_cap", "absolute_defense"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_absolute_defense",
        icon="combat/effects/prep_absolute_defense.svg",
        display_name="Абсолютная защита",
        short_description="До следующего размена входящий урон через resolver становится не больше 1.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} собирает абсолютную защиту."],
            tick=["Абсолютная защита {target} сводит удар к минимуму."],
            expire_effect=["Абсолютная защита {target} рассеивается."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)


_prep_aggressive_defense_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_aggressive_defense",
    technical=EffectTechnicalDTO(
        effect_id="prep_aggressive_defense",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[
            pipeline_mutation("force.block"),
            pipeline_mutation("force_shield_counter_branch"),
            pipeline_mutation("shield_counter_from_absorbed"),
            pipeline_mutation("shield_counter_power_mult", 1.5),
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["hit", "crit", "block"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "block", "shield", "damage_cap", "reflect"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_aggressive_defense",
        icon="combat/effects/prep_aggressive_defense.svg",
        display_name="Агрессивная защита",
        short_description="Следующий входящий удар принудительно уходит в контр-ветку щита.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} поднимает щит в агрессивную защиту."],
            expire_effect=["{target} встречает удар агрессивной защитой."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)


_concussed_no_feints_catalog = EffectCatalogEntryDTO(
    key="combat.effect.concussed_no_feints",
    technical=EffectTechnicalDTO(
        effect_id="concussed_no_feints",
        type=EffectType.CONTROL,
        duration=1,
        control_logic=ControlInstructionDTO(
            status_name="forbid_feints",
            source_behavior={"forbid_feints": True},
        ),
        tags=["control", "shield", "forbid_feints"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="concussed_no_feints",
        icon="combat/effects/concussed_no_feints.svg",
        display_name="Контузия",
        short_description="Следующий размен нельзя использовать финты.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} теряет возможность использовать приемы в следующем размене."],
            expire_effect=["{target} приходит в себя после контузии."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)


_prep_parry_riposte_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_parry_riposte",
    technical=EffectTechnicalDTO(
        effect_id="prep_parry_riposte",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[
            pipeline_mutation("allow_counter_on_parry"),
            pipeline_mutation("counter_chance_boost"),
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["parry"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "parry", "counter"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_parry_riposte",
        icon="combat/effects/prep_parry_riposte.svg",
        display_name="Готовый рипост",
        short_description="Следующее успешное парирование получает повышенный шанс контратаки.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} удерживает оружие для рипоста."],
            expire_effect=["{target} тратит подготовленный рипост."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)

_spiked_guard_catalog = EffectCatalogEntryDTO(
    key="combat.effect.spiked_guard",
    technical=EffectTechnicalDTO(
        effect_id="spiked_guard",
        type=EffectType.BUFF,
        duration=5,
        react_on_outcomes=["block"],
        consume_on_reaction=False,
        tags=["buff", "preparation", "tempo", "block", "shield", "reflect"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="spiked_guard",
        icon="combat/effects/spiked_guard.svg",
        display_name="Шипастая стойка",
        short_description="Пять разменов: успешный блок щитом отражает часть удара.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} собирает защиту в жесткую шипастую стойку."],
            tick=["Шипастая стойка {target} отвечает на удар."],
            expire_effect=["Шипастая стойка {target} рассеивается."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)

_prep_2h_steel_line_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_2h_steel_line",
    technical=EffectTechnicalDTO(
        effect_id="prep_2h_steel_line",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[pipeline_mutation("force.parry")],
        pipeline_mutation_role="target",
        react_on_outcomes=["parry"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "two_handed", "parry", "forced_parry"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_2h_steel_line",
        icon="combat/effects/prep_2h_steel_line.svg",
        display_name="Стальная линия",
        short_description="Следующая атака по вам будет парирована.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} ставит оружие в стальную линию."],
            expire_effect=["{target} переводит стальную линию в парирование."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)

_prep_2h_blade_return_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_2h_blade_return",
    technical=EffectTechnicalDTO(
        effect_id="prep_2h_blade_return",
        type=EffectType.BUFF,
        duration=999,
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="parry_mult",
                value_override=1.3,
                scope="duration",
                duration_exchanges=999,
            )
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["hit", "crit", "miss", "dodge", "parry", "block"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "two_handed", "parry", "parry_boost"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_2h_blade_return",
        icon="combat/effects/prep_2h_blade_return.svg",
        display_name="Возврат клинка",
        short_description="Следующая входящая атака проходит против усиленного парирования.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} возвращает клинок в защитную линию."],
            expire_effect=["{target} тратит возврат клинка."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)

_prep_2h_hard_intercept_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_2h_hard_intercept",
    technical=EffectTechnicalDTO(
        effect_id="prep_2h_hard_intercept",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[pipeline_mutation("force.parry")],
        pipeline_mutation_role="target",
        react_on_outcomes=["parry"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "two_handed", "parry", "debuff"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_2h_hard_intercept",
        icon="combat/effects/prep_2h_hard_intercept.svg",
        display_name="Жесткий перехват",
        short_description="Следующая атака парируется и сбивает размах противника.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} готовит жесткий перехват."],
            expire_effect=["{target} сбивает атаку жестким перехватом."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)

_prep_2h_answering_stance_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_2h_answering_stance",
    technical=EffectTechnicalDTO(
        effect_id="prep_2h_answering_stance",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[
            pipeline_mutation("force.parry"),
            pipeline_mutation("force_counter_on_parry"),
            pipeline_mutation("allow_counter_on_parry"),
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["parry"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "two_handed", "parry", "counter"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_2h_answering_stance",
        icon="combat/effects/prep_2h_answering_stance.svg",
        display_name="Ответная стойка",
        short_description="Следующая атака парируется и вызывает контратаку.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} закрывает линию в ответную стойку."],
            expire_effect=["{target} переводит парирование в ответную стойку."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)

_prep_2h_closed_distance_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_2h_closed_distance",
    technical=EffectTechnicalDTO(
        effect_id="prep_2h_closed_distance",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[
            pipeline_mutation("force.parry"),
            pipeline_mutation("force_counter_on_parry"),
            pipeline_mutation("allow_counter_on_parry"),
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["parry"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "two_handed", "parry", "counter", "high_cost"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_2h_closed_distance",
        icon="combat/effects/prep_2h_closed_distance.svg",
        display_name="Закрытая дистанция",
        short_description="Следующая атака парируется и вызывает жесткую контратаку.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} закрывает дистанцию для встречного ответа."],
            expire_effect=["{target} парирует и рвет дистанцию ответом."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)

_prep_2h_hidden_agility_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_2h_hidden_agility",
    technical=EffectTechnicalDTO(
        effect_id="prep_2h_hidden_agility",
        type=EffectType.BUFF,
        duration=999,
        pipeline_mutations=[
            pipeline_mutation("force.dodge"),
            pipeline_mutation("force_counter_on_dodge"),
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["dodge"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "two_handed", "dodge", "counter"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_2h_hidden_agility",
        icon="combat/effects/prep_2h_hidden_agility.svg",
        display_name="Скрытая ловкость",
        short_description="Следующая атака уходит в уворот и вызывает контратаку.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} скрывает движение за весом оружия."],
            expire_effect=["{target} уходит с линии и отвечает."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)


def _dual_prep_catalog(
    *,
    effect_id: str,
    display_name: str,
    short_description: str,
    pipeline_mutations: list | None = None,
    pipeline_mutation_role: str = "target",
    react_on_outcomes: list[str] | None = None,
    tags: list[str] | None = None,
) -> EffectCatalogEntryDTO:
    return EffectCatalogEntryDTO(
        key=f"combat.effect.{effect_id}",
        technical=EffectTechnicalDTO(
            effect_id=effect_id,
            type=EffectType.BUFF,
            duration=999,
            pipeline_mutations=pipeline_mutations or [],
            pipeline_mutation_role=pipeline_mutation_role,
            react_on_outcomes=react_on_outcomes or ["hit", "crit", "miss", "dodge", "parry", "block"],
            consume_on_reaction=True,
            tags=["buff", "preparation", "dual_wield", *(tags or [])],
        ),
        descriptive=build_combat_description(
            resource_type="effects",
            resource_id=effect_id,
            icon=f"combat/effects/{effect_id}.svg",
            display_name=display_name,
            short_description=short_description,
            humanoid_event_texts=CombatEventTextSetDTO(
                apply_effect=[f"{{target}} готовит {display_name.lower()}."],
                expire_effect=[f"{{target}} тратит {display_name.lower()}."],
            ),
            beast_event_texts=_BUFF_APPLY_BEAST,
        ),
    )


_prep_dual_broken_step_catalog = _dual_prep_catalog(
    effect_id="prep_dual_broken_step",
    display_name="Ломаный шаг",
    short_description="Следующий успешный уворот получает повышенный шанс контратаки.",
    pipeline_mutations=[pipeline_mutation("counter_chance_bonus_on_dodge")],
    react_on_outcomes=["dodge"],
    tags=["dodge", "counter"],
)

_prep_dual_shifting_line_catalog = EffectCatalogEntryDTO(
    key="combat.effect.prep_dual_shifting_line",
    technical=EffectTechnicalDTO(
        effect_id="prep_dual_shifting_line",
        type=EffectType.BUFF,
        duration=999,
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="parry_mult",
                value_override=1.25,
                scope="duration",
                duration_exchanges=999,
            )
        ],
        pipeline_mutation_role="target",
        react_on_outcomes=["hit", "crit", "miss", "dodge", "parry", "block"],
        consume_on_reaction=True,
        tags=["buff", "preparation", "dual_wield", "dodge", "parry_boost"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="prep_dual_shifting_line",
        icon="combat/effects/prep_dual_shifting_line.svg",
        display_name="Смена линии",
        short_description="Следующая входящая атака проходит против усиленного парирования.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} смещает линию второй рукой."],
            expire_effect=["{target} тратит смену линии."],
        ),
        beast_event_texts=_BUFF_APPLY_BEAST,
    ),
)

_prep_dual_empty_line_catalog = _dual_prep_catalog(
    effect_id="prep_dual_empty_line",
    display_name="Пустая линия",
    short_description="Следующий входящий удар наносит половину урона.",
    pipeline_mutations=[pipeline_mutation("damage_mult", 0.5)],
    react_on_outcomes=["hit", "crit"],
    tags=["dodge", "damage_reduction"],
)

_prep_dual_torn_rhythm_catalog = _dual_prep_catalog(
    effect_id="prep_dual_torn_rhythm",
    display_name="Рваный ритм",
    short_description="Следующий успешный уворот проверяет контратаку от капа.",
    pipeline_mutations=[pipeline_mutation("counter_to_cap_on_dodge")],
    react_on_outcomes=["dodge"],
    tags=["dodge", "counter_cap"],
)

_prep_dual_bind_blade_catalog = _dual_prep_catalog(
    effect_id="prep_dual_bind_blade",
    display_name="Связать клинок",
    short_description="Следующее успешное парирование снижает следующий исходящий урон атакующего.",
    react_on_outcomes=["parry"],
    tags=["parry", "debuff"],
)

_prep_dual_offhand_over_catalog = _dual_prep_catalog(
    effect_id="prep_dual_offhand_over",
    display_name="Вторая рука сверху",
    short_description="Следующее успешное парирование открывает контратаку и повышает ее шанс.",
    pipeline_mutations=[
        pipeline_mutation("allow_counter_on_parry"),
        pipeline_mutation("counter_chance_bonus_on_parry"),
    ],
    react_on_outcomes=["parry"],
    tags=["parry", "counter"],
)

_prep_dual_answering_series_counter_catalog = _dual_prep_catalog(
    effect_id="prep_dual_answering_series_counter",
    display_name="Ответная серия",
    short_description="Следующая успешная контратака наносит больше урона.",
    pipeline_mutations=[pipeline_mutation("damage_mult", 1.25)],
    pipeline_mutation_role="source",
    react_on_outcomes=["hit", "crit"],
    tags=["counter", "counter_only", "damage"],
)

_prep_dual_blade_mill_counter_catalog = _dual_prep_catalog(
    effect_id="prep_dual_blade_mill_counter",
    display_name="Мельница двух рук",
    short_description="Следующая успешная контратака наносит больше урона и запускает штатный offhand.",
    pipeline_mutations=[pipeline_mutation("damage_mult", 1.5)],
    pipeline_mutation_role="source",
    react_on_outcomes=["hit", "crit"],
    tags=["counter", "counter_only", "damage", "offhand"],
)

_prep_dual_blade_loop_parry_catalog = _dual_prep_catalog(
    effect_id="prep_dual_blade_loop_parry",
    display_name="Петля клинков",
    short_description="Следующее успешное парирование вызывает усиленную контратаку.",
    pipeline_mutations=[
        pipeline_mutation("force_counter_on_parry"),
        pipeline_mutation("allow_counter_on_parry"),
    ],
    react_on_outcomes=["parry"],
    tags=["parry", "counter", "high_cost"],
)

_prep_dual_blade_loop_counter_catalog = _dual_prep_catalog(
    effect_id="prep_dual_blade_loop_counter",
    display_name="Петля клинков: ответ",
    short_description="Контратака Петли наносит больше урона и снижает следующий исходящий урон цели.",
    pipeline_mutations=[pipeline_mutation("damage_mult", 1.5)],
    pipeline_mutation_role="source",
    react_on_outcomes=["hit", "crit"],
    tags=["counter", "counter_only", "damage", "debuff", "high_cost"],
)

# ── REGISTRY ──────────────────────────────────────────────────────────────────

BUFF_EFFECTS_CATALOG: dict[str, EffectCatalogEntryDTO] = {
    "buff_str": _buff_str_catalog,
    "buff_dex": _buff_dex_catalog,
    "buff_int": _buff_int_catalog,
    "buff_end": _buff_end_catalog,
    "buff_armor": _buff_armor_catalog,
    "buff_evasion": _buff_evasion_catalog,
    "buff_accuracy": _buff_accuracy_catalog,
    "buff_crit": _buff_crit_catalog,
    "buff_phys_dmg": _buff_phys_dmg_catalog,
    "prep_counter_on_dodge": _prep_counter_on_dodge_catalog,
    "prep_counter_on_parry": _prep_counter_on_parry_catalog,
    "prep_foresight_parry": _prep_foresight_parry_catalog,
    "prep_second_breath": _prep_second_breath_catalog,
    "prep_perfect_riposte": _prep_perfect_riposte_catalog,
    "prep_glancing_dodge": _prep_glancing_dodge_catalog,
    "prep_counter_cap_on_dodge": _prep_counter_cap_on_dodge_catalog,
    "prep_brace_guard": _prep_brace_guard_catalog,
    "prep_active_defense": _prep_active_defense_catalog,
    "prep_full_defense": _prep_full_defense_catalog,
    "prep_absolute_defense": _prep_absolute_defense_catalog,
    "prep_aggressive_defense": _prep_aggressive_defense_catalog,
    "concussed_no_feints": _concussed_no_feints_catalog,
    "prep_parry_riposte": _prep_parry_riposte_catalog,
    "spiked_guard": _spiked_guard_catalog,
    "prep_2h_steel_line": _prep_2h_steel_line_catalog,
    "prep_2h_blade_return": _prep_2h_blade_return_catalog,
    "prep_2h_hard_intercept": _prep_2h_hard_intercept_catalog,
    "prep_2h_answering_stance": _prep_2h_answering_stance_catalog,
    "prep_2h_closed_distance": _prep_2h_closed_distance_catalog,
    "prep_2h_hidden_agility": _prep_2h_hidden_agility_catalog,
    "prep_dual_broken_step": _prep_dual_broken_step_catalog,
    "prep_dual_shifting_line": _prep_dual_shifting_line_catalog,
    "prep_dual_empty_line": _prep_dual_empty_line_catalog,
    "prep_dual_torn_rhythm": _prep_dual_torn_rhythm_catalog,
    "prep_dual_bind_blade": _prep_dual_bind_blade_catalog,
    "prep_dual_offhand_over": _prep_dual_offhand_over_catalog,
    "prep_dual_answering_series_counter": _prep_dual_answering_series_counter_catalog,
    "prep_dual_blade_mill_counter": _prep_dual_blade_mill_counter_catalog,
    "prep_dual_blade_loop_parry": _prep_dual_blade_loop_parry_catalog,
    "prep_dual_blade_loop_counter": _prep_dual_blade_loop_counter_catalog,
}

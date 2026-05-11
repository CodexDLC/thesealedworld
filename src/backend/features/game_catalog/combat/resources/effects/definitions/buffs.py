from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.modifier_applications import ModifierApplicationDTO
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import pipeline_mutation
from src.backend.features.game_catalog.combat.resources.effects.schemas import (
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
        react_on_outcomes=["hit", "crit"],
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
        react_on_outcomes=["hit", "crit"],
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
    "prep_glancing_dodge": _prep_glancing_dodge_catalog,
    "prep_counter_cap_on_dodge": _prep_counter_cap_on_dodge_catalog,
    "prep_brace_guard": _prep_brace_guard_catalog,
    "prep_parry_riposte": _prep_parry_riposte_catalog,
    "spiked_guard": _spiked_guard_catalog,
}

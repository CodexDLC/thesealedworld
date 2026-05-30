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

_DEBUFF_APPLY_BEAST = CombatEventTextSetDTO(
    apply_effect=["{target} получает {effect}."],
    expire_effect=["{effect} {target} спадает."],
)


def _debuff_catalog(
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
            type=EffectType.DEBUFF,
            duration=3,
            resistance_profile_id="generic_debuff",
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
                resist=["{target} держит защиту — {effect} не проходит."],
                cleanse=["{effect} на {target} снят."],
            ),
            beast_event_texts=_DEBUFF_APPLY_BEAST,
        ),
    )


_debuff_str_catalog = _debuff_catalog(
    effect_id="debuff_str",
    display_name="Ослабление Силы",
    short_description="Снижает Силу.",
    modifier_id="strength_add",
    value=-1.0,
    tags=["debuff", "attribute", "curse"],
    apply_humanoid=["{source} ослабляет мощь {target}.", "{target} получает {effect} — сила тает."],
    expire_humanoid=["Ослабление Силы {target} проходит.", "{target} избавляется от {effect}."],
)

_debuff_armor_catalog = _debuff_catalog(
    effect_id="debuff_armor",
    display_name="Ослабление Брони",
    short_description="Снижает Броню.",
    modifier_id="armor_add",
    value=-1.0,
    tags=["debuff", "defense", "physical"],
    apply_humanoid=["{source} пробивает защиту {target}.", "{target} получает {effect} — броня ослаблена."],
    expire_humanoid=["Броня {target} восстанавливается.", "{target} избавляется от {effect}."],
)

_debuff_evasion_catalog = _debuff_catalog(
    effect_id="debuff_evasion",
    display_name="Ослабление Уклонения",
    short_description="Снижает уклонение.",
    modifier_id="evasion_add",
    value=-0.01,
    tags=["debuff", "defense", "ice"],
    apply_humanoid=["{source} сковывает движения {target}.", "{target} получает {effect}."],
    expire_humanoid=["Ослабление Уклонения {target} спадает.", "{target} избавляется от {effect}."],
)

_debuff_accuracy_catalog = _debuff_catalog(
    effect_id="debuff_accuracy",
    display_name="Ослабление Точности",
    short_description="Снижает точность.",
    modifier_id="accuracy_add",
    value=-0.01,
    tags=["debuff", "offense", "physical"],
    apply_humanoid=["{source} сбивает прицел {target}.", "{target} получает {effect} — точность падает."],
    expire_humanoid=["Ослабление Точности {target} спадает.", "{target} избавляется от {effect}."],
)

_debuff_2h_damage_halved_catalog = EffectCatalogEntryDTO(
    key="combat.effect.debuff_2h_damage_halved",
    technical=EffectTechnicalDTO(
        effect_id="debuff_2h_damage_halved",
        type=EffectType.DEBUFF,
        duration=1,
        resistance_profile_id="generic_debuff",
        pipeline_mutations=[pipeline_mutation("damage_mult", 0.5)],
        pipeline_mutation_role="source",
        react_on_outcomes=["hit", "crit", "miss", "dodge", "parry", "block"],
        consume_on_reaction=True,
        tags=["debuff", "two_handed", "damage_reduction", "offense"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="debuff_2h_damage_halved",
        icon="combat/effects/debuff_2h_damage_halved.svg",
        display_name="Сбитый размах",
        short_description="Следующий исходящий урон уменьшен вдвое.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{source} сбивает размах {target}."],
            expire_effect=["{target} теряет сбитый размах."],
            resist=["{target} удерживает размах."],
            cleanse=["Сбитый размах {target} снят."],
        ),
        beast_event_texts=_DEBUFF_APPLY_BEAST,
    ),
)

_debuff_ranged_repositioning_catalog = EffectCatalogEntryDTO(
    key="combat.effect.debuff_ranged_repositioning",
    technical=EffectTechnicalDTO(
        effect_id="debuff_ranged_repositioning",
        type=EffectType.DEBUFF,
        duration=1,
        resistance_profile_id=None,
        pipeline_mutation_role="source",
        react_on_outcomes=["hit", "crit", "miss", "dodge", "parry", "block"],
        consume_on_reaction=True,
        tags=["debuff", "ranged_combat", "backstep", "damage_reduction", "offense"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="debuff_ranged_repositioning",
        icon="combat/effects/debuff_ranged_repositioning.svg",
        display_name="Смена позиции",
        short_description="После идеального отскока следующий исходящий урон снижен на один размен.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} сбивает темп сменой позиции."],
            expire_effect=["{target} восстанавливает линию огня."],
            cleanse=["Смена позиции {target} снята."],
        ),
        beast_event_texts=_DEBUFF_APPLY_BEAST,
    ),
)

# ── REGISTRY ──────────────────────────────────────────────────────────────────

DEBUFF_EFFECTS_CATALOG: dict[str, EffectCatalogEntryDTO] = {
    "debuff_str": _debuff_str_catalog,
    "debuff_armor": _debuff_armor_catalog,
    "debuff_evasion": _debuff_evasion_catalog,
    "debuff_accuracy": _debuff_accuracy_catalog,
    "debuff_2h_damage_halved": _debuff_2h_damage_halved_catalog,
    "debuff_ranged_repositioning": _debuff_ranged_repositioning_catalog,
}

from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.modifier_applications import ModifierApplicationDTO
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

# ── REGISTRY ──────────────────────────────────────────────────────────────────

DEBUFF_EFFECTS_CATALOG: dict[str, EffectCatalogEntryDTO] = {
    "debuff_str": _debuff_str_catalog,
    "debuff_armor": _debuff_armor_catalog,
    "debuff_evasion": _debuff_evasion_catalog,
    "debuff_accuracy": _debuff_accuracy_catalog,
}

from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.effects.schemas import (
    EffectCatalogEntryDTO,
    EffectTechnicalDTO,
    EffectType,
)

# ── POISON ──────────────────────────────────────────────────────────────────

_poison_catalog = EffectCatalogEntryDTO(
    key="combat.effect.dot_poison",
    technical=EffectTechnicalDTO(
        effect_id="dot_poison",
        type=EffectType.DOT,
        duration=3,
        resource_impact={"hp": -1},
        tags=["dot", "poison", "nature"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="dot_poison",
        icon="combat/effects/dot_poison.svg",
        display_name="Яд",
        short_description="Яд наносит урон каждый ход.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=[
                "{source} отравляет {target}.",
                "{target} получает {effect} — яд начинает действовать.",
            ],
            tick=[
                "Яд разъедает {target}: -{value} {resource}.",
                "{effect} жжёт изнутри: {target} теряет {value} {resource}.",
            ],
            expire_effect=[
                "Яд в крови {target} нейтрализован.",
                "{target} больше не под действием {effect}.",
            ],
            resist=["{target} сопротивляется яду — {effect} не приживается."],
            cleanse=["{effect} на {target} очищен противоядием."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} отравлен."],
            tick=["Яд действует на {target}: -{value} {resource}."],
            expire_effect=["Яд выходит из тела {target}."],
        ),
    ),
)

# ── BLEED ────────────────────────────────────────────────────────────────────

_bleed_catalog = EffectCatalogEntryDTO(
    key="combat.effect.dot_bleed",
    technical=EffectTechnicalDTO(
        effect_id="dot_bleed",
        type=EffectType.DOT,
        duration=3,
        resource_impact={"hp": -3},
        tags=["dot", "bleed", "physical"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="dot_bleed",
        icon="combat/effects/dot_bleed.svg",
        display_name="Кровотечение",
        short_description="Рана кровоточит.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=[
                "{source} наносит рану: {target} начинает кровоточить.",
                "{target} получает {effect} — рана открыта.",
            ],
            tick=[
                "{effect} терзает {target}: -{value} {resource}.",
                "Рана {target} не затянулась: -{value} {resource}.",
            ],
            expire_effect=[
                "Кровотечение на {target} останавливается.",
                "{target} больше не теряет кровь.",
            ],
            resist=["{target} сдерживает кровотечение — {effect} не закрепляется."],
            cleanse=["Кровотечение {target} очищено."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} получает рану и начинает кровоточить."],
            tick=["Рана {target} кровоточит: -{value} {resource}."],
            expire_effect=["Рана {target} затягивается."],
        ),
    ),
)

# ── BURN ─────────────────────────────────────────────────────────────────────

_burn_catalog = EffectCatalogEntryDTO(
    key="combat.effect.dot_burn",
    technical=EffectTechnicalDTO(
        effect_id="dot_burn",
        type=EffectType.DOT,
        duration=3,
        resource_impact={"hp": -1},
        tags=["dot", "burn", "fire"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="dot_burn",
        icon="combat/effects/dot_burn.svg",
        display_name="Ожог",
        short_description="Огонь обжигает плоть.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=[
                "{source} поджигает {target}.",
                "{target} охвачен {effect}.",
            ],
            tick=[
                "Огонь обжигает {target}: -{value} {resource}.",
                "{effect} пылает на {target}: -{value} {resource}.",
            ],
            expire_effect=[
                "Огонь на {target} гаснет.",
                "{target} вырывается из {effect}.",
            ],
            resist=["{target} выносит жар — {effect} не закрепляется."],
            cleanse=["Пламя {target} сбито — {effect} снят."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} охвачен огнём."],
            tick=["Огонь жжёт {target}: -{value} {resource}."],
            expire_effect=["Огонь на {target} затухает."],
        ),
    ),
)

# ── REGISTRY ──────────────────────────────────────────────────────────────────

DOT_EFFECTS_CATALOG: dict[str, EffectCatalogEntryDTO] = {
    "dot_poison": _poison_catalog,
    "dot_bleed": _bleed_catalog,
    "dot_burn": _burn_catalog,
}

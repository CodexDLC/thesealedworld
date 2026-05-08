from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.effects.schemas import (
    EffectCatalogEntryDTO,
    EffectTechnicalDTO,
    EffectType,
)

# ── REGEN HP ──────────────────────────────────────────────────────────────────

_regen_hp_catalog = EffectCatalogEntryDTO(
    key="combat.effect.hot_regen_hp",
    technical=EffectTechnicalDTO(
        effect_id="hot_regen_hp",
        type=EffectType.HOT,
        duration=3,
        resource_impact={"hp": 1},
        tags=["hot", "regen", "nature", "healing"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="hot_regen_hp",
        icon="combat/effects/hot_regen_hp.svg",
        display_name="Регенерация",
        short_description="Восстановление здоровья.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=[
                "{source} даёт {target} исцеляющий эффект.",
                "{target} получает {effect} — тело начинает восстанавливаться.",
            ],
            tick=[
                "Регенерация залечивает {target}: +{value} {resource}.",
                "{effect} работает: {target} восстанавливает {value} {resource}.",
            ],
            expire_effect=[
                "Регенерация {target} завершается.",
                "{target} больше не восстанавливается от {effect}.",
            ],
            cleanse=["{effect} на {target} прерван."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} получает {effect}."],
            tick=["{target} восстанавливает {value} {resource}."],
            expire_effect=["Регенерация {target} заканчивается."],
        ),
    ),
)

# ── REGEN EN ──────────────────────────────────────────────────────────────────

_regen_en_catalog = EffectCatalogEntryDTO(
    key="combat.effect.hot_regen_en",
    technical=EffectTechnicalDTO(
        effect_id="hot_regen_en",
        type=EffectType.HOT,
        duration=3,
        resource_impact={"en": 1},
        tags=["hot", "clarity", "arcane"],
    ),
    descriptive=build_combat_description(
        resource_type="effects",
        resource_id="hot_regen_en",
        icon="combat/effects/hot_regen_en.svg",
        display_name="Ясность",
        short_description="Восстановление энергии.",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=[
                "{source} дарует {target} ясность разума.",
                "{target} получает {effect} — энергия начинает восстанавливаться.",
            ],
            tick=[
                "Ясность восполняет {target}: +{value} {resource}.",
                "{effect} действует: {target} восстанавливает {value} {resource}.",
            ],
            expire_effect=[
                "Ясность {target} рассеивается.",
                "{target} больше не восстанавливает энергию от {effect}.",
            ],
            cleanse=["{effect} на {target} прерван."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            apply_effect=["{target} получает {effect}."],
            tick=["{target} восстанавливает {value} {resource}."],
            expire_effect=["{effect} {target} заканчивается."],
        ),
    ),
)

# ── REGISTRY ──────────────────────────────────────────────────────────────────

HOT_EFFECTS_CATALOG: dict[str, EffectCatalogEntryDTO] = {
    "hot_regen_hp": _regen_hp_catalog,
    "hot_regen_en": _regen_en_catalog,
}

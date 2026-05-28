from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatDescriptionDTO,
    CombatEventTextSetDTO,
    CombatTaxonomyDescriptionDTO,
)
from src.backend.features.game_catalog.combat.resources.effects.schemas import (
    ControlInstructionDTO,
    EffectCatalogEntryDTO,
    EffectTechnicalDTO,
    EffectType,
)


def _control_description(
    effect_id: str,
    display_name: str,
    short_description: str,
    tooltip: str,
    control_term: str,
    humanoid_event_texts: CombatEventTextSetDTO,
) -> CombatDescriptionDTO:
    icon = f"combat/effects/{effect_id}.svg"
    return CombatDescriptionDTO(
        variants={
            "humanoid": CombatTaxonomyDescriptionDTO(
                icon=icon,
                display_name=display_name,
                short_description=short_description,
                long_description=short_description,
                ui_label=display_name,
                tooltip=tooltip,
                event_texts=humanoid_event_texts,
                control_term=control_term,
            ),
            "beast": CombatTaxonomyDescriptionDTO(
                icon=icon,
                display_name=display_name,
                short_description=short_description,
                long_description=short_description,
                ui_label=display_name,
                tooltip=tooltip,
                event_texts=CombatEventTextSetDTO(
                    apply_effect=["{target} получает {effect}."],
                    control_prevent_action=["{target} не может действовать."],
                    expire_effect=["{effect} {target} проходит."],
                ),
            ),
        }
    )


# ── STUN ──────────────────────────────────────────────────────────────────────

_stun_catalog = EffectCatalogEntryDTO(
    key="combat.effect.stun",
    technical=EffectTechnicalDTO(
        effect_id="stun",
        type=EffectType.CONTROL,
        duration=1,
        resistance_profile_id="control_physical",
        control_logic=ControlInstructionDTO(
            status_name="is_stun",
            source_behavior={"can_act": False},
            target_behavior={"can_dodge": False, "force_hit": True},
        ),
        tags=["control", "stun", "physical"],
    ),
    descriptive=_control_description(
        effect_id="stun",
        display_name="Оглушение",
        short_description="Пропуск хода. Нельзя уклоняться.",
        tooltip="Оглушён: пропуск хода, нельзя уклоняться.",
        control_term="оглушение",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=[
                "{source} оглушает {target}.",
                "{target} получает {effect} — теряет способность действовать.",
            ],
            control_prevent_action=[
                "{target} оглушён и не может действовать в этот ход.",
                "Оглушение держит {target}: действие пропущено.",
            ],
            expire_effect=[
                "Оглушение {target} проходит.",
                "{target} приходит в себя после {effect}.",
            ],
            resist=["{target} выдерживает удар — {effect} не срабатывает."],
            cleanse=["Оглушение {target} снято."],
        ),
    ),
)

# ── SLEEP ─────────────────────────────────────────────────────────────────────

_sleep_catalog = EffectCatalogEntryDTO(
    key="combat.effect.sleep",
    technical=EffectTechnicalDTO(
        effect_id="sleep",
        type=EffectType.CONTROL,
        duration=3,
        resistance_profile_id="control_mental",
        control_logic=ControlInstructionDTO(
            status_name="is_sleep",
            source_behavior={"can_act": False},
            target_behavior={"can_dodge": False, "force_crit": True},
        ),
        tags=["control", "sleep", "mental"],
    ),
    descriptive=_control_description(
        effect_id="sleep",
        display_name="Сон",
        short_description="Спит. Любой урон будит (логика пробуждения в Resolver).",
        tooltip="Сон: цель не действует, удары — критические.",
        control_term="сон",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=[
                "{source} погружает {target} в сон.",
                "{target} засыпает под действием {effect}.",
            ],
            control_prevent_action=[
                "{target} крепко спит и не может действовать.",
                "Сон держит {target}: ход пропущен.",
            ],
            expire_effect=[
                "{target} пробуждается.",
                "Сон {target} прошёл.",
            ],
            resist=["{target} сопротивляется сну — {effect} не берёт."],
            cleanse=["{target} разбужен — {effect} снят."],
        ),
    ),
)

# ── KNOCKDOWN ─────────────────────────────────────────────────────────────────

_knockdown_catalog = EffectCatalogEntryDTO(
    key="combat.effect.knockdown",
    technical=EffectTechnicalDTO(
        effect_id="knockdown",
        type=EffectType.CONTROL,
        duration=1,
        resistance_profile_id="control_physical",
        control_logic=ControlInstructionDTO(
            status_name="is_knockdown",
            source_behavior={"can_act": True},
            target_behavior={"can_dodge": False},
        ),
        tags=["control", "knockdown", "physical"],
    ),
    descriptive=_control_description(
        effect_id="knockdown",
        display_name="Сбит с ног",
        short_description="Сбит с ног. Нельзя уклоняться.",
        tooltip="Сбит с ног: нельзя уклоняться.",
        control_term="сбивание с ног",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=[
                "{source} сбивает {target} с ног.",
                "{target} падает — {effect}.",
            ],
            control_prevent_action=[
                "{target} лежит на земле: уклонение невозможно.",
            ],
            expire_effect=[
                "{target} поднимается на ноги.",
                "{effect} {target} проходит.",
            ],
            resist=["{target} удерживает равновесие — {effect} не срабатывает."],
            cleanse=["{effect} {target} снят."],
        ),
    ),
)

# ── DISARM ────────────────────────────────────────────────────────────────────

_disarm_catalog = EffectCatalogEntryDTO(
    key="combat.effect.disarm",
    technical=EffectTechnicalDTO(
        effect_id="disarm",
        type=EffectType.CONTROL,
        duration=2,
        resistance_profile_id="control_physical",
        control_logic=ControlInstructionDTO(
            status_name="is_disarmed",
            source_behavior={"can_use_weapon": False},
            target_behavior={},
        ),
        tags=["control", "disarm", "physical"],
    ),
    descriptive=_control_description(
        effect_id="disarm",
        display_name="Обезоруживание",
        short_description="Нельзя использовать оружие.",
        tooltip="Обезоружен: нельзя использовать оружие.",
        control_term="обезоруживание",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=[
                "{source} выбивает оружие из рук {target}.",
                "{target} обезоружен — {effect}.",
            ],
            control_prevent_action=[
                "{target} обезоружен и не может атаковать оружием.",
            ],
            expire_effect=[
                "{target} подбирает оружие.",
                "{effect} {target} снят.",
            ],
            resist=["{target} удерживает оружие — {effect} не срабатывает."],
            cleanse=["{effect} {target} снят."],
        ),
    ),
)

# ── SILENCE ───────────────────────────────────────────────────────────────────

_silence_catalog = EffectCatalogEntryDTO(
    key="combat.effect.silence",
    technical=EffectTechnicalDTO(
        effect_id="silence",
        type=EffectType.CONTROL,
        duration=2,
        resistance_profile_id="control_mental",
        control_logic=ControlInstructionDTO(
            status_name="is_silenced",
            source_behavior={"can_cast_spell": False},
            target_behavior={},
        ),
        tags=["control", "silence", "magical"],
    ),
    descriptive=_control_description(
        effect_id="silence",
        display_name="Безмолвие",
        short_description="Нельзя использовать магию.",
        tooltip="Безмолвие: нельзя использовать заклинания.",
        control_term="безмолвие",
        humanoid_event_texts=CombatEventTextSetDTO(
            apply_effect=[
                "{source} заглушает магию {target}.",
                "{target} погружается в {effect} — магия недоступна.",
            ],
            control_prevent_action=[
                "{target} под безмолвием: заклинания недоступны.",
            ],
            expire_effect=[
                "Безмолвие {target} спадает.",
                "{target} снова может колдовать.",
            ],
            resist=["{target} противостоит безмолвию — {effect} не берёт."],
            cleanse=["{effect} {target} снят."],
        ),
    ),
)

# ── REGISTRY ──────────────────────────────────────────────────────────────────

CONTROL_EFFECTS_CATALOG: dict[str, EffectCatalogEntryDTO] = {
    "stun": _stun_catalog,
    "sleep": _sleep_catalog,
    "knockdown": _knockdown_catalog,
    "disarm": _disarm_catalog,
    "silence": _silence_catalog,
}

from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
)
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
    raw_modifiers: dict,
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
            raw_modifiers=raw_modifiers,
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
    raw_modifiers={"strength": 1.0},
    tags=["buff", "attribute", "physical"],
    apply_humanoid=["{source} усиливает мощь {target}.", "{target} получает {effect} — сила растёт."],
    expire_humanoid=["Усиление Силы {target} иссякает.", "{target} теряет {effect}."],
)

_buff_dex_catalog = _buff_catalog(
    effect_id="buff_dex",
    display_name="Усиление Ловкости",
    short_description="Увеличивает Ловкость.",
    raw_modifiers={"dexterity": 1.0},
    tags=["buff", "attribute", "physical"],
    apply_humanoid=["{source} обостряет реакцию {target}.", "{target} получает {effect}."],
    expire_humanoid=["Усиление Ловкости {target} иссякает.", "{target} теряет {effect}."],
)

_buff_int_catalog = _buff_catalog(
    effect_id="buff_int",
    display_name="Усиление Интеллекта",
    short_description="Увеличивает Интеллект.",
    raw_modifiers={"intelligence": 1.0},
    tags=["buff", "attribute", "magical"],
    apply_humanoid=["{source} проясняет разум {target}.", "{target} получает {effect}."],
    expire_humanoid=["Усиление Интеллекта {target} рассеивается.", "{target} теряет {effect}."],
)

_buff_end_catalog = _buff_catalog(
    effect_id="buff_end",
    display_name="Усиление Выносливости",
    short_description="Увеличивает Выносливость.",
    raw_modifiers={"endurance": 1.0},
    tags=["buff", "attribute", "physical"],
    apply_humanoid=["{source} укрепляет стойкость {target}.", "{target} получает {effect}."],
    expire_humanoid=["Усиление Выносливости {target} иссякает.", "{target} теряет {effect}."],
)

_buff_armor_catalog = _buff_catalog(
    effect_id="buff_armor",
    display_name="Усиление Брони",
    short_description="Увеличивает Броню.",
    raw_modifiers={"armor": 1.0},
    tags=["buff", "defense", "physical"],
    apply_humanoid=["{source} усиливает броню {target}.", "{target} получает {effect} — броня укреплена."],
    expire_humanoid=["Усиление брони {target} иссякает.", "{target} теряет {effect}."],
)

_buff_evasion_catalog = _buff_catalog(
    effect_id="buff_evasion",
    display_name="Усиление Уклонения",
    short_description="Увеличивает шанс уклонения.",
    raw_modifiers={"evasion": 0.01},
    tags=["buff", "defense", "air"],
    apply_humanoid=["{source} повышает уклонение {target}.", "{target} получает {effect}."],
    expire_humanoid=["Усиление Уклонения {target} иссякает.", "{target} теряет {effect}."],
)

_buff_accuracy_catalog = _buff_catalog(
    effect_id="buff_accuracy",
    display_name="Усиление Точности",
    short_description="Увеличивает точность.",
    raw_modifiers={"accuracy": 0.01},
    tags=["buff", "offense"],
    apply_humanoid=["{source} направляет руку {target}.", "{target} получает {effect} — точность растёт."],
    expire_humanoid=["Усиление Точности {target} иссякает.", "{target} теряет {effect}."],
)

_buff_crit_catalog = _buff_catalog(
    effect_id="buff_crit",
    display_name="Усиление Крита",
    short_description="Увеличивает шанс крита.",
    raw_modifiers={"crit_chance": 0.01},
    tags=["buff", "offense"],
    apply_humanoid=["{source} обостряет инстинкт {target}.", "{target} получает {effect}."],
    expire_humanoid=["Усиление Крита {target} иссякает.", "{target} теряет {effect}."],
)

_buff_phys_dmg_catalog = _buff_catalog(
    effect_id="buff_phys_dmg",
    display_name="Усиление Физ. Урона",
    short_description="Увеличивает физический урон.",
    raw_modifiers={"physical_damage_bonus": 1.0},
    tags=["buff", "offense", "physical"],
    apply_humanoid=["{source} усиливает удары {target}.", "{target} получает {effect} — урон растёт."],
    expire_humanoid=["Усиление Урона {target} иссякает.", "{target} теряет {effect}."],
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
}

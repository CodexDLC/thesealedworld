from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CombatTaxonomy = Literal["humanoid", "beast"]


class CombatEventTextSetDTO(BaseModel):
    use: list[str] = Field(default_factory=list)
    hit: list[str] = Field(default_factory=list)
    crit: list[str] = Field(default_factory=list)
    miss: list[str] = Field(default_factory=list)
    block: list[str] = Field(default_factory=list)
    parry: list[str] = Field(default_factory=list)
    dodge: list[str] = Field(default_factory=list)
    apply_effect: list[str] = Field(default_factory=list)
    expire_effect: list[str] = Field(default_factory=list)


class CombatTaxonomyDescriptionDTO(BaseModel):
    icon: str
    display_name: str
    short_description: str
    long_description: str
    ui_label: str
    tooltip: str
    event_texts: CombatEventTextSetDTO = Field(default_factory=CombatEventTextSetDTO)


class CombatDescriptionDTO(BaseModel):
    default_taxonomy: CombatTaxonomy = "humanoid"
    variants: dict[CombatTaxonomy, CombatTaxonomyDescriptionDTO]


class CombatCatalogEntryDTO(BaseModel):
    key: str
    technical: Any
    descriptive: CombatDescriptionDTO


def build_combat_description(
    *,
    resource_type: str,
    resource_id: str,
    display_name: str,
    short_description: str,
    humanoid_event_texts: CombatEventTextSetDTO,
    beast_event_texts: CombatEventTextSetDTO,
    humanoid_long_description: str = "",
    beast_display_name: str = "",
    beast_short_description: str = "",
    beast_long_description: str = "",
    ui_label: str = "",
    tooltip: str = "",
    icon: str = "",
) -> CombatDescriptionDTO:
    resolved_icon = icon or f"combat/{resource_type}/{resource_id}.png"
    resolved_ui_label = ui_label or display_name
    resolved_tooltip = tooltip or short_description
    resolved_long = humanoid_long_description or short_description
    resolved_beast_display = beast_display_name or display_name
    resolved_beast_short = beast_short_description or short_description
    resolved_beast_long = beast_long_description or resolved_beast_short

    return CombatDescriptionDTO(
        variants={
            "humanoid": CombatTaxonomyDescriptionDTO(
                icon=resolved_icon,
                display_name=display_name,
                short_description=short_description,
                long_description=resolved_long,
                ui_label=resolved_ui_label,
                tooltip=resolved_tooltip,
                event_texts=humanoid_event_texts,
            ),
            "beast": CombatTaxonomyDescriptionDTO(
                icon=resolved_icon,
                display_name=resolved_beast_display,
                short_description=resolved_beast_short,
                long_description=resolved_beast_long,
                ui_label=resolved_beast_display,
                tooltip=resolved_beast_short,
                event_texts=beast_event_texts,
            ),
        }
    )


def default_ability_event_texts(name: str) -> CombatEventTextSetDTO:
    return CombatEventTextSetDTO(
        use=[
            "{source} использует {ability}.",
            "{source} направляет {ability} на {target}.",
        ],
        hit=[
            "{ability} попадает по {target}.",
            "{target} получает удар от {ability}.",
        ],
        crit=[
            "{ability} критически поражает {target}.",
            "{source} усиливает {ability}, и {target} получает критический удар.",
        ],
        miss=[
            "{ability} проходит мимо {target}.",
            "{source} не попадает по {target} способностью {ability}.",
        ],
        block=[
            "{target} блокирует {ability}.",
        ],
        parry=[
            "{target} парирует {ability}.",
        ],
        dodge=[
            "{target} уклоняется от {ability}.",
        ],
        apply_effect=[
            "{ability} накладывает {effect} на {target}.",
            "{target} получает эффект {effect} от {ability}.",
        ],
        expire_effect=[
            "{effect} от {ability} на {target} заканчивается.",
        ],
    )


def default_feint_event_texts(name: str) -> CombatEventTextSetDTO:
    return CombatEventTextSetDTO(
        use=[
            "{source} применяет финт {feint}.",
            "{source} готовит {feint} против {target}.",
        ],
        hit=[
            "{feint} попадает по {target}.",
            "{source} проводит {feint} по {target}.",
        ],
        crit=[
            "{source} проводит критический {feint} по {target}.",
            "{feint} особенно болезненно поражает {target}.",
        ],
        miss=[
            "{source} срывает {feint} и промахивается по {target}.",
        ],
        block=[
            "{target} блокирует {feint}.",
        ],
        parry=[
            "{target} парирует {feint}.",
        ],
        dodge=[
            "{target} уходит от финта {source}: {feint}.",
        ],
        apply_effect=[
            "{feint} накладывает {effect} на {target}.",
        ],
        expire_effect=[
            "{effect} от финта {feint} на {target} заканчивается.",
        ],
    )


def default_effect_event_texts(name: str) -> CombatEventTextSetDTO:
    return CombatEventTextSetDTO(
        apply_effect=[
            "{source} накладывает {effect} на {target}.",
            "{target} получает эффект {effect}.",
        ],
        expire_effect=[
            "{effect} на {target} заканчивается.",
            "{target} больше не находится под эффектом {effect}.",
        ],
        hit=[
            "{effect} действует на {target}.",
        ],
        crit=[
            "{effect} резко усиливается на {target}.",
        ],
        miss=[
            "{effect} не закрепляется на {target}.",
        ],
    )


def default_trigger_event_texts(name: str) -> CombatEventTextSetDTO:
    return CombatEventTextSetDTO(
        use=[
            "Срабатывает {trigger}.",
            "{trigger} меняет ход размена.",
        ],
        hit=[
            "{trigger} срабатывает при попадании по {target}.",
        ],
        crit=[
            "{trigger} срабатывает на критическом ударе по {target}.",
        ],
        miss=[
            "{trigger} срабатывает после промаха {source}.",
        ],
        block=[
            "{trigger} срабатывает при блоке {target}.",
        ],
        parry=[
            "{trigger} срабатывает при парировании {target}.",
        ],
        dodge=[
            "{trigger} срабатывает при уклонении {target}.",
        ],
        apply_effect=[
            "{trigger} накладывает {effect} на {target}.",
        ],
        expire_effect=[
            "Последствие {trigger} на {target} заканчивается.",
        ],
    )


def default_gift_event_texts(name: str) -> CombatEventTextSetDTO:
    return CombatEventTextSetDTO(
        use=[
            "{source} обращается к дару {gift}.",
            "Дар {gift} отзывается на волю {source}.",
        ],
        hit=[
            "Дар {gift} помогает {source} поразить {target}.",
        ],
        crit=[
            "Дар {gift} вспыхивает особенно ярко и поражает {target}.",
        ],
        miss=[
            "Дар {gift} не достигает {target}.",
        ],
        apply_effect=[
            "Дар {gift} накладывает {effect} на {target}.",
        ],
        expire_effect=[
            "Влияние дара {gift} на {target} заканчивается.",
        ],
    )

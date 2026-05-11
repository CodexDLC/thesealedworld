from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, Field

CombatTaxonomy = Literal["humanoid", "beast"]


class CombatResolvedTemplateDTO(BaseModel):
    text: str
    event: str
    taxonomy: str
    variant: int = 0


class CombatEventTextSetDTO(BaseModel):
    attack_use: list[str] = Field(default_factory=list)
    hit_result: list[str] = Field(default_factory=list)
    crit_result: list[str] = Field(default_factory=list)
    miss_result: list[str] = Field(default_factory=list)
    block_result: list[str] = Field(default_factory=list)
    parry_result: list[str] = Field(default_factory=list)
    dodge_result: list[str] = Field(default_factory=list)
    use: list[str] = Field(default_factory=list)
    hit: list[str] = Field(default_factory=list)
    crit: list[str] = Field(default_factory=list)
    miss: list[str] = Field(default_factory=list)
    block: list[str] = Field(default_factory=list)
    parry: list[str] = Field(default_factory=list)
    dodge: list[str] = Field(default_factory=list)
    apply_effect: list[str] = Field(default_factory=list)
    heal: list[str] = Field(default_factory=list)
    area_use: list[str] = Field(default_factory=list)
    area_result: list[str] = Field(default_factory=list)
    no_resource: list[str] = Field(default_factory=list)
    expire_effect: list[str] = Field(default_factory=list)
    tick: list[str] = Field(default_factory=list)
    resist: list[str] = Field(default_factory=list)
    cleanse: list[str] = Field(default_factory=list)
    control_prevent_action: list[str] = Field(default_factory=list)
    proc: list[str] = Field(default_factory=list)
    hit_proc: list[str] = Field(default_factory=list)
    crit_proc: list[str] = Field(default_factory=list)
    miss_proc: list[str] = Field(default_factory=list)
    dodge_proc: list[str] = Field(default_factory=list)
    parry_proc: list[str] = Field(default_factory=list)
    block_proc: list[str] = Field(default_factory=list)
    token_gain: list[str] = Field(default_factory=list)
    counter: list[str] = Field(default_factory=list)
    extra_strike: list[str] = Field(default_factory=list)

    def event_template(self, event: str) -> str | None:
        templates = getattr(self, event, None)
        if not isinstance(templates, list) or not templates:
            return None
        template = templates[0]
        return template if isinstance(template, str) and template else None

    def exchange_template(self, outcome: str) -> str | None:
        attack = self.event_template("attack_use") or self.event_template("use")
        result = self.event_template(f"{outcome}_result") or self.event_template(outcome)
        if attack and result:
            return self._sentence(f"{attack.rstrip(' .')}, {result.lstrip(' .')}")
        if attack:
            return self._sentence(attack)
        if result:
            return self._sentence(result)
        return None

    @staticmethod
    def _sentence(text: str) -> str:
        text = text.strip()
        if not text:
            return text
        return text if text[-1] in ".!?" else f"{text}."


class CombatTaxonomyDescriptionDTO(BaseModel):
    icon: str
    display_name: str
    short_description: str
    long_description: str
    ui_label: str
    tooltip: str
    event_texts: CombatEventTextSetDTO = Field(default_factory=CombatEventTextSetDTO)
    control_term: str | None = None


class CombatDescriptionDTO(BaseModel):
    default_taxonomy: CombatTaxonomy = "humanoid"
    variants: dict[CombatTaxonomy, CombatTaxonomyDescriptionDTO]

    def resolve_event_template(
        self,
        event: str,
        taxonomy_chain: list[str] | None = None,
    ) -> CombatResolvedTemplateDTO | None:
        for taxonomy in self._taxonomy_candidates(taxonomy_chain):
            variant = self.variants.get(cast("CombatTaxonomy", taxonomy))
            if variant is None:
                continue
            text = variant.event_texts.event_template(event)
            if text:
                return CombatResolvedTemplateDTO(text=text, event=event, taxonomy=taxonomy)
        return None

    def resolve_exchange_template(
        self,
        outcome: str,
        taxonomy_chain: list[str] | None = None,
    ) -> CombatResolvedTemplateDTO | None:
        for taxonomy in self._taxonomy_candidates(taxonomy_chain):
            variant = self.variants.get(cast("CombatTaxonomy", taxonomy))
            if variant is None:
                continue
            text = variant.event_texts.exchange_template(outcome)
            if text:
                return CombatResolvedTemplateDTO(text=text, event=outcome, taxonomy=taxonomy)
        return None

    def _taxonomy_candidates(self, taxonomy_chain: list[str] | None = None) -> list[str]:
        candidates = [*(taxonomy_chain or []), self.default_taxonomy, "humanoid"]
        return list(dict.fromkeys(candidate for candidate in candidates if candidate))


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
    control_term: str | None = None,
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
                control_term=control_term,
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
        heal=[
            "{source} направляет {ability} на {target}.",
            "{ability} восстанавливает силы {target}.",
        ],
        area_use=[
            "{source} использует {ability}.",
        ],
        area_result=[
            "{ability} расходится по {targets_count} целям.",
        ],
        no_resource=[
            "{source} пытается использовать {ability}, но сил не хватает.",
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


def default_trigger_proc_event_texts(name: str) -> CombatEventTextSetDTO:
    return CombatEventTextSetDTO(
        proc=[
            f"Срабатывает {name}.",
            f"{{source}} активирует {name}.",
        ],
        hit_proc=[
            f"{name} вступает в действие: {{source}} поражает {{target}}.",
        ],
        crit_proc=[
            f"{name} срабатывает на крите: {{source}} рассекает {{target}}.",
        ],
        miss_proc=[
            f"{name} даёт {{source}} преимущество после промаха.",
        ],
        dodge_proc=[
            f"{name}: {{target}} уклоняется и контратакует.",
        ],
        parry_proc=[
            f"{name}: {{target}} парирует и отвечает.",
        ],
        block_proc=[
            f"{name}: {{target}} блокирует и наносит ответный удар.",
        ],
        apply_effect=[
            f"{name} накладывает {{effect}} на {{target}}.",
        ],
        token_gain=[
            f"{{source}} получает токен {{token}} от {name}.",
        ],
        counter=[
            f"{name} открывает контратаку {{source}} по {{target}}.",
        ],
        extra_strike=[
            f"{name} даёт {{source}} дополнительный удар по {{target}}.",
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
        heal=[
            "Дар {gift} возвращает силы {target}.",
        ],
        area_use=[
            "{source} раскрывает дар {gift}.",
        ],
        area_result=[
            "Дар {gift} касается {targets_count} целей.",
        ],
        no_resource=[
            "Дар {gift} не отзывается: {source} не хватает ресурса.",
        ],
        expire_effect=[
            "Влияние дара {gift} на {target} заканчивается.",
        ],
    )

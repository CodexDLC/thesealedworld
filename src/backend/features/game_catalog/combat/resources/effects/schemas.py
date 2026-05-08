from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatCatalogEntryDTO,
    CombatDescriptionDTO,
)


class EffectType(StrEnum):
    DOT = "dot"  # Damage Over Time
    HOT = "hot"  # Heal Over Time
    BUFF = "buff"  # Stat Bonus
    DEBUFF = "debuff"  # Stat Penalty
    CONTROL = "control"  # Stun, Sleep, Silence (Logic)


class ControlInstructionDTO(BaseModel):
    """
    Инструкции поведения для эффектов контроля.
    """

    # Имя флага состояния (для UI/AI и проверок)
    # Пример: "is_stun", "is_blind"
    status_name: str

    # Инструкции для Атакующего (если он под этим эффектом)
    # Ключи, которые понимает AbilityService/ContextBuilder.
    # Пример: {"can_act": False} (Стан), {"accuracy_mult": 0.5} (Слепота)
    source_behavior: dict[str, Any] = Field(default_factory=dict)

    # Инструкции для Защитника (если он под этим эффектом)
    # Пример: {"can_dodge": False} (Стан), {"damage_taken_mult": 1.5} (Уязвимость)
    target_behavior: dict[str, Any] = Field(default_factory=dict)


class EffectTechnicalDTO(BaseModel):
    """Pure technical configuration for an effect (no display text)."""

    effect_id: str
    type: EffectType
    duration: int
    resource_impact: dict[str, int] = Field(default_factory=dict)
    raw_modifiers: dict[str, float] = Field(default_factory=dict)
    control_logic: ControlInstructionDTO | None = None
    tags: list[str] = Field(default_factory=list)


class EffectCatalogEntryDTO(CombatCatalogEntryDTO):
    """
    Catalog contract: key + technical + descriptive.
    Catalog key format: "combat.effect.{effect_id}"
    """

    technical: EffectTechnicalDTO
    descriptive: CombatDescriptionDTO


class EffectDTO(BaseModel):
    """
    Шаблон эффекта в библиотеке (GameData).
    """

    effect_id: str
    name_en: str
    name_ru: str

    type: EffectType
    duration: int

    # --- 1. Ресурсы (DOT/HOT) ---
    # Базовое значение за ход.
    # Пример: {"hp": -10, "en": 5}
    resource_impact: dict[str, int] = Field(default_factory=dict)

    # --- 2. Статы (BUFF/DEBUFF) ---
    # Значения, которые добавляются в temp modifiers.
    # Пример: {"strength": 5.0, "armor": -10.0}
    raw_modifiers: dict[str, float] = Field(default_factory=dict)

    # --- 3. Логика (CONTROL) ---
    # Инструкции поведения.
    control_logic: ControlInstructionDTO | None = None

    # Теги (для диспела/иммунитета)
    tags: list[str] = Field(default_factory=list)

    description: str

    @classmethod
    def from_catalog_entry(cls, entry: EffectCatalogEntryDTO) -> EffectDTO:
        t = entry.technical
        variant = entry.descriptive.variants.get(entry.descriptive.default_taxonomy)
        return cls(
            effect_id=t.effect_id,
            name_en=getattr(variant, "display_name", t.effect_id),
            name_ru=getattr(variant, "display_name", t.effect_id),
            type=t.type,
            duration=t.duration,
            resource_impact=t.resource_impact,
            raw_modifiers=t.raw_modifiers,
            control_logic=t.control_logic,
            tags=t.tags,
            description=getattr(variant, "short_description", ""),
        )

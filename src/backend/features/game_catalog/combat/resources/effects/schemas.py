from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatCatalogEntryDTO,
    CombatDescriptionDTO,
)
from src.backend.features.game_catalog.combat.resources.common.modifier_applications import (  # noqa: TC001
    ModifierApplicationDTO,
)
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import (  # noqa: TC001
    PipelineMutationApplicationDTO,
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


class EffectResistanceProfileDTO(BaseModel):
    """Chance gate configuration for applying an effect to a target."""

    profile_id: str
    base_chance: float = 1.0
    source_modifiers: list[str] = Field(default_factory=list)
    target_modifiers: list[str] = Field(default_factory=list)
    floor: float = 0.05
    cap: float = 1.0
    tags: list[str] = Field(default_factory=list)


class EffectTechnicalDTO(BaseModel):
    """Pure technical configuration for an effect (no display text)."""

    effect_id: str
    type: EffectType
    duration: int
    resistance_profile_id: str | None = None
    resource_impact: dict[str, int] = Field(default_factory=dict)
    modifier_applications: list[ModifierApplicationDTO] = Field(default_factory=list)
    pipeline_mutations: list[PipelineMutationApplicationDTO] = Field(default_factory=list)
    pipeline_mutation_role: Literal["source", "target", "both"] = "target"
    react_on_outcomes: list[str] = Field(default_factory=list)
    consume_on_reaction: bool = True
    control_logic: ControlInstructionDTO | None = None
    tags: list[str] = Field(default_factory=list)


class EffectCatalogEntryDTO(CombatCatalogEntryDTO):
    """
    Catalog contract: key + technical + descriptive.
    Catalog key format: "combat.effect.{effect_id}"
    """

    technical: EffectTechnicalDTO
    descriptive: CombatDescriptionDTO

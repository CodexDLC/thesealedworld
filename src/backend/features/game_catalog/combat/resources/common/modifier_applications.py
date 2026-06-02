from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ModifierApplicationTargetActor = Literal["self", "target", "attacker", "defender"]
ModifierApplicationValueMode = Literal["base", "base_multiplier", "override", "source_main_hand_damage_multiplier"]
ModifierApplicationScope = Literal["current_exchange", "duration"]


class ModifierApplicationDTO(BaseModel):
    """Catalog-side request to apply a numeric modifier contract at runtime."""

    modifier_id: str
    target_actor: ModifierApplicationTargetActor = "self"
    value_mode: ModifierApplicationValueMode = "base"
    value_multiplier: float = 1.0
    value_override: float | None = None
    scope: ModifierApplicationScope = "current_exchange"
    duration_exchanges: int | None = None
    tags: list[str] = Field(default_factory=list)

from typing import Any

from pydantic import BaseModel, Field

from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatCatalogEntryDTO,
    CombatDescriptionDTO,
)


class TriggerTechnicalDTO(BaseModel):
    """
    Pure logic configuration for a trigger.
    Consumed by CombatResolver._resolve_triggers() and log_builder.
    No UI fields.
    """

    trigger_id: str  # Matches the flag name in TriggerRulesFlagsDTO, e.g. "bleed_on_crit"

    # Activation event: "ON_CRIT", "ON_MISS", "ON_DODGE", "ON_PARRY",
    # "ON_BLOCK", "ON_BLOCK_FAIL", "ON_CHECK_CONTROL", "ON_ACCURACY_CHECK", "ON_DAMAGE"
    event: str

    chance: float = 1.0

    # Key-path mutations applied to PipelineContextDTO / InteractionResultDTO.
    # Supports dotted paths ("formula.can_pierce": True) and the
    # special "add_effect" command ({"id": "dot_bleed"}).
    mutations: dict[str, Any] = Field(default_factory=dict)

    # Explicit effect IDs applied by this trigger (populated manually at definition time).
    # Lets log_builder resolve effect display names without parsing mutations.
    applied_effect_ids: list[str] = Field(default_factory=list)

    token_grants_attacker: list[str] = Field(default_factory=list)
    token_grants_defender: list[str] = Field(default_factory=list)


class TriggerCatalogEntryDTO(CombatCatalogEntryDTO):
    """
    Full catalog record for a trigger.
    key        — "combat.trigger.{group}.{trigger_id}"
    technical  — TriggerTechnicalDTO (logic)
    descriptive — CombatDescriptionDTO (display text, icons)
    """

    technical: TriggerTechnicalDTO
    descriptive: CombatDescriptionDTO

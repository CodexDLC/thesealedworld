from typing import Literal

from pydantic import BaseModel, Field

from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatCatalogEntryDTO,
    CombatDescriptionDTO,
)
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import PipelineMutationApplicationDTO

TriggerSource = Literal["weapon", "feint", "style", "effect", "ability", "monster", "system"]
TriggerStackingRule = Literal["unique", "stack", "strongest", "refresh", "forbidden_duplicate"]
TriggerDisplayPolicy = Literal["merge", "separate", "silent"]


def default_trigger_sources() -> list[TriggerSource]:
    return ["weapon", "feint", "style", "effect", "ability", "monster", "system"]


class TriggerTechnicalDTO(BaseModel):
    """
    Pure logic configuration for a trigger.
    Consumed by resolver.support.trigger_activator.resolve_triggers() and log_builder.
    No UI fields.
    """

    trigger_id: str  # Matches the flag name in TriggerRulesFlagsDTO, e.g. "weapon_heavy_crit"

    # Activation event: "ON_CRIT", "ON_MISS", "ON_DODGE", "ON_PARRY",
    # "ON_BLOCK", "ON_BLOCK_FAIL", "ON_CHECK_CONTROL", "ON_ACCURACY_CHECK",
    # "ON_PRE_EVASION", "ON_DAMAGE"
    event: str

    chance: float = 1.0
    chance_skill_key: str | None = None
    chance_skill_scale: float = 0.0
    chance_cap: float | None = None

    # Whitelisted pipeline-local context/result mutations.
    pipeline_mutations: list[PipelineMutationApplicationDTO] = Field(default_factory=list)

    # Standard trigger-catalog metadata. Sources are validated by activation
    # helpers before a trigger is exposed to the resolver.
    allowed_sources: list[TriggerSource] = Field(default_factory=default_trigger_sources)
    stacking_rule: TriggerStackingRule = "unique"
    display_policy: TriggerDisplayPolicy = "merge"
    tags: list[str] = Field(default_factory=list)

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

from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatCatalogEntryDTO,
    CombatDescriptionDTO,
)
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType


class CombatItemActionKind(StrEnum):
    CONSUMABLE = "consumable"
    GRENADE = "grenade"
    SCROLL = "scroll"


class CombatItemConsumePolicy(StrEnum):
    ON_ACCEPT = "on_accept"
    ON_HIT = "on_hit"
    NEVER = "never"


class CombatItemActionTechnicalDTO(BaseModel):
    item_action_id: str
    item_id: str | None = None
    base_item_id: str | None = None
    ability_id: str | None = None
    kind: CombatItemActionKind = CombatItemActionKind.CONSUMABLE
    consume_policy: CombatItemConsumePolicy = CombatItemConsumePolicy.ON_ACCEPT
    target: TargetType = TargetType.SINGLE_ENEMY
    target_count: int = 1
    triggers: list[str] | None = None
    override_damage: tuple[float, float] | None = None
    effects: list[dict[str, Any]] | None = None
    token_grants: dict[str, int] | None = None


class CombatItemActionCatalogEntryDTO(CombatCatalogEntryDTO):
    key: str
    technical: CombatItemActionTechnicalDTO
    descriptive: CombatDescriptionDTO

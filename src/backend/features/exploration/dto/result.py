from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.shared.enums import CoreDomain


@dataclass(frozen=True, slots=True)
class ExplorationTransition:
    char_id: int
    target_state: CoreDomain
    reason: str
    combat_id: str | int | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class MoveResolution:
    current_loc_id: str
    current_loc_data: dict[str, Any]
    target_loc_id: str | None = None
    target_loc_data: dict[str, Any] | None = None
    allowed: bool = False
    message: str | None = None

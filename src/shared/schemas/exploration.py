# src/shared/schemas/exploration.py
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


# --- Enums ---

class HudType(str, Enum):
    ALERT = "alert"
    INFO = "info"
    EXPLORATION = "exploration"


class EncounterType(str, Enum):
    COMBAT = "combat"
    MERCHANT = "merchant"
    QUEST = "quest"
    OBJECT = "object"


class DetectionStatus(str, Enum):
    DETECTED = "detected"
    AMBUSH = "ambush"
    HIDDEN = "hidden"


# --- DTOs ---

class GridButtonDTO(BaseModel):
    id: str
    label: str
    action: str
    is_active: bool = True
    style: str = "primary"  # primary, secondary, danger, success


class NavigationGridDTO(BaseModel):
    # 3x3 Grid (Telegram Legacy)
    nw: GridButtonDTO | None = None
    n: GridButtonDTO | None = None
    ne: GridButtonDTO | None = None
    w: GridButtonDTO | None = None
    center: GridButtonDTO | None = None
    e: GridButtonDTO | None = None
    sw: GridButtonDTO | None = None
    s: GridButtonDTO | None = None
    se: GridButtonDTO | None = None
    
    # Additional service buttons (bottom row)
    services: list[GridButtonDTO] = Field(default_factory=list)


class ExplorationHudDTO(BaseModel):
    threat_tier: int = 0
    players_count: int = 0
    battles_count: int = 0
    is_safe_zone: bool = False


class AlertHudDTO(BaseModel):
    message: str
    style: str = "info"


class WorldNavigationDTO(BaseModel):
    loc_id: str
    title: str
    description: str
    visual_objects: list[dict[str, Any]] = Field(default_factory=list)
    players_nearby: int = 0
    grid: NavigationGridDTO
    hud: ExplorationHudDTO | AlertHudDTO


class EnemyPreviewDTO(BaseModel):
    name: str
    level: int
    hp_percent: float = 100.0


class EncounterOptionDTO(BaseModel):
    id: str
    label: str
    style: str = "primary"


class EncounterDTO(BaseModel):
    id: str
    type: EncounterType
    status: DetectionStatus = DetectionStatus.DETECTED
    title: str
    description: str
    enemies: list[EnemyPreviewDTO] = Field(default_factory=list)
    options: list[EncounterOptionDTO] = Field(default_factory=list)
    session_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ListItemDTO(BaseModel):
    id: str
    text: str
    action: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExplorationListDTO(BaseModel):
    title: str
    items: list[ListItemDTO]
    page: int = 1
    total_pages: int = 1
    back_action: str = "look_around"


# --- Requests ---

class MoveRequest(BaseModel):
    char_id: int
    direction: str | None = None
    target_id: str | None = None


class InteractRequest(BaseModel):
    char_id: int
    action: str
    target_id: str | None = None


class UseServiceRequest(BaseModel):
    char_id: int
    service_id: str

# src/shared/schemas/exploration.py
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from src.shared.schemas.world_theme import WorldThemeDTO

# --- Enums ---


class HudType(StrEnum):
    ALERT = "alert"
    INFO = "info"
    EXPLORATION = "exploration"


class EncounterType(StrEnum):
    COMBAT = "combat"
    MERCHANT = "merchant"
    QUEST = "quest"
    OBJECT = "object"


class DetectionStatus(StrEnum):
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


class NavigationActionsDTO(BaseModel):
    movement: dict[str, GridButtonDTO] = Field(default_factory=dict)
    exploration: dict[str, GridButtonDTO] = Field(default_factory=dict)
    services: dict[str, GridButtonDTO] = Field(default_factory=dict)
    auto_routes: dict[str, GridButtonDTO] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class ExplorationHudDTO(BaseModel):
    threat_tier: float = 0
    players_count: int = 0
    battles_count: int = 0
    is_safe_zone: bool = False
    dominant_anchor: str | None = None
    ambient_tags: list[str] = Field(default_factory=list)


class AlertHudDTO(BaseModel):
    message: str
    style: str = "info"


class WorldNavigationDTO(BaseModel):
    loc_id: str
    title: str
    description: str
    background_url: str | None = None
    anchor_influence: dict[str, Any] = Field(default_factory=dict)
    world_theme: WorldThemeDTO = Field(default_factory=WorldThemeDTO)
    visual_objects: list[dict[str, Any]] = Field(default_factory=list)
    players_nearby: int = 0
    grid: NavigationGridDTO
    navigation: NavigationActionsDTO = Field(default_factory=NavigationActionsDTO)
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

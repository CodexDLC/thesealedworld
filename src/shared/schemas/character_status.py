from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.shared.enums import CoreDomain
from src.shared.schemas.panel import PanelDTO
from src.shared.schemas.world_theme import WorldThemeDTO


class CharacterActorCoreDTO(BaseModel):
    """Public snapshot of the Redis actor core document: game:ac:{char_id}."""

    model_config = ConfigDict(extra="allow")

    key: str
    schema_version: int = 1
    char_id: int
    user_id: UUID | str
    state: CoreDomain | str
    prev_state: CoreDomain | str | None = None
    bio: dict[str, Any] = Field(default_factory=dict)
    location: dict[str, Any] = Field(default_factory=dict)
    vitals: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)
    sessions: dict[str, Any] = Field(default_factory=dict)
    active_quest: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    skills: dict[str, Any] = Field(default_factory=dict)
    symbiote: dict[str, Any] = Field(default_factory=dict)
    world_theme: WorldThemeDTO = Field(default_factory=WorldThemeDTO)
    updated_at: datetime | str | None = None
    panel: PanelDTO | None = None

from __future__ import annotations

import uuid  # noqa: TC003
from datetime import datetime  # noqa: TC003
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.shared.enums import CoreDomain

CharacterGender = Literal["male", "female", "other"]


class VitalValueDTO(BaseModel):
    cur: int
    max: int
    regen: float = 0.0


class CharacterSessionBioDTO(BaseModel):
    name: str
    gender: CharacterGender
    avatar: str | None = None
    created_at: datetime


class CharacterSessionLocationDTO(BaseModel):
    current: str = "52_52"
    prev: str | None = None


class CharacterSessionVitalsDTO(BaseModel):
    hp: VitalValueDTO = Field(default_factory=lambda: VitalValueDTO(cur=100, max=100))
    energy: VitalValueDTO = Field(default_factory=lambda: VitalValueDTO(cur=100, max=100))
    stamina: VitalValueDTO = Field(default_factory=lambda: VitalValueDTO(cur=100, max=100))
    last_update: float = 0.0


class CharacterSessionAttributesDTO(BaseModel):
    strength: int = 8
    agility: int = 8
    endurance: int = 8
    intelligence: int = 8
    wisdom: int = 8
    men: int = 8
    perception: int = 8
    charisma: int = 8
    luck: int = 8


class CharacterSessionRefsDTO(BaseModel):
    scenario_id: str | None = None
    combat_id: str | None = None
    inventory_id: str | None = None


class CharacterSessionMetricsDTO(BaseModel):
    gear_score: int = 0


class CharacterSessionSymbioteDTO(BaseModel):
    name: str = "Symbiote"
    gift_id: str | None = None
    gift_rank: int = 1


class CharacterSessionDocumentDTO(BaseModel):
    schema_version: int = 1
    char_id: int
    user_id: uuid.UUID
    state: CoreDomain = CoreDomain.SCENARIO
    prev_state: CoreDomain | None = CoreDomain.LOBBY
    bio: CharacterSessionBioDTO
    location: CharacterSessionLocationDTO = Field(default_factory=CharacterSessionLocationDTO)
    vitals: CharacterSessionVitalsDTO = Field(default_factory=CharacterSessionVitalsDTO)
    attributes: CharacterSessionAttributesDTO = Field(default_factory=CharacterSessionAttributesDTO)
    sessions: CharacterSessionRefsDTO = Field(default_factory=CharacterSessionRefsDTO)
    active_quest: str | None = None
    metrics: CharacterSessionMetricsDTO = Field(default_factory=CharacterSessionMetricsDTO)
    skills: dict[str, object] = Field(default_factory=dict)
    symbiote: CharacterSessionSymbioteDTO = Field(default_factory=CharacterSessionSymbioteDTO)
    updated_at: datetime

    model_config = ConfigDict(use_enum_values=True)

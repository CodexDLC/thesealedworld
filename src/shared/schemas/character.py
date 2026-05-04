import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Gender = Literal["male", "female", "other"]


class CharacterShellCreateDTO(BaseModel):
    user_id: uuid.UUID


class CharacterShellDTO(BaseModel):
    character_id: int


class CharacterOnboardingUpdateDTO(BaseModel):
    name: str
    gender: Gender
    game_stage: str


class CharacterReadDTO(BaseModel):
    character_id: int
    user_id: uuid.UUID
    name: str
    gender: Gender
    avatar_url: str | None = None
    game_stage: str
    prev_game_stage: str | None = None
    location_id: str = "52_52"
    prev_location_id: str | None = None
    vitals_snapshot: dict[str, Any] | None = None
    active_sessions: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CharacterAttributesUpdateDTO(BaseModel):
    strength: int
    agility: int
    endurance: int
    intelligence: int
    wisdom: int
    men: int
    perception: int
    charisma: int
    luck: int


class CharacterAttributesReadDTO(CharacterAttributesUpdateDTO):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    character_id: int = 0

    model_config = ConfigDict(from_attributes=True)


class CharacterStatusDTO(BaseModel):
    character_id: int
    hp: float
    max_hp: int
    energy: float
    max_energy: int
    stamina: float
    max_stamina: int
    last_update: datetime
    avatar_url: str | None = None
    name: str | None = None


CharacterStatsUpdateDTO = CharacterAttributesUpdateDTO
CharacterStatsReadDTO = CharacterAttributesReadDTO

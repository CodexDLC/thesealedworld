from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.shared.utils.character_name import (
    CHARACTER_NAME_MAX_LENGTH,
    CHARACTER_NAME_MIN_LENGTH,
    CharacterNameError,
    normalize_character_name,
)

CharacterCreationGender = Literal["male", "female", "other"]


class CreateCharacterRequestDTO(BaseModel):
    name: str = Field(..., min_length=CHARACTER_NAME_MIN_LENGTH, max_length=CHARACTER_NAME_MAX_LENGTH)
    gender: CharacterCreationGender
    avatar: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        try:
            return normalize_character_name(value).display
        except CharacterNameError as exc:
            raise ValueError(exc.message) from exc


class EnterCharacterRequestDTO(BaseModel):
    character_id: int


class DeleteCharacterRequestDTO(BaseModel):
    character_id: int
    confirm_name: str = Field(..., min_length=CHARACTER_NAME_MIN_LENGTH, max_length=CHARACTER_NAME_MAX_LENGTH)

    @field_validator("confirm_name")
    @classmethod
    def normalize_confirm_name(cls, value: str) -> str:
        try:
            return normalize_character_name(value).display
        except CharacterNameError as exc:
            raise ValueError(exc.message) from exc


class CharacterNameAvailabilityRequestDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


class CharacterNameAvailabilityDTO(BaseModel):
    available: bool
    name: str | None = None
    name_key: str | None = None
    code: str | None = None
    message: str | None = None


class GameLobbyUserContextDTO(BaseModel):
    user_id: UUID
    email: str | None = None


class GameLobbyPopulationStatsDTO(BaseModel):
    characters_total: int = 0


class CharacterSummaryItemDTO(BaseModel):
    name: str
    item_type: str = ""
    slot: str | None = None
    rarity: str = "shared"
    quantity: int = 1


class CharacterSummarySkillDTO(BaseModel):
    skill_key: str
    total_xp: float = 0.0
    is_unlocked: bool = False
    progress_state: str = ""


class CharacterInventorySummaryDTO(BaseModel):
    equipped_count: int = 0
    backpack_count: int = 0
    resource_count: int = 0
    currency: dict[str, int] = Field(default_factory=dict)
    resources: dict[str, int] = Field(default_factory=dict)
    components: dict[str, int] = Field(default_factory=dict)


class GameLobbyCharacterSelectRequestDTO(GameLobbyUserContextDTO):
    character_id: int


class GameLobbyCharacterCreateRequestDTO(GameLobbyUserContextDTO):
    character: CreateCharacterRequestDTO


class GameLobbyCharacterReleaseRequestDTO(GameLobbyUserContextDTO):
    character: EnterCharacterRequestDTO


class GameLobbyCharacterDeleteRequestDTO(GameLobbyUserContextDTO):
    character: DeleteCharacterRequestDTO


class LobbySlotDTO(BaseModel):
    index: int
    is_empty: bool = True
    character_id: str | None = None
    name: str | None = None
    avatar_url: str | None = None
    status: str = "VACANT"
    presence_status: Literal["online", "offline"] = "offline"
    location_id: str | None = None
    updated_at: datetime | None = None
    vitals: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, int] = Field(default_factory=dict)
    equipped_items: list[CharacterSummaryItemDTO] = Field(default_factory=list)
    inventory_summary: CharacterInventorySummaryDTO = Field(default_factory=CharacterInventorySummaryDTO)
    skills: list[CharacterSummarySkillDTO] = Field(default_factory=list)


class GameLobbyPayloadDTO(BaseModel):
    title: str = "Порог"
    description: str = "Врата молчат. Начни путь, когда будешь готов создать нового персонажа."
    primary_action_label: str = "Начать приключение"
    primary_action: str = "start_adventure"
    message: str | None = None
    max_slots: int = 4
    can_start: bool = True
    slots: list[LobbySlotDTO] = Field(default_factory=list)

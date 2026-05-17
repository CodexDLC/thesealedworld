from typing import Literal
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


class GameLobbyPayloadDTO(BaseModel):
    title: str = "Порог"
    description: str = "Врата молчат. Начни путь, когда будешь готов создать нового персонажа."
    primary_action_label: str = "Начать приключение"
    primary_action: str = "start_adventure"
    message: str | None = None
    max_slots: int = 4
    can_start: bool = True
    slots: list[LobbySlotDTO] = Field(default_factory=list)

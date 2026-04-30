from typing import Literal

from pydantic import BaseModel, Field, field_validator

CharacterCreationGender = Literal["male", "female", "other"]


class CreateCharacterRequestDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=32)
    gender: CharacterCreationGender
    avatar: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Character name cannot be empty")
        return name


class EnterCharacterRequestDTO(BaseModel):
    character_id: int


class DeleteCharacterRequestDTO(BaseModel):
    character_id: int
    confirm_name: str = Field(..., min_length=1, max_length=32)

    @field_validator("confirm_name")
    @classmethod
    def normalize_confirm_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Character confirmation name cannot be empty")
        return name


class LobbySlotDTO(BaseModel):
    index: int
    is_empty: bool = True
    character_id: str | None = None
    name: str | None = None
    avatar_url: str | None = None
    status: str = "VACANT"


class GameLobbyPayloadDTO(BaseModel):
    title: str = "The Threshold"
    description: str = "The neural gate is quiet. Begin the journey when you are ready to shape a new vessel."
    primary_action_label: str = "Начать приключение"
    primary_action: str = "start_adventure"
    message: str | None = None
    max_slots: int = 4
    can_start: bool = True
    slots: list[LobbySlotDTO] = Field(default_factory=list)

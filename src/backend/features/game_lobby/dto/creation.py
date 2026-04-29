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


class ScenarioPlaceholderPayloadDTO(BaseModel):
    message: str = "Scenario awakening_rift not wired yet"
    quest_key: str = "awakening_rift"

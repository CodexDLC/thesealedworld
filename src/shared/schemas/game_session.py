from __future__ import annotations

from pydantic import BaseModel, Field


class StartingImprintOptionDTO(BaseModel):
    imprint_key: str
    title: str
    description: str = ""


class StartingImprintOptionsDTO(BaseModel):
    imprints: list[StartingImprintOptionDTO] = Field(default_factory=list)


class DevStarterRiftResetRequestDTO(BaseModel):
    character_id: int
    imprint_key: str

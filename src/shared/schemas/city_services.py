from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CityServiceScreenEnum(StrEnum):
    MAIN = "main"
    SECTION = "section"


class CityServiceActionEnum(StrEnum):
    MENU_MAIN = "menu_main"
    OPEN_SECTION = "open_section"
    START_DIALOGUE = "start_dialogue"
    REST = "rest"
    LEAVE = "leave"
    PLACEHOLDER = "placeholder"


class CityServiceSectionDTO(BaseModel):
    id: str
    title: str
    description: str | None = None
    icon: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CityServiceButtonDTO(BaseModel):
    label: str
    action: CityServiceActionEnum
    icon: str | None = None
    section_id: str | None = None
    is_disabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class CityServiceUIPayloadDTO(BaseModel):
    service_id: str
    service_type: str
    location_id: str | None = None
    screen: CityServiceScreenEnum
    section_id: str | None = None
    title: str
    description: str
    background_url: str | None = None
    sections: list[CityServiceSectionDTO] = Field(default_factory=list)
    buttons: list[CityServiceButtonDTO] = Field(default_factory=list)
    notice: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CityServiceActionDTO(BaseModel):
    action: CityServiceActionEnum
    service_id: str
    screen: CityServiceScreenEnum | None = None
    section_id: str | None = None
    location_id: str | None = None
    value: dict[str, Any] | None = None

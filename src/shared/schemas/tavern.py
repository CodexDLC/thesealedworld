from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TavernScreenEnum(StrEnum):
    MAIN = "main"
    BAR = "bar"
    ROOM = "room"
    COMMON_HALL = "common_hall"


class TavernActionEnum(StrEnum):
    MENU_MAIN = "menu_main"
    GO_BAR = "go_bar"
    GO_ROOMS = "go_rooms"
    GO_COMMON_HALL = "go_common_hall"
    TALK_BARTENDER = "talk_bartender"
    REST = "rest"
    LEAVE = "leave"


class TavernButtonDTO(BaseModel):
    label: str
    action: TavernActionEnum
    icon: str | None = None
    is_disabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class TavernRoomDTO(BaseModel):
    tavern_id: str
    room_key: str | None = None
    status: str = "unclaimed"
    is_owned: bool = False
    can_rest: bool = False


class TavernCommonHallDTO(BaseModel):
    title: str = "Общий зал"
    occupants_count: int = 0
    group_requests: list[dict[str, Any]] = Field(default_factory=list)
    notices: list[dict[str, Any]] = Field(default_factory=list)


class TavernBarDTO(BaseModel):
    bartender_key: str = "last_refuge_bartender"
    dialogue_quest_key: str = "tavern_bartender_dialogue"


class TavernUIPayloadDTO(BaseModel):
    tavern_id: str
    service_id: str
    location_id: str | None = None
    screen: TavernScreenEnum
    title: str
    description: str
    buttons: list[TavernButtonDTO] = Field(default_factory=list)
    bar: TavernBarDTO | None = None
    room: TavernRoomDTO | None = None
    common_hall: TavernCommonHallDTO | None = None
    notice: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TavernActionDTO(BaseModel):
    action: TavernActionEnum
    screen: TavernScreenEnum | None = None
    tavern_id: str | None = None
    service_id: str | None = None
    location_id: str | None = None
    value: dict[str, Any] | None = None

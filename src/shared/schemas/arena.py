from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ArenaActionEnum(StrEnum):
    MENU_MAIN = "MENU_MAIN"
    MENU_MODE = "MENU_MODE"
    JOIN_QUEUE = "JOIN_QUEUE"
    CHECK_MATCH = "CHECK_MATCH"
    ACCEPT_SHADOW = "ACCEPT_SHADOW"
    CONTINUE_SEARCH = "CONTINUE_SEARCH"
    CHECK_COMBAT_READY = "CHECK_COMBAT_READY"
    CANCEL_QUEUE = "CANCEL_QUEUE"
    LEAVE = "LEAVE"


class ArenaModeEnum(StrEnum):
    ONE_VS_ONE = "one_vs_one"
    GROUP = "group"
    TOURNAMENT = "tournament"


class ArenaScreenEnum(StrEnum):
    MAIN_MENU = "main_menu"
    MODE_MENU = "mode_menu"
    SEARCHING = "searching"
    SHADOW_OFFER = "shadow_offer"
    COMBAT_PENDING = "combat_pending"
    COMBAT_FAILED = "combat_failed"


class ArenaButtonDTO(BaseModel):
    text: str
    action: ArenaActionEnum | str
    mode: ArenaModeEnum | str | None = None
    value: dict[str, Any] | None = None
    variant: str | None = None


class ArenaActionDTO(BaseModel):
    action: ArenaActionEnum | str
    mode: ArenaModeEnum | str | None = None
    value: dict[str, Any] | None = None


class ArenaUIPayloadDTO(BaseModel):
    screen: ArenaScreenEnum | str
    title: str
    description: str
    mode: ArenaModeEnum | str | None = None
    arena_session_id: str | None = None
    combat_id: str | None = None
    gs: int | None = None
    wait_time_sec: int = 0
    poll_after_ms: int = 1000
    timeout_sec: int = 60
    buttons: list[ArenaButtonDTO] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

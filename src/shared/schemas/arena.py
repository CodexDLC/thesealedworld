from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# --- Enums ---


class ArenaScreenEnum(StrEnum):
    """Экраны арены."""

    MAIN_MENU = "main_menu"
    MODE_MENU = "mode_menu"
    SEARCHING = "searching"
    MATCH_FOUND = "match_found"
    SHADOW_OFFER = "shadow_offer"
    COMBAT_PENDING = "combat_pending"
    COMBAT_FAILED = "combat_failed"


class ArenaModeEnum(StrEnum):
    """Режимы арены."""

    ONE_VS_ONE = "one_vs_one"
    GROUP = "group"
    TOURNAMENT = "tournament"


class ArenaActionEnum(StrEnum):
    """Действия на арене."""

    MENU_MAIN = "menu_main"
    MENU_MODE = "menu_mode"
    JOIN_QUEUE = "join_queue"
    START_SHADOW = "start_shadow"
    CHECK_MATCH = "check_match"
    ACCEPT_SHADOW = "accept_shadow"
    CONTINUE_SEARCH = "continue_search"
    CHECK_COMBAT_READY = "check_combat_ready"
    CANCEL_QUEUE = "cancel_queue"
    LEAVE = "leave"
    START_BATTLE = "start_battle"


# --- DTOs ---


class ArenaJsonDTO(BaseModel):
    model_config = ConfigDict(extra="allow")


class ArenaButtonDTO(ArenaJsonDTO):
    """Кнопка интерфейса."""

    text: str
    action: str
    mode: str | None = None
    value: dict[str, Any] | str | None = None
    variant: str | None = None


ButtonDTO = ArenaButtonDTO


class ArenaUIPayloadDTO(ArenaJsonDTO):
    """Данные для отрисовки UI арены."""

    screen: ArenaScreenEnum
    mode: str | None = None
    title: str
    description: str
    buttons: list[ArenaButtonDTO] = Field(default_factory=list)

    # Optional fields
    gs: int | None = None
    opponent_name: str | None = None
    is_shadow: bool = False
    wait_time_sec: int | None = None
    poll_after_ms: int = 1000
    arena_session_id: str | None = None
    combat_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArenaActionDTO(ArenaJsonDTO):
    """Действие игрока на арене."""

    action: str
    mode: str | None = None
    value: Any | None = None

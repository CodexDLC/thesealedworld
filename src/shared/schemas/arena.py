from enum import Enum
from typing import Any

from pydantic import BaseModel

# --- Enums ---


class ArenaScreenEnum(str, Enum):
    """Экраны арены."""

    MAIN_MENU = "main_menu"
    MODE_MENU = "mode_menu"
    SEARCHING = "searching"
    MATCH_FOUND = "match_found"


class ArenaModeEnum(str, Enum):
    """Режимы арены."""

    ONE_VS_ONE = "1v1"
    GROUP = "group"
    TOURNAMENT = "tournament"


class ArenaActionEnum(str, Enum):
    """Действия на арене."""

    MENU_MAIN = "menu_main"
    MENU_MODE = "menu_mode"
    JOIN_QUEUE = "join_queue"
    CHECK_MATCH = "check_match"
    CANCEL_QUEUE = "cancel_queue"
    LEAVE = "leave"
    START_BATTLE = "start_battle"


# --- DTOs ---


class ButtonDTO(BaseModel):
    """Кнопка интерфейса."""

    text: str
    action: str
    mode: str | None = None
    value: str | None = None


class ArenaUIPayloadDTO(BaseModel):
    """Данные для отрисовки UI арены."""

    screen: ArenaScreenEnum
    mode: str | None = None
    title: str
    description: str
    buttons: list[ButtonDTO]

    # Optional fields
    gs: int | None = None
    opponent_name: str | None = None
    is_shadow: bool = False


class ArenaActionDTO(BaseModel):
    """Действие игрока на арене."""

    action: str
    mode: str | None = None
    value: Any | None = None

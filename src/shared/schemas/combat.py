from pydantic import BaseModel


class CombatLogEntryDTO(BaseModel):
    """Одна запись лога."""

    text: str
    timestamp: float
    tags: list[str] = []


class ActorShortInfo(BaseModel):
    """Минимальная инфа для списков"""

    char_id: int
    name: str
    hp_percent: int
    is_dead: bool
    is_target: bool = False  # Выделение в списке


class ActorFullInfo(BaseModel):
    """Полная инфа для Hero и Target"""

    char_id: int
    name: str
    team: str
    is_dead: bool

    # Строка 1
    hp_current: int
    hp_max: int
    energy_current: int
    energy_max: int

    # Для кнопок
    weapon_type: str  # "sword", "bow", "staff" (из main_hand)

    # Строка 2 (Tokens)
    # Суммарные токены (свободные + замороженные в руке)
    tokens: dict[str, int]  # {"tactics": 5, "gift": 1}

    # Строка 3 (Status)
    effects: list[str]  # ["burn", "stun"] (ID иконок)

    # Строка 4 (Feints Hand)
    feints: dict[str, str] = {}  # {"sand_throw": "Бросок песка"}


class CombatDashboardDTO(BaseModel):
    """Полный снимок экрана боя."""

    turn_number: int
    status: str  # active / waiting / finished

    # Блок 1: Я
    hero: ActorFullInfo

    # Блок 2: Цель (если есть)
    target: ActorFullInfo | None = None

    # Блок 3: Списки (для контекста)
    allies: list[ActorShortInfo]
    enemies: list[ActorShortInfo]

    winner_team: str | None = None


class CombatLogDTO(BaseModel):
    """Логи с пагинацией."""

    logs: list[CombatLogEntryDTO]
    total: int
    page: int

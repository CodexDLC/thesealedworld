from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CombatJsonDTO(BaseModel):
    """Loose browser combat contract while the final DTO shape is being calibrated."""

    model_config = ConfigDict(extra="allow")


class CombatLogEntryDTO(CombatJsonDTO):
    """Одна запись лога."""

    text: str
    timestamp: float
    tags: list[str] = []


class CombatRegisterMoveRequestDTO(CombatJsonDTO):
    action: str = "exchange"
    target_id: str | int | None = None
    ability_id: str | None = None
    skill_id: str | None = None
    feint_id: str | None = None
    item_id: str | int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class CombatEventDTO(CombatJsonDTO):
    type: str = "log"
    text: str | None = "NO_DATA"
    timestamp: int | float | None = None
    tags: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


class CombatDeltaDTO(CombatJsonDTO):
    events: list[CombatEventDTO] = Field(default_factory=list)


class CombatActorVitalsDTO(CombatJsonDTO):
    hp_current: int = 0
    hp_max: int = 1
    energy_current: int = 0
    energy_max: int = 1
    tactics: int = 0


class CombatEffectBadgeDTO(CombatJsonDTO):
    uid: str | None = None
    effect_id: str = "NO_DATA"
    expires_at_exchange: int | None = None
    impact: dict[str, Any] = Field(default_factory=dict)


class CombatAbilityBadgeDTO(CombatJsonDTO):
    uid: str | None = None
    ability_id: str = "NO_DATA"
    expires_at_exchange: int | None = None
    impact: dict[str, Any] = Field(default_factory=dict)


class CombatFeintOptionDTO(CombatJsonDTO):
    feint_id: str = "NO_DATA"
    cost: dict[str, int] = Field(default_factory=dict)


class CombatActionOptionDTO(CombatJsonDTO):
    action: str = "system"
    label: str = "NO_DATA"
    enabled: bool = True
    target_id: str | None = None
    ability_id: str | None = None
    feint_id: str | None = None
    catalog_ref: str | None = None
    reason: str | None = None


class CombatActorCardDTO(CombatJsonDTO):
    actor_id: str = "NO_DATA"
    name: str = "NO_DATA"
    actor_type: str = "unknown"
    team: str = "neutral"
    avatar_url: str | None = None
    gear_score: int | None = None
    power_score: int | None = None
    is_ai: bool = False
    is_dead: bool = False
    is_target: bool = False
    exchange_counter: int = 0
    target_queue_size: int = 0
    pending_actions: dict[str, int] = Field(default_factory=dict)
    vitals: CombatActorVitalsDTO = Field(default_factory=CombatActorVitalsDTO)
    weapon_type: str | None = None
    quick_items: list[dict[str, Any]] = Field(default_factory=list)
    known_abilities: list[str] = Field(default_factory=list)
    tokens: dict[str, int] = Field(default_factory=dict)
    active_effects: list[CombatEffectBadgeDTO] = Field(default_factory=list)
    active_abilities: list[CombatAbilityBadgeDTO] = Field(default_factory=list)
    feints: list[CombatFeintOptionDTO] = Field(default_factory=list)


class ActorShortInfo(CombatJsonDTO):
    """Минимальная инфа для списков"""

    char_id: int
    name: str
    hp_percent: int
    is_dead: bool
    is_target: bool = False  # Выделение в списке


class ActorFullInfo(CombatJsonDTO):
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


class CombatDashboardDTO(CombatJsonDTO):
    """Полный снимок экрана боя."""

    session_id: str = "NO_DATA"
    turn_number: int = 0
    status: str = "waiting"
    phase: str | None = None
    battle_type: str | None = None
    location_id: str | None = None
    personal_turn_number: int | None = None
    round_size: int | None = None
    action_state: str = "NO_DATA"
    target_queue_size: int = 0
    pending_action_count: int = 0
    hero: CombatActorCardDTO = Field(default_factory=CombatActorCardDTO)
    target: CombatActorCardDTO | None = None
    allies: list[CombatActorCardDTO] = Field(default_factory=list)
    enemies: list[CombatActorCardDTO] = Field(default_factory=list)
    active_effects: list[CombatEffectBadgeDTO] = Field(default_factory=list)
    feints: list[CombatFeintOptionDTO] = Field(default_factory=list)
    available_actions: list[CombatActionOptionDTO] = Field(default_factory=list)
    events_delta: CombatDeltaDTO = Field(default_factory=CombatDeltaDTO)
    log_total: int = 0
    winner_team: str | None = None


class CombatResultActionDTO(CombatJsonDTO):
    """Browser action suggested after combat result resolution."""

    label: str = "Понятно"
    action: str = "close"
    target_state: str | None = None


class CombatResultDTO(CombatJsonDTO):
    """Archived or recovered combat result shown when live runtime state is unavailable."""

    combat_id: str | None = None
    char_id: int
    status: str = "archive_pending"
    outcome: str = "unknown"
    title: str = "Итоги боя"
    message: str = "Боевая сессия уже завершена или недоступна."
    summary: str = (
        "Архив результатов боя еще не подключен. Итог будет восстановлен из архива после внедрения хранилища."
    )
    reason: str = "combat_session_not_found"
    archived: bool = False
    rewards: dict[str, Any] = Field(default_factory=dict)
    injuries: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    primary_action: CombatResultActionDTO = Field(default_factory=CombatResultActionDTO)


class CombatLogDTO(CombatJsonDTO):
    """Логи с пагинацией."""

    session_id: str = "NO_DATA"
    entries: list[CombatEventDTO] = Field(default_factory=list)
    logs: list[CombatLogEntryDTO] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20

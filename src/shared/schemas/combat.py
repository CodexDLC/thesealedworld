from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CombatJsonDTO(BaseModel):
    """Loose browser combat contract while the final DTO shape is being calibrated."""

    model_config = ConfigDict(extra="allow")


class CombatErrorDTO(CombatJsonDTO):
    """Structured combat API error for frontend branching."""

    code: str
    message: str
    domain: str = "combat"
    frontend_action: str = "show_message"
    retriable: bool = False
    context: dict[str, Any] = Field(default_factory=dict)


class CombatErrorResponseDTO(CombatJsonDTO):
    error: CombatErrorDTO


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


class CombatPinFeintRequestDTO(CombatJsonDTO):
    feint_id: str | None = None


class CombatLogActorRefDTO(CombatJsonDTO):
    id: str
    name: str
    team: str | None = None
    actor_type: str | None = None


class CombatLogActionRefDTO(CombatJsonDTO):
    mode: str = "exchange"
    id: str | None = None
    catalog: str | None = None
    catalog_key: str | None = None
    event: str | None = None
    taxonomy: str = "humanoid"


class CombatLogTemplateRefDTO(CombatJsonDTO):
    key: str | None = None
    event: str | None = None
    taxonomy: str = "humanoid"
    variant: int = 0
    text: str | None = None


class CombatLogPublicResourceDTO(CombatJsonDTO):
    actor_id: str | None = None
    resource: str
    before: int | None = None
    after: int
    max: int
    delta: int | None = None
    label: str | None = None


class CombatLogPublicTokenDTO(CombatJsonDTO):
    actor_id: str | None = None
    owner: str
    token: str
    amount: int
    icon: str | None = None
    tooltip: str | None = None


class CombatLogPublicEffectDTO(CombatJsonDTO):
    actor_id: str | None = None
    owner: str
    effect_id: str
    action: str
    duration: int | None = None
    icon: str | None = None
    tooltip: str | None = None


class CombatLogPublicResultDTO(CombatJsonDTO):
    resources: list[CombatLogPublicResourceDTO] = Field(default_factory=list)
    tokens: list[CombatLogPublicTokenDTO] = Field(default_factory=list)
    effects: list[CombatLogPublicEffectDTO] = Field(default_factory=list)


class CombatLogBadgeDTO(CombatJsonDTO):
    kind: str
    value: int | float | None = None
    resource: str | None = None
    direction: str | None = None


class CombatExchangeStateDTO(CombatJsonDTO):
    """Compact combat exchange state for the central battle viewport."""

    pair_status: str = "unknown"
    opponent_response_state: str = "unknown"
    title: str = "COMBAT"
    summary_text: str = "Бой начался. Противники выбирают позицию для первого размена."
    turn: int | None = None
    source: CombatLogActorRefDTO | None = None
    target: CombatLogActorRefDTO | None = None
    outcome: str | None = None
    badges: list[CombatLogBadgeDTO] = Field(default_factory=list)


class CombatEventDTO(CombatJsonDTO):
    type: str = "log"
    id: str | None = None
    kind: str = "log"
    text: str | None = "NO_DATA"
    severity: str = "normal"
    timestamp: int | float | None = None
    tags: list[str] = Field(default_factory=list)
    source: CombatLogActorRefDTO | None = None
    target: CombatLogActorRefDTO | None = None
    action: CombatLogActionRefDTO | None = None
    template: CombatLogTemplateRefDTO | None = None
    outcome: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    result: CombatLogPublicResultDTO = Field(default_factory=CombatLogPublicResultDTO)
    resources: list[CombatLogPublicResourceDTO] = Field(default_factory=list)
    badges: list[CombatLogBadgeDTO] = Field(default_factory=list)
    effects: list[dict[str, Any]] = Field(default_factory=list)
    flags: dict[str, bool] = Field(default_factory=dict)
    data: dict[str, Any] = Field(default_factory=dict)


class CombatLogTurnDTO(CombatJsonDTO):
    global_turn: int | None = None
    title: str = "Ход NO_DATA"
    entries: list[CombatEventDTO] = Field(default_factory=list)


class CombatDeltaDTO(CombatJsonDTO):
    events: list[CombatEventDTO] = Field(default_factory=list)
    turns: list[CombatLogTurnDTO] = Field(default_factory=list)


class CombatActorVitalsDTO(CombatJsonDTO):
    hp_current: int = 0
    hp_max: int = 1
    energy_current: int = 0
    energy_max: int = 1
    stamina_current: int = 0
    stamina_max: int = 1
    tactics: int = 0


class CombatEffectBadgeDTO(CombatJsonDTO):
    uid: str | None = None
    effect_id: str = "NO_DATA"
    expires_at_exchange: int | None = None
    impact: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    title: str | None = None
    description: str | None = None
    duration_label: str | None = None


class CombatAbilityBadgeDTO(CombatJsonDTO):
    uid: str | None = None
    ability_id: str = "NO_DATA"
    expires_at_exchange: int | None = None
    impact: dict[str, Any] = Field(default_factory=dict)


class CombatFeintOptionDTO(CombatJsonDTO):
    feint_id: str = "NO_DATA"
    cost: dict[str, int] = Field(default_factory=dict)
    pinned: bool = False
    purchase_group: str = "basic"
    icon: str = ""


class CombatActionOptionDTO(CombatJsonDTO):
    action: str = "system"
    label: str = "NO_DATA"
    enabled: bool = True
    target_id: str | None = None
    ability_id: str | None = None
    feint_id: str | None = None
    catalog_ref: str | None = None
    reason: str | None = None


class CombatStatValueDTO(CombatJsonDTO):
    key: str
    label: str
    value: int | float
    value_text: str
    tooltip: str | None = None


class CombatStatSectionDTO(CombatJsonDTO):
    key: str
    label: str
    items: list[CombatStatValueDTO] = Field(default_factory=list)


class CombatActorStatSheetDTO(CombatJsonDTO):
    actor_id: str
    name: str
    sections: list[CombatStatSectionDTO] = Field(default_factory=list)
    total_count: int = 0


class CombatActorCardDTO(CombatJsonDTO):
    actor_id: str = "NO_DATA"
    name: str = "NO_DATA"
    actor_type: str = "unknown"
    team: str = "neutral"
    avatar_url: str | None = None
    archetype: str | None = None
    role: str | None = None
    template_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: dict[str, Any] = Field(default_factory=dict)
    visual: dict[str, Any] = Field(default_factory=dict)
    gear_score: int | None = None
    power_score: int | None = None
    is_ai: bool = False
    is_dead: bool = False
    is_target: bool = False
    committed: bool = False
    commit_state: str = "idle"
    timeout_total_ms: int | None = None
    remaining_ms: int | None = None
    force_attack_at_ms: int | None = None
    exchange_counter: int = 0
    target_queue_size: int = 0
    pending_actions: dict[str, int] = Field(default_factory=dict)
    vitals: CombatActorVitalsDTO = Field(default_factory=CombatActorVitalsDTO)
    weapon_type: str | None = None
    quick_items: list[dict[str, Any]] = Field(default_factory=list)
    known_abilities: list[str] = Field(default_factory=list)
    ability_cooldowns: dict[str, int] = Field(default_factory=dict)
    tokens: dict[str, int] = Field(default_factory=dict)
    active_effects: list[CombatEffectBadgeDTO] = Field(default_factory=list)
    active_abilities: list[CombatAbilityBadgeDTO] = Field(default_factory=list)
    feints: list[CombatFeintOptionDTO] = Field(default_factory=list)
    stat_sheet: CombatActorStatSheetDTO | None = None


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
    exchange_state: CombatExchangeStateDTO | None = None
    events_delta: CombatDeltaDTO = Field(default_factory=CombatDeltaDTO)
    log_total: int = 0
    winner_team: str | None = None


class CombatResultActionDTO(CombatJsonDTO):
    """Browser action suggested after combat result resolution."""

    label: str = "Понятно"
    action: str = "close"
    target_state: str | None = None


class PostCombatLootItemDTO(CombatJsonDTO):
    item_id: str
    template_id: str
    name: str
    rarity: str = "common"
    amount: int = 1
    source: str | None = None
    instance_id: str | None = None
    is_resource: bool = False


class PostCombatLootCorpseDTO(CombatJsonDTO):
    corpse_id: str
    name: str
    corpse_type: str = "monster"
    items: list[PostCombatLootItemDTO] = Field(default_factory=list)


class PostCombatOutcomeDTO(CombatJsonDTO):
    char_id: int
    outcome: str
    target_state: str
    return_state: str | None = None
    notice: str | None = None
    combat_id: str | None = None
    corpse_ids: list[str] = Field(default_factory=list)
    loot_context: dict[str, Any] = Field(default_factory=dict)
    rating_delta: dict[str, Any] | None = None
    death_summary: dict[str, Any] = Field(default_factory=dict)


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
    teams: dict[str, list[str]] = Field(default_factory=dict)
    actors: dict[str, Any] = Field(default_factory=dict)
    report: dict[str, Any] = Field(default_factory=dict)
    rewards: dict[str, Any] = Field(default_factory=dict)
    injuries: dict[str, Any] = Field(default_factory=dict)
    reward_hooks: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    primary_action: CombatResultActionDTO = Field(default_factory=CombatResultActionDTO)


class CombatLogDTO(CombatJsonDTO):
    """Логи с пагинацией."""

    session_id: str = "NO_DATA"
    entries: list[CombatEventDTO] = Field(default_factory=list)
    turns: list[CombatLogTurnDTO] = Field(default_factory=list)
    logs: list[CombatLogEntryDTO] = Field(default_factory=list)
    total_turns: int = 0
    total: int = 0
    page: int = 1
    page_size: int = 20

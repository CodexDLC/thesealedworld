"""
DTO, описывающие Сессию (Session) и Инициализацию.
"""

from typing import Any, NamedTuple

from pydantic import BaseModel, Field

from src.backend.domains.user_features.combat.dto.combat_actor_dto import ActorSnapshot


class SessionDataDTO(NamedTuple):
    """DTO for transferring assembled data to the persistence method."""

    meta: dict[str, Any]
    actors: dict[str, dict[str, Any]]  # final_id -> {key: value} (HASH/JSON fields)
    targets: dict[str, list[str]]  # final_id -> [enemy_id, ...]


class CombatTeamDTO(BaseModel):
    """Описание команды для создания боя."""

    players: list[int] = Field(default_factory=list)
    pets: list[int] = Field(default_factory=list)
    monsters: list[str] = Field(default_factory=list)


class CombatInitContextDTO(BaseModel):
    """Контекст инициализации (передается в CombatInitService)."""

    mode: str = "standard"
    teams: list[CombatTeamDTO]


class BattleMeta(BaseModel):
    """Глобальные счетчики (из Redis :meta)"""

    active: int
    step_counter: int
    active_actors_count: int
    teams: dict[str, list[str | int]]  # ID могут быть int (игроки) или str (монстры)
    winner: str | None = None
    actors_info: dict[str, str] = Field(default_factory=dict)
    dead_actors: list[str | int] = Field(default_factory=list)
    last_activity_at: int = 0
    battle_type: str
    location_id: str


class BattleContext(BaseModel):
    """
    Глобальный контекст сессии в памяти Воркера.
    """

    session_id: str
    meta: BattleMeta
    # Ключи - str, так как JSON ключи всегда строки, и у нас есть монстры с ID "goblin_1"
    actors: dict[str, ActorSnapshot]

    moves_cache: dict[str, dict[str, Any]] = Field(default_factory=dict)
    targets: dict[str, list[int]] = Field(default_factory=dict)
    pending_logs: list[dict] = Field(default_factory=list)

    # NEW: Очередь возврата целей (заполняется в Executor, обрабатывается в DataService)
    pending_target_returns: list[dict[str, int]] = Field(default_factory=list)

    # NEW: Очередь умерших акторов (заполняется в Executor, обрабатывается в DataService)
    pending_dead_actors: list[str | int] = Field(default_factory=list)

    def get_actor(self, char_id: str | int) -> ActorSnapshot | None:
        return self.actors.get(str(char_id))

    def get_enemies(self, char_id: str | int) -> list[ActorSnapshot]:
        me = self.get_actor(char_id)
        if not me:
            return []
        return [a for a in self.actors.values() if a.team != me.meta.team and a.is_alive]


class MechanicsFlagsDTO(BaseModel):
    """
    Мутация стейта (Mechanics Service).
    Управляет тем, какие изменения применяются к акторам.
    """

    pay_cost: bool = True  # Списывать ли энергию/хп за действие
    grant_xp: bool = True  # Начислять ли опыт в буфер
    check_death: bool = True  # Проверять ли смерть после удара
    apply_damage: bool = True  # Наносить ли урон в HP/Shield
    apply_sustain: bool = True  # Считать ли вампиризм/реген
    apply_periodic: bool = False  # Флаг для тиков DoT/HoT
    generate_feints: bool = True  # NEW: Генерировать ли финты (отключать для insta_skill)

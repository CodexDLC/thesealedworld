"""
DTO, описывающие Сессию (Session) и Инициализацию.
"""

from typing import Any, NamedTuple, TypedDict

from pydantic import BaseModel, Field

from src.backend.features.combat.dto.actor import ActorSnapshot
from src.backend.features.combat.dto.ai_memory_dto import AiMemoryDTO
from src.backend.features.combat.dto.ids import ActorId, ActorIdLike


class SessionDataDTO(NamedTuple):
    """DTO for transferring assembled data to the persistence method."""

    meta: dict[str, Any]
    actors: dict[str, dict[str, Any]]  # final_id -> {key: value} (HASH/JSON fields)
    targets: dict[str, list[str]]  # final_id -> [enemy_id, ...]


class TargetReturnDTO(TypedDict):
    """Target queue return pair committed after an exchange."""

    source_id: ActorId
    target_id: ActorId


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
    teams: dict[str, list[ActorIdLike]]  # ID могут быть int (игроки) или str (монстры)
    winner: str | None = None
    actors_info: dict[str, str] = Field(default_factory=dict)
    dead_actors: list[ActorIdLike] = Field(default_factory=list)
    last_activity_at: int = 0
    started_at: int | None = None
    battle_type: str
    location_id: str
    # AI policy artifact id used by all AI actors in this battle. Frozen at
    # battle start from CombatAiConfig.ACTIVE_POLICY_ID; empty string defers
    # to PolicyStore env/default resolution.
    ai_policy_id: str = ""


class BattleContext(BaseModel):
    """
    Глобальный контекст сессии в памяти Воркера.
    """

    session_id: str
    meta: BattleMeta
    # Ключи - str, так как JSON ключи всегда строки, и у нас есть монстры с ID "goblin_1"
    actors: dict[str, ActorSnapshot]

    moves_cache: dict[str, dict[str, Any]] = Field(default_factory=dict)
    targets: dict[ActorId, list[ActorId]] = Field(default_factory=dict)
    pending_logs: list[dict] = Field(default_factory=list)
    pending_result_support_tasks: list[dict[str, Any]] = Field(default_factory=list)

    # NEW: Очередь возврата целей (заполняется в Executor, обрабатывается в DataService)
    pending_target_returns: list[TargetReturnDTO] = Field(default_factory=list)

    # NEW: Очередь умерших акторов (заполняется в Executor, обрабатывается в DataService)
    pending_dead_actors: list[ActorIdLike] = Field(default_factory=list)

    # NEW (PR5): Cross-turn AI memory keyed by actor id. Filled by the
    # executor's post-exchange hook; read by the AI runtime. Reset when the
    # battle session ends. See runtime/ai/ai_memory.py for the contract.
    ai_memory: dict[str, AiMemoryDTO] = Field(default_factory=dict)

    def get_actor(self, char_id: ActorIdLike) -> ActorSnapshot | None:
        return self.actors.get(str(char_id))

    def get_enemies(self, char_id: ActorIdLike) -> list[ActorSnapshot]:
        me = self.get_actor(char_id)
        if not me:
            return []
        return [a for a in self.actors.values() if a.team != me.meta.team and a.is_alive]

    def get_allies(self, char_id: ActorIdLike) -> list[ActorSnapshot]:
        """Live teammates of ``char_id``, excluding the actor itself."""
        me = self.get_actor(char_id)
        if not me:
            return []
        my_id = str(me.meta.id)
        return [a for a in self.actors.values() if a.team == me.meta.team and str(a.meta.id) != my_id and a.is_alive]


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

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from src.backend.infrastructure.game_config.manager import GameConfigManager


@dataclass(frozen=True)
class ExplorationTunables:
    """Snapshot of exploration scalars consumed by encounter policy/services.

    Defaults equal the historical constants from the (now-removed)
    ``features.exploration.dto.config`` module; nothing changes behaviorally
    unless a Redis-backed override is loaded via ``load_exploration_tunables``.
    """

    default_spawn_point: str = "52_52"
    travel_time_mult: float = 1.0
    event_chance_per_step: float = 0.08
    chance_merchant: float = 0.01
    chance_quest: float = 0.02
    chance_combat_base: float = 0.45
    chance_combat_search: float = 0.80
    encounter_base_chance: float = 0.15
    encounter_weight_base: float = 1.0
    encounter_session_ttl_seconds: int = 30 * 60


DEFAULT_EXPLORATION_TUNABLES = ExplorationTunables()

_active_tunables: ContextVar[ExplorationTunables] = ContextVar(
    "exploration_tunables", default=DEFAULT_EXPLORATION_TUNABLES
)


def current_tunables() -> ExplorationTunables:
    return _active_tunables.get()


@contextmanager
def use_tunables(tunables: ExplorationTunables) -> Iterator[None]:
    token = _active_tunables.set(tunables)
    try:
        yield
    finally:
        _active_tunables.reset(token)


async def load_exploration_tunables(manager: GameConfigManager | None) -> ExplorationTunables:
    """Build an ExplorationTunables snapshot from a GameConfigManager. None → defaults."""
    if manager is None:
        return DEFAULT_EXPLORATION_TUNABLES
    d = DEFAULT_EXPLORATION_TUNABLES
    return ExplorationTunables(
        default_spawn_point=await manager.get_str("exploration", "DEFAULT_SPAWN_POINT", default=d.default_spawn_point),
        travel_time_mult=await manager.get_float("exploration", "TRAVEL_TIME_MULT", default=d.travel_time_mult),
        event_chance_per_step=await manager.get_float(
            "exploration", "EVENT_CHANCE_PER_STEP", default=d.event_chance_per_step
        ),
        chance_merchant=await manager.get_float("exploration", "CHANCE_MERCHANT", default=d.chance_merchant),
        chance_quest=await manager.get_float("exploration", "CHANCE_QUEST", default=d.chance_quest),
        chance_combat_base=await manager.get_float("exploration", "CHANCE_COMBAT_BASE", default=d.chance_combat_base),
        chance_combat_search=await manager.get_float(
            "exploration", "CHANCE_COMBAT_SEARCH", default=d.chance_combat_search
        ),
        encounter_base_chance=await manager.get_float(
            "exploration", "ENCOUNTER_BASE_CHANCE", default=d.encounter_base_chance
        ),
        encounter_weight_base=await manager.get_float(
            "exploration", "ENCOUNTER_WEIGHT_BASE", default=d.encounter_weight_base
        ),
        encounter_session_ttl_seconds=await manager.get_int(
            "exploration",
            "ENCOUNTER_SESSION_TTL_SECONDS",
            default=d.encounter_session_ttl_seconds,
        ),
    )

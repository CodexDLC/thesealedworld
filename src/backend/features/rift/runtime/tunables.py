from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

    from src.backend.infrastructure.game_config.manager import GameConfigManager


DEFAULT_TRANSITION_OPENING_CONTEXT: dict[str, Any] = {
    "status": "contract_placeholder",
    "applies_to": [
        "rift_transition_combat",
        "future_world_travel_combat",
    ],
    "default_result": "neutral_opening",
    "possible_results": [
        "neutral_opening",
        "player_advantage",
        "enemy_advantage",
        "ambush_detected",
        "bad_position",
    ],
    "skill_hooks": [
        {
            "skill_key": "skill_scouting",
            "result_bias": [
                "ambush_detected",
                "player_advantage",
            ],
            "future_effects": [],
            "notes": "Scouting improves the opening state, it does not lower the chance of combat.",
        },
        {
            "skill_key": "skill_pathfinder",
            "result_bias": [
                "player_advantage",
            ],
            "future_effects": [],
            "notes": "Pathfinder can improve route position before contact.",
        },
        {
            "skill_key": "skill_hunting",
            "result_bias": [
                "ambush_detected",
                "player_advantage",
            ],
            "future_effects": [],
            "notes": "Hunting can expose tracks and movement lines.",
        },
        {
            "skill_key": "skill_adaptation",
            "result_bias": [
                "neutral_opening",
            ],
            "future_effects": [],
            "notes": "Adaptation can reduce terrain penalties in later combat integration.",
        },
        {
            "skill_key": "skill_tactics",
            "result_bias": [
                "player_advantage",
            ],
            "future_effects": [],
            "notes": "Tactics can convert detected contact into a better first exchange.",
        },
    ],
}


@dataclass(frozen=True)
class RiftTunables:
    transition_base_chance_per_tick: float = 0.35
    transition_tick_interval_ms: int = 1000
    transition_exploration_duration_ms: int = 3000
    transition_return_duration_ms: int = 1000
    transition_suppress_ordinary_after_combat: bool = True
    ordinary_node_combat_enabled: bool = True
    ordinary_node_first_visit_only: bool = True
    ordinary_node_combat_chance: float = 0.30
    transition_opening_context: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_TRANSITION_OPENING_CONTEXT))


DEFAULT_RIFT_TUNABLES = RiftTunables()

_active_tunables: ContextVar[RiftTunables] = ContextVar("rift_tunables", default=DEFAULT_RIFT_TUNABLES)


def current_tunables() -> RiftTunables:
    return _active_tunables.get()


@contextmanager
def use_tunables(tunables: RiftTunables) -> Iterator[None]:
    token = _active_tunables.set(tunables)
    try:
        yield
    finally:
        _active_tunables.reset(token)


async def load_rift_tunables(manager: GameConfigManager | None) -> RiftTunables:
    if manager is None:
        return DEFAULT_RIFT_TUNABLES
    d = DEFAULT_RIFT_TUNABLES
    return RiftTunables(
        transition_base_chance_per_tick=await manager.get_float(
            "rift",
            "TRANSITION_BASE_CHANCE_PER_TICK",
            default=d.transition_base_chance_per_tick,
        ),
        transition_tick_interval_ms=await manager.get_int(
            "rift",
            "TRANSITION_TICK_INTERVAL_MS",
            default=d.transition_tick_interval_ms,
        ),
        transition_exploration_duration_ms=await manager.get_int(
            "rift",
            "TRANSITION_EXPLORATION_DURATION_MS",
            default=d.transition_exploration_duration_ms,
        ),
        transition_return_duration_ms=await manager.get_int(
            "rift",
            "TRANSITION_RETURN_DURATION_MS",
            default=d.transition_return_duration_ms,
        ),
        transition_suppress_ordinary_after_combat=await manager.get_bool(
            "rift",
            "TRANSITION_SUPPRESS_ORDINARY_AFTER_COMBAT",
            default=d.transition_suppress_ordinary_after_combat,
        ),
        ordinary_node_combat_enabled=await manager.get_bool(
            "rift",
            "ORDINARY_NODE_COMBAT_ENABLED",
            default=d.ordinary_node_combat_enabled,
        ),
        ordinary_node_first_visit_only=await manager.get_bool(
            "rift",
            "ORDINARY_NODE_FIRST_VISIT_ONLY",
            default=d.ordinary_node_first_visit_only,
        ),
        ordinary_node_combat_chance=await manager.get_float(
            "rift",
            "ORDINARY_NODE_COMBAT_CHANCE",
            default=d.ordinary_node_combat_chance,
        ),
        transition_opening_context=dict(DEFAULT_TRANSITION_OPENING_CONTEXT),
    )

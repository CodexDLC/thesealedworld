"""Factories for in-memory combat simulation state."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from src.backend.features.combat.dto.session import BattleContext, BattleMeta
from src.backend.features.combat.runtime.engine.stats_engine import StatsEngine
from src.backend.features.combat.runtime.simulation.state import InMemoryBattleLimits, InMemoryBattleState

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorSnapshot


class InMemoryBattleFactory:
    """Build simulation BattleContext objects from already assembled actors."""

    @staticmethod
    def from_actors(
        actors: list[ActorSnapshot],
        *,
        session_id: str = "simulation",
        limits: InMemoryBattleLimits | None = None,
        seed: int = 0,
        battle_type: str = "simulation",
        location_id: str = "simulation",
    ) -> InMemoryBattleState:
        teams: dict[str, list[int | str]] = defaultdict(list)
        actor_map: dict[str, ActorSnapshot] = {}
        actors_info: dict[str, str] = {}

        for actor in actors:
            actor_id = str(actor.meta.id)
            teams[str(actor.meta.team)].append(actor_id)
            actor_map[actor_id] = actor
            actors_info[actor_id] = "ai" if actor.meta.is_ai else "player"

        meta = BattleMeta(
            active=1,
            step_counter=0,
            active_actors_count=sum(1 for actor in actors if actor.is_alive),
            teams=dict(teams),
            actors_info=actors_info,
            battle_type=battle_type,
            location_id=location_id,
        )
        ctx = BattleContext(
            session_id=session_id,
            meta=meta,
            actors=actor_map,
            targets={
                actor.meta.id: [enemy.meta.id for enemy in _sorted_enemy_targets(actors, actor)]
                for actor in actors
                if actor.is_alive
            },  # type: ignore
        )
        return InMemoryBattleState(ctx=ctx, limits=limits or InMemoryBattleLimits(), seed=seed)


def _sorted_enemy_targets(actors: list[ActorSnapshot], actor: ActorSnapshot) -> list[ActorSnapshot]:
    enemies = [enemy for enemy in actors if enemy.meta.team != actor.meta.team and enemy.is_alive]
    return sorted(enemies, key=lambda enemy: (_initiative(enemy), str(enemy.meta.id)))


def _initiative(actor: ActorSnapshot) -> float:
    StatsEngine.ensure_stats(actor)
    if actor.stats is None:
        return 0.0
    return float(actor.stats.mods.initiative or 0.0)

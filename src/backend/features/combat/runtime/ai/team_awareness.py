"""Best-effort awareness of already-committed teammate intents.

The combat session keeps a per-step ``moves_cache`` of payloads other actors
have already registered this turn. When the AI plans for a bot mid-turn,
we can read that cache to bias the bot's decisions toward focus fire and
away from duplicating control effects.

Limits to acknowledge:

* The cache only carries *already committed* intents. Other AI workers may
  be planning in parallel — their decisions won't appear here. This is
  best-effort awareness, not synchronised coordination.
* Player intents are equally visible. The signal is "who in my team is
  attacking whom", not "who am I going to coordinate with explicitly".
* Re-resolving a teammate's feint tags requires the catalog lookup that
  PR1 ``derive_feint_tags`` provides; an unknown feint id contributes
  nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.backend.features.combat.dto.actor import ActorSnapshot  # noqa: TC001
from src.backend.features.combat.dto.session import BattleContext  # noqa: TC001
from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.combat.runtime.ai.feint_tags import derive_feint_tags


@dataclass(frozen=True)
class TeamState:
    """Snapshot of teammate intents already registered this step.

    ``allies_targets`` maps ``target_id`` → count of teammates already
    aimed at that target this step.

    ``allies_pending_control_targets`` is the set of target ids on which a
    teammate has already queued a feint that carries a ``control`` tag —
    queueing another control on the same target this turn is wasted.
    """

    allies_targets: dict[str, int] = field(default_factory=dict)
    allies_pending_control_targets: frozenset[str] = field(default_factory=frozenset)


def extract_team_state(battle: BattleContext | None, bot: ActorSnapshot) -> TeamState:
    """Build a :class:`TeamState` for one bot from a battle context.

    ``battle is None`` or an empty ``moves_cache`` yields the empty state.
    Re-resolves teammate feint ids through the catalog so the control-dedup
    branch can fire even when the cached payload only carries an id.
    """
    if battle is None:
        return TeamState()
    moves_cache = getattr(battle, "moves_cache", None) or {}
    if not moves_cache:
        return TeamState()

    my_team = bot.meta.team
    my_id = str(bot.meta.id)
    targets: dict[str, int] = {}
    control_targets: set[str] = set()

    for actor_id, payload in moves_cache.items():
        if not isinstance(payload, dict):
            continue
        if str(actor_id) == my_id:
            continue
        ally = battle.get_actor(actor_id)
        if ally is None or ally.team != my_team or not ally.is_alive:
            continue

        target_id_raw = payload.get("target_id")
        if target_id_raw is None:
            continue
        target_id = str(target_id_raw)
        targets[target_id] = targets.get(target_id, 0) + 1

        feint_id = payload.get("feint_id")
        if not feint_id:
            continue
        entry = CombatCatalogIntegrator.get_feint_catalog_entry(str(feint_id))
        if entry is None:
            continue
        tags = derive_feint_tags(entry, str(feint_id))
        if "control" in tags:
            control_targets.add(target_id)

    return TeamState(
        allies_targets=targets,
        allies_pending_control_targets=frozenset(control_targets),
    )

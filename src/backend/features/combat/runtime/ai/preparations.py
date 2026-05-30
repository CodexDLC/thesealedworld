"""Catalogued preparation effects, grouped by AI-relevant threat profile.

A preparation is a buff on the source actor that triggers on the *next*
defensive event (incoming hit, dodge, parry). For the scorer there are
three groups that change the value of attacking that target:

* :data:`COUNTER_ON_HIT_PREPS` — attacking this target will provoke a
  counter-attack on a successful defence. Hitting through a counter prep
  costs the attacker an extra reply.
* :data:`DAMAGE_REDUCTION_PREPS` — the next incoming damage is capped or
  halved. Any non-dispelling attack into this prep wastes most of its
  expected damage.
* :data:`FORCED_DEFENCE_PREPS` — the next incoming attack is guaranteed to
  be parried (or otherwise defended). Damage probability drops sharply
  unless the prep is dispelled first.

:data:`HEAL_PREPS` is the bot's own preparation set that already promises
a heal — used to penalise stacking another heal feint on top.

Source of truth: the ``preparation_effects[*].id`` values found in
``src/backend/features/game_catalog/combat/resources/feints/definitions/``.
"""

from __future__ import annotations

from src.backend.features.combat.dto.actor import ActorSnapshot  # noqa: TC001

# Preparations that fire a counter-attack on the *next* successful defence
# the source makes. Attacking this target invites the counter.
COUNTER_ON_HIT_PREPS: frozenset[str] = frozenset(
    {
        "prep_counter_on_dodge",
        "prep_counter_cap_on_dodge",
        "prep_perfect_riposte",
        "prep_2h_answering_stance",
        "prep_2h_closed_distance",
        "prep_2h_hidden_agility",
    }
)

# Preparations that reduce or cap incoming damage on the next hit. The
# attacker still hits, but for vastly reduced output.
DAMAGE_REDUCTION_PREPS: frozenset[str] = frozenset(
    {
        "prep_glancing_dodge",
        "prep_active_defense",
        "prep_full_defense",
        "prep_absolute_defense",
        "prep_aggressive_defense",
    }
)

# Preparations that force a parry / strong defence on the next incoming
# attack. Attacking through one without dispelling is a near-guaranteed miss.
FORCED_DEFENCE_PREPS: frozenset[str] = frozenset(
    {
        "prep_foresight_parry",
        "prep_2h_steel_line",
        "prep_2h_blade_return",
        "prep_2h_hard_intercept",
    }
)

# Preparations on the source that already promise a heal trigger.
HEAL_PREPS: frozenset[str] = frozenset(
    {
        "prep_second_breath",
        "prep_perfect_riposte",
    }
)

# Union of all preps that punish a naive attack (counter, damage cap, or
# forced defence). Tested as one set in the scorer's threat branch.
THREATENING_PREPS: frozenset[str] = COUNTER_ON_HIT_PREPS | DAMAGE_REDUCTION_PREPS | FORCED_DEFENCE_PREPS

_PREP_EFFECT_PREFIX = "prep_"


def extract_preparations(actor: ActorSnapshot) -> frozenset[str]:
    """Return the set of ``prep_*`` effect ids active on the actor.

    Reads ``actor.statuses.effects`` and filters by the ``prep_`` prefix.
    Returns an empty set if statuses are missing.
    """
    statuses = getattr(actor, "statuses", None)
    if statuses is None:
        return frozenset()
    effects = getattr(statuses, "effects", None) or []
    return frozenset(
        str(effect.effect_id)
        for effect in effects
        if effect is not None
        and isinstance(getattr(effect, "effect_id", None), str)
        and effect.effect_id.startswith(_PREP_EFFECT_PREFIX)
    )

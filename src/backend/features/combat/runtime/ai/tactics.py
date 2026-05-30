"""Per-turn tactic selection and policy overlays.

A ``Tactic`` is a short-lived (one turn) mode that biases the bot toward
aggression or defence. It is derived from the bot's current observation
plus its :class:`Archetype` and applied as a multiplicative *overlay*
on top of the loaded :class:`Policy` for the duration of the turn.

Overlays multiply existing weights (see :meth:`Policy.with_overlay`). They
never introduce new keys — that responsibility belongs to the underlying
archetype policy JSON.
"""

from __future__ import annotations

from enum import StrEnum

from src.backend.features.combat.runtime.ai.archetypes import Archetype
from src.backend.features.combat.runtime.ai.observation import SelfObservation  # noqa: TC001


class Tactic(StrEnum):
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    BALANCED = "balanced"


# Multiplicative weight overlays per tactic. Keys must already exist in the
# loaded policy; missing keys are ignored by :meth:`Policy.with_overlay`.
TACTIC_OVERLAYS: dict[Tactic, dict[str, float]] = {
    Tactic.AGGRESSIVE: {
        "expected_damage": 1.4,
        "damage_tag": 1.3,
        "defense": 0.5,
        "heal": 0.4,
        "self_buff": 0.7,
    },
    Tactic.DEFENSIVE: {
        "defense": 1.6,
        "heal": 1.8,
        "self_buff": 1.4,
        "expected_damage": 0.8,
        "prep_threat_penalty": 1.5,
    },
    Tactic.BALANCED: {},
}


def choose_tactic(self_obs: SelfObservation, archetype: Archetype) -> Tactic:
    """Pick the tactic for this turn.

    Rules (transparent thresholds — designers can tune them by adjusting
    the archetype JSON weights rather than editing branches here):

    * Berserker stays aggressive while it can still fight back; only when
      it's almost dead does it fall back to balanced (no defensive mode —
      a berserker doesn't retreat).
    * Bulwark stays defensive at all times.
    * For any other archetype: low HP triggers defensive mode; high HP +
      stamina triggers aggressive; otherwise balanced.
    """
    if archetype is Archetype.BERSERKER:
        return Tactic.BALANCED if self_obs.hp_pct < 0.15 else Tactic.AGGRESSIVE

    if archetype is Archetype.BULWARK:
        return Tactic.DEFENSIVE

    if self_obs.hp_pct < 0.3:
        return Tactic.DEFENSIVE

    if self_obs.hp_pct > 0.7 and self_obs.stamina_pct > 0.5:
        return Tactic.AGGRESSIVE

    return Tactic.BALANCED

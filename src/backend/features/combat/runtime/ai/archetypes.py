"""NPC AI archetypes — coarse personality templates that select a policy.

An archetype is a small string label stored on the actor (``meta.ai_archetype``)
that maps to a bundled policy JSON. Designers attach the label to monster
templates; the runtime loads the matching policy through
:meth:`PolicyStore.load`. Missing or unknown labels fall back to
:attr:`Archetype.BALANCED`, which mirrors the default policy.

The set is intentionally small (5 entries). Each archetype is just a weight
preference, not a behaviour fork — the scoring code path is identical for
all archetypes.
"""

from __future__ import annotations

from enum import StrEnum


class Archetype(StrEnum):
    """Coarse NPC personality template."""

    BERSERKER = "berserker"
    DUELIST = "duelist"
    BULWARK = "bulwark"
    TACTICIAN = "tactician"
    BALANCED = "balanced"

    @classmethod
    def coerce(cls, value: str | None) -> Archetype:
        """Return the matching archetype or :attr:`BALANCED` on unknown input."""
        if value is None:
            return cls.BALANCED
        normalised = str(value).strip().lower()
        if not normalised:
            return cls.BALANCED
        for member in cls:
            if member.value == normalised:
                return member
        return cls.BALANCED


def archetype_policy_filename(archetype: Archetype) -> str:
    """Return the bundled policy filename for an archetype."""
    return f"archetype_{archetype.value}.json"

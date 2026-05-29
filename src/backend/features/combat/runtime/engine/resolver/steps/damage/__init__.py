"""Damage step sub-pipeline (Phase 5 decomposition).

Module-level singleton ``damage_step`` is the entry point. Sub-phases (
``raw_roll``, ``physical``, ``pure``, ``elemental``, ``shield_absorb``,
``final_clamp``, ``damage_event``) are private to the package; if a caller
needs to override one in a test, monkeypatch the function attribute on the
relevant sub-module.
"""

from .damage_step import DamageStep, damage_step

__all__ = ["DamageStep", "damage_step"]

"""Damage state — accumulators threaded through sub-phases.

Slotted dataclass; per-call allocation matches the locals it replaces in the
old monolithic damage step. Sub-phases mutate this in place plus the shared
``InteractionResultDTO`` (``res``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DamageState:
    # Range / roll inputs (filled by raw_roll).
    min_d: float = 0.0
    max_d: float = 0.0
    base: float | None = None
    spread: float | None = None
    raw_damage: float = 0.0
    source_id: str = "0"
    target_id: str = "0"

    # Accumulators.
    total_damage: float = 0.0
    damage_parts: dict[str, float] = field(default_factory=dict)
    elemental_damage_enabled: bool = False
    elemental_damage_before_armor: float = 0.0

    # Physical channel trace fields (also read by damage_event).
    crit_multiplier: float = 1.0
    base_before_physical: float = 0.0
    physical_added: float = 0.0
    mitigation_pct: float = 0.0
    armor_flat: float = 0.0
    armor_trace: dict[str, Any] = field(default_factory=dict)
    phys_res_raw: float = 0.0
    phys_suppression: float = 0.0
    phys_res_suppression_pct: float = 0.0
    after_resist: float = 0.0
    after_armor: float = 0.0

    # Magic-armor mitigation applied after the elemental loop.
    magic_armor_flat: float = 0.0
    magic_after_armor: float = 0.0

    # Shield absorb/reflect for successful blocked-branch contacts.
    shield_absorb: float = 0.0
    shield_reflect: float = 0.0
    shield_reflect_base: float = 0.0
    shield_absorb_ratio: float = 0.0
    shield_absorb_cap: float = 0.0
    shield_guard_power: float = 0.0
    shield_reflect_ratio: float = 0.0
    shield_mastery: float = 0.0

    # Final clamp.
    incoming_damage_cap: int = 0

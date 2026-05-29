"""Support helpers for CombatResolver: stateless leaf functions.

Each submodule contains canonical implementations of resolver helpers.
``CombatResolver`` either delegates to these directly, or — for helpers that
participate in the ``_bonus_token_roll`` monkeypatch chain (token/trigger
grants) — retains a parallel implementation that calls ``cls.`` to honor
existing test patches. Step classes introduced in Phase 4 will call these
canonical support functions directly.

Modules:
- ``trace_writer``       — diagnostic traces (CombatCheckTraceDTO/CombatDamageTraceDTO + loguru bind).
- ``offensive_lookup``   — source-aware stat lookup, accuracy skill bonus.
- ``armor_math``         — armor / resistance / crit-multiplier math.
- ``token_awarder``      — token-grant primitives.
- ``trigger_activator``  — trigger rule dispatch, chance, effect/token application.
"""

from . import (
    armor_math,
    offensive_lookup,
    token_awarder,
    trace_writer,
    trigger_activator,
)

__all__ = [
    "armor_math",
    "offensive_lookup",
    "token_awarder",
    "trace_writer",
    "trigger_activator",
]

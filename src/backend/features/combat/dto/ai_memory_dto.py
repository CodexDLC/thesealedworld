"""DTO for cross-turn AI memory entries stored on BattleContext.

Kept in :mod:`dto` (not :mod:`runtime.ai`) so :class:`BattleContext` can
reference it without triggering the AI runtime's package initialiser
(which transitively imports the brain, scorer, action_space).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AiMemoryDTO(BaseModel):
    """Per-actor rolling memory for one battle session.

    See :mod:`combat.runtime.ai.ai_memory` for the recording API and the
    semantics of each field. The DTO is intentionally small and JSON-clean
    so it survives the normal battle-session serialisation.
    """

    # Recent outcomes when this actor was the defender. Right end is newest.
    defence_outcomes: list[str] = Field(default_factory=list)
    # Recent feints chosen by this actor as attacker. Right end is newest.
    feints_used: list[str] = Field(default_factory=list)
    # Most recent target id this actor aimed at (sticky-focus signal).
    last_target_id: str | None = None

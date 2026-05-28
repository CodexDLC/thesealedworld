"""Runtime combat AI for monster actors.

This package owns the inference path: it converts a `BattleContext` plus a
bot snapshot into a list of payloads compatible with
`CombatTurnManager.register_moves_batch`. Offline training lives in the
sibling `training/` sub-package and shares only the JSON policy contract.
"""

from src.backend.features.combat.runtime.ai.brain import MonsterCombatBrain
from src.backend.features.combat.runtime.ai.policy import Policy
from src.backend.features.combat.runtime.ai.policy_store import PolicyStore

__all__ = ["MonsterCombatBrain", "Policy", "PolicyStore"]

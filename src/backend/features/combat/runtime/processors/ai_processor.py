from typing import Any

from src.backend.features.combat.dto.actor import ActorSnapshot
from src.backend.features.combat.dto.session import BattleContext
from src.backend.features.combat.runtime.ai import MonsterCombatBrain


class AiProcessor:
    """Produce runtime move payloads for NPC-controlled combat actors.

    Backed by :class:`MonsterCombatBrain`: legal actions are scored under a
    JSON-trained policy and finite resources (feint hand, stamina) are
    allocated across per-target intents.

    Both APIs return payloads compatible with
    :meth:`CombatTurnManager.register_moves_batch` — no AI-specific
    contract branch in the combat pipeline.
    """

    def __init__(self, brain: MonsterCombatBrain | None = None) -> None:
        self._brain = brain or MonsterCombatBrain()

    def decide_turn(
        self,
        bot: ActorSnapshot,
        battle: BattleContext,
        candidate_targets: list[ActorSnapshot],
    ) -> list[dict[str, Any]]:
        """Plan all per-target intents for one bot in one shot.

        Args:
            bot: Acting NPC snapshot.
            battle: Full battle context (for alive-enemy count and session-seeded RNG).
            candidate_targets: Targets the bot must produce an intent against.

        Returns:
            One payload per target, in the same order. Each payload is
            ``{"action": "attack", "target_id": ..., "feint_id"?: ...}``.
        """
        return self._brain.decide_turn(bot, battle, candidate_targets)

    def decide_exchange(self, bot: ActorSnapshot, target: ActorSnapshot) -> dict[str, Any]:
        """Single-pair payload (legacy API; preserved for callers and tests)."""
        return self._brain.decide_exchange(bot, target)

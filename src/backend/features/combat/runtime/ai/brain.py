"""High-level inference API for monster combat AI.

The brain is the single entry point used by :class:`AiProcessor`. It does not
mutate any persistent state: ``StatsEngine.ensure_stats`` is called for the
side-effect of materialising ``actor.stats``, which is the same contract the
resolver relies on, but no token, stamina, or feint-hand mutation propagates
outside :class:`CombatTurnManager` / :class:`FeintService`.

Model
-----

Combat is fully asynchronous: each exchange is one (attacker, defender)
pair, resolved independently of the rest of the battle. The brain's primary
API reflects that — :meth:`decide_exchange` produces one payload for one
target, scoring legal actions against that specific defender.

:meth:`decide_turn` exists as a *planning-budget* convenience for callers
that hand the bot a list of pending intents in a single AI task (the
collector typically does this for efficiency). It is a thin sequential
wrapper around :meth:`decide_exchange`: between iterations it mutates a
*local* copy of the bot snapshot so the next exchange sees a realistic
remaining hand and remaining stamina. Without this local mutation the bot
would over-commit stamina across targets — every iteration would see the
same full budget and pick the most expensive feint, the executor would
then run out of stamina and reject half of them.

The local mutation is a *planning* model, not a Redis write: real
deduction happens inside ``CombatTurnManager.register_moves_batch`` /
``FeintService.consume_feint`` / executor, as before.
"""

from __future__ import annotations

import copy
import hashlib
import random
from typing import Any

from src.backend.features.combat.dto.actor import ActorSnapshot  # noqa: TC001
from src.backend.features.combat.dto.session import BattleContext  # noqa: TC001
from src.backend.features.combat.runtime.ai.action_space import build_legal_actions_for_target
from src.backend.features.combat.runtime.ai.observation import extract_self, extract_target
from src.backend.features.combat.runtime.ai.policy import Policy  # noqa: TC001
from src.backend.features.combat.runtime.ai.policy_store import PolicyStore
from src.backend.features.combat.runtime.ai.scorer import PolicyScorer
from src.backend.features.combat.runtime.engine.feint_service import FeintService


class MonsterCombatBrain:
    """Per-exchange inference for a monster actor.

    Primary API: :meth:`decide_exchange` returns one payload for one
    (bot, target) pair. :meth:`decide_turn` is the planning-budget wrapper
    that loops decide_exchange across pending intents, locally accounting
    for the hand-and-stamina depletion that will happen at registration time.
    """

    def __init__(self, policy_store: PolicyStore | None = None, policy: Policy | None = None) -> None:
        self._policy_store = policy_store or PolicyStore()
        self._policy_override = policy

    @property
    def policy(self) -> Policy:
        if self._policy_override is not None:
            return self._policy_override
        return self._policy_store.load()

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def decide_exchange(
        self,
        bot: ActorSnapshot,
        target: ActorSnapshot,
        battle: BattleContext | None = None,
    ) -> dict[str, Any]:
        """Pick one payload for the (bot, target) exchange.

        Reads ``bot.meta.feints.hand`` and ``bot.meta.stamina`` as the
        current planning budget. Selects the legal action with the highest
        policy score. Does not mutate ``bot`` or ``target``.
        """
        alive_enemy_count = self._alive_enemy_count(bot, battle, [target])
        self_obs = extract_self(bot, alive_enemy_count=alive_enemy_count)
        target_obs = extract_target(target)
        policy = self.policy
        rng = random.Random(self._rng_seed(bot, battle, target))

        actions = build_legal_actions_for_target(bot, target)
        if not actions:
            # Defensive: action space always yields at least the basic attack.
            return {"action": "attack", "target_id": str(target.meta.id)}

        best_action = max(
            actions,
            key=lambda action: PolicyScorer.score(self_obs, target_obs, action, policy, rng),
        )
        return best_action.to_payload()

    # ------------------------------------------------------------------
    # Planning-budget wrapper
    # ------------------------------------------------------------------

    def decide_turn(
        self,
        bot: ActorSnapshot,
        battle: BattleContext | None,
        candidate_targets: list[ActorSnapshot],
    ) -> list[dict[str, Any]]:
        """Plan all pending intents in one AI task, respecting a shared budget.

        Iterates ``candidate_targets``, calling :meth:`decide_exchange` for
        each. Between iterations the *local* copy of ``bot`` is mutated:

        * The chosen feint is removed from the hand (it can only be
          consumed once at registration).
        * Its stamina activation cost is subtracted from
          ``bot.meta.stamina`` (the shared budget across all intents in
          this batch).

        The result: the second target sees a realistic remaining hand and
        a remaining stamina pool, so it does not over-commit. The
        original ``bot`` snapshot is left untouched.
        """
        if not candidate_targets:
            return []

        # Plan against a local clone so the caller's snapshot stays clean.
        local_bot = copy.deepcopy(bot)

        payloads: list[dict[str, Any]] = []
        for target in candidate_targets:
            payload = self.decide_exchange(local_bot, target, battle)
            payloads.append(payload)
            self._apply_intent_to_local_state(local_bot, payload)

        return payloads

    # ------------------------------------------------------------------
    # Local planning mutation
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_intent_to_local_state(local_bot: ActorSnapshot, payload: dict[str, Any]) -> None:
        """Simulate the executor's resource debit on the local snapshot.

        Updates the planning-budget view of the bot so subsequent
        :meth:`decide_exchange` calls in the same :meth:`decide_turn`
        iteration see a realistic remaining hand and stamina.

        Hand: pop the consumed feint (it can only be used once per round
        until refill).

        Stamina: subtract the activation cost (shared resource pool across
        all intents in this batch).

        Tokens: untouched — they are already frozen at refill time, and
        the live ``actor.tokens`` already reflects that freeze. We are not
        simulating Redis state, only the AI's view of its remaining budget.
        """
        feint_id = payload.get("feint_id")
        if not feint_id:
            return

        hand = local_bot.meta.feints.hand
        cost = hand.pop(feint_id, None)
        if cost is None:
            return

        stamina_cost = FeintService.activation_stamina_cost(cost)
        local_bot.meta.stamina = max(0, int(local_bot.meta.stamina or 0) - stamina_cost)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _alive_enemy_count(
        bot: ActorSnapshot,
        battle: BattleContext | None,
        fallback_targets: list[ActorSnapshot],
    ) -> int:
        if battle is not None:
            enemies = battle.get_enemies(bot.meta.id)
            if enemies:
                return len(enemies)
        return sum(1 for target in fallback_targets if target.is_alive)

    @staticmethod
    def _rng_seed(
        bot: ActorSnapshot,
        battle: BattleContext | None,
        target: ActorSnapshot | None = None,
    ) -> int:
        """Process-stable RNG seed for one (bot, target, step) decision.

        Uses ``blake2b`` so the same triple always produces the same seed
        across worker restarts and machines. Including the target id makes
        the noise component independent per-pair: two exchanges of the
        same bot in the same step do not share a seed.
        """
        session_id = battle.session_id if battle is not None else "no-session"
        step = battle.meta.step_counter if battle is not None else 0
        target_id = target.meta.id if target is not None else "no-target"
        payload = f"{session_id}|{bot.meta.id}|{target_id}|{step}".encode()
        digest = hashlib.blake2b(payload, digest_size=8).digest()
        return int.from_bytes(digest, "big") & 0xFFFFFFFF


# Re-export for direct typing imports.
__all__ = ["MonsterCombatBrain", "FeintService"]

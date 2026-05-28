"""High-level inference API for monster combat AI.

The brain is the single entry point used by :class:`AiProcessor`. It does not
mutate any snapshot state: ``StatsEngine.ensure_stats`` is called for the
side-effect of materialising ``actor.stats``, which is the same contract the
resolver relies on, but no token, stamina, or feint-hand mutation happens
outside :class:`CombatTurnManager` / :class:`FeintService`.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any

from src.backend.features.combat.dto.actor import ActorSnapshot  # noqa: TC001
from src.backend.features.combat.dto.session import BattleContext  # noqa: TC001
from src.backend.features.combat.runtime.ai.action_space import (
    LegalAction,  # noqa: TC001
    build_legal_actions_for_target,
)
from src.backend.features.combat.runtime.ai.observation import (
    TargetObservation,  # noqa: TC001
    extract_self,
    extract_target,
)
from src.backend.features.combat.runtime.ai.policy import Policy  # noqa: TC001
from src.backend.features.combat.runtime.ai.policy_store import PolicyStore
from src.backend.features.combat.runtime.ai.scorer import PolicyScorer
from src.backend.features.combat.runtime.engine.feint_service import FeintService


class MonsterCombatBrain:
    """One-call inference for a single bot's turn.

    Workflow:

    1. Extract self / per-target observations.
    2. Score every legal action for every target.
    3. Greedily allocate feints from the hand across targets, subject to
       stamina and one-use-per-feint constraints. The most beneficial
       target (largest score delta between best feint action and the basic
       attack) gets first pick.
    4. Emit one payload per target, compatible with
       :meth:`CombatTurnManager.register_moves_batch`.
    """

    def __init__(self, policy_store: PolicyStore | None = None, policy: Policy | None = None) -> None:
        self._policy_store = policy_store or PolicyStore()
        self._policy_override = policy

    @property
    def policy(self) -> Policy:
        if self._policy_override is not None:
            return self._policy_override
        return self._policy_store.load()

    def decide_turn(
        self,
        bot: ActorSnapshot,
        battle: BattleContext | None,
        candidate_targets: list[ActorSnapshot],
    ) -> list[dict[str, Any]]:
        if not candidate_targets:
            return []

        alive_enemy_count = self._alive_enemy_count(bot, battle, candidate_targets)
        self_obs = extract_self(bot, alive_enemy_count=alive_enemy_count)
        policy = self.policy
        rng = random.Random(self._rng_seed(bot, battle))

        scored_per_target: list[tuple[ActorSnapshot, TargetObservation, list[tuple[LegalAction, float]]]] = []
        for target in candidate_targets:
            target_obs = extract_target(target)
            actions = build_legal_actions_for_target(bot, target)
            scored = [(action, PolicyScorer.score(self_obs, target_obs, action, policy, rng)) for action in actions]
            scored_per_target.append((target, target_obs, scored))

        return self._greedy_allocate(bot, scored_per_target)

    def decide_exchange(self, bot: ActorSnapshot, target: ActorSnapshot) -> dict[str, Any]:
        """Legacy single-target API kept for backward compatibility."""
        payloads = self.decide_turn(bot, None, [target])
        if payloads:
            return payloads[0]
        return {"action": "attack", "target_id": str(target.meta.id)}

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
    def _rng_seed(bot: ActorSnapshot, battle: BattleContext | None) -> int:
        """Process-stable RNG seed for the bot's turn.

        Uses ``blake2b`` so the same ``(session_id, bot_id, step)`` triple
        always produces the same seed — across worker restarts and across
        machines. Python's built-in ``hash()`` is randomized via
        ``PYTHONHASHSEED`` and is not stable between processes.
        """
        session_id = battle.session_id if battle is not None else "no-session"
        step = battle.meta.step_counter if battle is not None else 0
        payload = f"{session_id}|{bot.meta.id}|{step}".encode()
        digest = hashlib.blake2b(payload, digest_size=8).digest()
        return int.from_bytes(digest, "big") & 0xFFFFFFFF

    @staticmethod
    def _greedy_allocate(
        bot: ActorSnapshot,
        scored_per_target: list[tuple[ActorSnapshot, TargetObservation, list[tuple[LegalAction, float]]]],
    ) -> list[dict[str, Any]]:
        """Allocate hand feints across targets respecting stamina and uniqueness.

        Each feint in the hand can be used **at most once** in a turn — once it
        is queued against one target, it cannot be queued against another.
        Stamina is the only shared resource between intents (feint tokens are
        already frozen at refill).
        """
        available_stamina = max(0, int(bot.meta.stamina or 0))
        used_feints: set[str] = set()
        plans: list[dict[str, Any]] = []

        # Stable best-attack mapping per target index for the fallback action.
        best_basic_per_target: dict[int, LegalAction] = {}
        # Sorted (target_index, action, score, delta) for greedy picking.
        ranked: list[tuple[int, LegalAction, float, float]] = []

        for idx, (_target, _obs, scored) in enumerate(scored_per_target):
            basic_actions = [item for item in scored if item[0].feint_id is None]
            feint_actions = [item for item in scored if item[0].feint_id is not None]

            if not basic_actions:
                # Defensive: should always include a plain attack.
                continue
            basic_action, basic_score = max(basic_actions, key=lambda item: item[1])
            best_basic_per_target[idx] = basic_action

            for action, score in feint_actions:
                ranked.append((idx, action, score, score - basic_score))

        # Highest delta first; ties broken by raw score (stable & deterministic).
        ranked.sort(key=lambda item: (item[3], item[2]), reverse=True)

        chosen_per_target: dict[int, LegalAction] = {}
        for idx, action, _score, delta in ranked:
            if delta <= 0:
                continue
            if idx in chosen_per_target:
                continue
            if action.feint_id in used_feints:
                continue
            if action.stamina_cost > available_stamina:
                continue
            chosen_per_target[idx] = action
            used_feints.add(action.feint_id or "")
            available_stamina -= action.stamina_cost

        for idx, (_target, _obs, _scored) in enumerate(scored_per_target):
            action = chosen_per_target.get(idx) or best_basic_per_target.get(idx)
            if action is None:
                continue
            plans.append(action.to_payload())

        return plans


# Re-export for direct typing imports.
__all__ = ["MonsterCombatBrain", "FeintService"]

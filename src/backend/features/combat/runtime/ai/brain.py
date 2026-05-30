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
collector typically does this for efficiency). It may emit an instant
ability before an exchange for the same target; instant abilities do not
consume the target queue and do not count as exchanges. Between iterations
it mutates a *local* copy of the bot snapshot so the next decision sees a
realistic remaining hand, stamina, energy, and combat tokens. Without this
local mutation the bot would over-commit resources across targets.

The local mutation is a *planning* model, not a Redis write: real
deduction happens inside ``CombatTurnManager.register_moves_batch`` /
``FeintService.consume_feint`` / executor, as before.
"""

from __future__ import annotations

import copy
import hashlib
import random
from typing import TYPE_CHECKING, Any

from loguru import logger as log

from src.backend.features.combat.dto.actor import ActorSnapshot  # noqa: TC001
from src.backend.features.combat.dto.session import BattleContext  # noqa: TC001
from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.combat.runtime.ai.action_space import (
    LegalAction,
    build_legal_actions_for_target,
    build_legal_instant_actions_for_target,
)
from src.backend.features.combat.runtime.ai.ai_memory import get_memory
from src.backend.features.combat.runtime.ai.archetypes import Archetype
from src.backend.features.combat.runtime.ai.observation import extract_self, extract_target
from src.backend.features.combat.runtime.ai.policy_store import PolicyStore
from src.backend.features.combat.runtime.ai.scorer import PolicyScorer
from src.backend.features.combat.runtime.ai.tactics import TACTIC_OVERLAYS, choose_tactic
from src.backend.features.combat.runtime.ai.team_awareness import TeamState, extract_team_state
from src.backend.features.combat.runtime.engine.feint_service import FeintService

if TYPE_CHECKING:
    from src.backend.features.combat.runtime.ai.policy import Policy


class MonsterCombatBrain:
    """Per-exchange inference for a monster actor.

    Primary API: :meth:`decide_exchange` returns one payload for one
    (bot, target) pair. :meth:`decide_turn` is the planning-budget wrapper
    that loops across pending intents, optionally emits instant abilities
    before exchanges, and locally accounts for resource depletion.
    """

    def __init__(self, policy_store: PolicyStore | None = None, policy: Policy | None = None) -> None:
        self._policy_store = policy_store or PolicyStore()
        self._policy_override = policy
        self._base_policy_cache: Policy | None = None
        self._archetype_policy_cache: dict[str, Policy] = {}

    @property
    def policy(self) -> Policy:
        if self._policy_override is not None:
            return self._policy_override
        if self._base_policy_cache is None:
            self._base_policy_cache = self._policy_store.load()
        return self._base_policy_cache

    def _policy_for_bot(self, bot: ActorSnapshot) -> Policy:
        """Resolve the bot's archetype policy (or the explicit override)."""
        if self._policy_override is not None:
            return self._policy_override
        archetype_id = str(getattr(bot.meta, "ai_archetype", "balanced") or "balanced")
        policy = self._archetype_policy_cache.get(archetype_id)
        if policy is None:
            policy = self._policy_store.load(archetype=archetype_id)
            self._archetype_policy_cache[archetype_id] = policy
        return policy

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def decide_exchange(
        self,
        bot: ActorSnapshot,
        target: ActorSnapshot,
        battle: BattleContext | None = None,
        *,
        policy_override: Policy | None = None,
        team_state: TeamState | None = None,
    ) -> dict[str, Any]:
        """Pick one payload for the (bot, target) exchange.

        Reads ``bot.meta.feints.hand`` and ``bot.meta.stamina`` as the
        current planning budget. Selects the legal action with the highest
        policy score. Does not mutate ``bot`` or ``target``.

        ``policy_override`` lets :meth:`decide_turn` pass a tactic-adjusted
        policy in once per turn without re-resolving the archetype on every
        target. ``team_state`` is similarly threaded so team awareness work
        runs once per turn instead of per (bot, target).
        """
        alive_enemy_count = self._alive_enemy_count(bot, battle, [target])
        self_obs = extract_self(
            bot,
            alive_enemy_count=alive_enemy_count,
            team_state=team_state,
            memory=get_memory(battle, bot.meta.id),
        )
        target_obs = extract_target(target, memory=get_memory(battle, target.meta.id))
        policy = policy_override if policy_override is not None else self._policy_for_bot(bot)
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

        Iterates ``candidate_targets``, optionally scoring one instant
        ability before calling :meth:`decide_exchange` for each target.
        Between iterations the *local* copy of ``bot`` is mutated:

        * The chosen feint is removed from the hand (it can only be
          consumed once at registration).
        * Its stamina activation cost is subtracted from
          ``bot.meta.stamina`` (the shared budget across all intents in
          this planning pass).
        * Chosen instant ability energy/token costs are subtracted from
          the local planning snapshot.

        The result: the second target sees a realistic remaining hand and
        a remaining stamina pool, so it does not over-commit. The
        original ``bot`` snapshot is left untouched.
        """
        if not candidate_targets:
            return []

        # Plan against a local clone so the caller's snapshot stays clean.
        local_bot = copy.deepcopy(bot)

        # Resolve archetype + tactic once per turn so per-target loops below
        # do not re-derive policy each iteration. The tactic decision uses
        # the planning-budget view (local_bot) so a depleted-stamina batch
        # picks defensive/balanced rather than aggressive.
        archetype = Archetype.coerce(getattr(local_bot.meta, "ai_archetype", None))
        base_policy = self._policy_for_bot(local_bot)
        # Team state is best-effort: it reads moves already committed this
        # step. Extract once for the whole turn — the cache does not change
        # between our decide_exchange iterations.
        team_state = extract_team_state(battle, local_bot)
        turn_self_obs = extract_self(
            local_bot,
            alive_enemy_count=self._alive_enemy_count(local_bot, battle, candidate_targets),
            team_state=team_state,
            memory=get_memory(battle, local_bot.meta.id),
        )
        tactic = choose_tactic(turn_self_obs, archetype)
        policy = base_policy.with_overlay(TACTIC_OVERLAYS[tactic])
        log.bind(
            bot_id=str(local_bot.meta.id),
            archetype=archetype.value,
            tactic=tactic.value,
            hp_pct=round(turn_self_obs.hp_pct, 3),
            stamina_pct=round(turn_self_obs.stamina_pct, 3),
            alive_enemy_count=turn_self_obs.alive_enemy_count,
            ally_focus_targets=len(team_state.allies_targets),
        ).trace("AiTacticChosen")

        payloads: list[dict[str, Any]] = []
        for target in candidate_targets:
            instant_payload = self._decide_optional_instant(
                local_bot,
                target,
                battle,
                policy_override=policy,
                team_state=team_state,
            )
            if instant_payload is not None:
                payloads.append(instant_payload)
                self._apply_intent_to_local_state(local_bot, instant_payload)

            payload = self.decide_exchange(
                local_bot,
                target,
                battle,
                policy_override=policy,
                team_state=team_state,
            )
            payloads.append(payload)
            self._apply_intent_to_local_state(local_bot, payload)

        return payloads

    def _decide_optional_instant(
        self,
        bot: ActorSnapshot,
        target: ActorSnapshot,
        battle: BattleContext | None = None,
        *,
        policy_override: Policy | None = None,
        team_state: TeamState | None = None,
    ) -> dict[str, Any] | None:
        actions = build_legal_instant_actions_for_target(bot, target)
        if not actions:
            return None

        alive_enemy_count = self._alive_enemy_count(bot, battle, [target])
        self_obs = extract_self(
            bot,
            alive_enemy_count=alive_enemy_count,
            team_state=team_state,
            memory=get_memory(battle, bot.meta.id),
        )
        target_obs = extract_target(target, memory=get_memory(battle, target.meta.id))
        policy = policy_override if policy_override is not None else self._policy_for_bot(bot)
        rng = random.Random(self._rng_seed(bot, battle, target) ^ 0xA17A11)

        skip_action = LegalAction(
            action_type="skip_instant",
            target_id=str(target.meta.id),
            feint_id=None,
            tags=frozenset(),
        )
        skip_score = PolicyScorer.score(self_obs, target_obs, skip_action, policy, rng)
        scored_actions = [(PolicyScorer.score(self_obs, target_obs, action, policy, rng), action) for action in actions]
        best_score, best_action = max(scored_actions, key=lambda item: item[0])
        if best_score <= skip_score:
            return None
        return best_action.to_payload()

    # ------------------------------------------------------------------
    # Local planning mutation
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_intent_to_local_state(local_bot: ActorSnapshot, payload: dict[str, Any]) -> None:
        """Simulate the executor's resource debit on the local snapshot.

        Updates the planning-budget view of the bot so subsequent
        :meth:`decide_exchange` and instant checks in the same
        :meth:`decide_turn` iteration see realistic remaining resources.

        Hand: pop the consumed feint (it can only be used once per round
        until refill).

        Stamina: subtract the activation cost for exchange feints.

        Energy/tokens: subtract instant ability costs. This is local planning
        accounting only; executor/turn manager still owns the real runtime
        mutation.
        """
        ability_id = payload.get("ability_id")
        if ability_id:
            entry = CombatCatalogIntegrator.get_ability_catalog_entry(str(ability_id))
            if entry is None:
                return
            cost = entry.technical.cost
            local_bot.meta.en = max(0, int(local_bot.meta.en or 0) - int(cost.energy or 0))
            token_cost = dict(cost.tokens)
            if cost.gift_tokens > 0:
                token_cost["gift"] = token_cost.get("gift", 0) + int(cost.gift_tokens)
            for token, amount in token_cost.items():
                local_bot.meta.tokens[str(token)] = max(
                    0,
                    int(local_bot.meta.tokens.get(str(token), 0) or 0) - int(amount or 0),
                )
            return

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

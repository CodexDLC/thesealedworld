"""Deterministic scoring environment for MVP policy evaluation.

This is *not* a CombatPipeline simulator. It is a tag-matching reward
function on the curated scenario set in :mod:`scenarios`. The trainer
rewards a policy when the action picked by the brain against a target
carries the tags the scenario flagged as desirable, and punishes obvious
mistakes (e.g. throwing a costly feint when the scenario expected an
empty action).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from src.backend.features.combat.runtime.ai.action_space import build_legal_actions_for_target
from src.backend.features.combat.runtime.ai.brain import MonsterCombatBrain
from src.backend.features.combat.runtime.ai.policy import Policy  # noqa: TC001
from src.backend.features.combat.runtime.ai.training.scenarios import SyntheticScenario  # noqa: TC001


@dataclass(frozen=True)
class EvalResult:
    """Aggregate outcome of evaluating one policy against scenarios."""

    total_reward: float
    per_scenario: dict[str, float]


class ScoringEnvironment:
    """Deterministic reward function used during evolutionary search."""

    def __init__(self, scenarios: list[SyntheticScenario]) -> None:
        self._scenarios = list(scenarios)

    def evaluate(self, policy: Policy, rng: random.Random | None = None) -> EvalResult:
        brain = MonsterCombatBrain(policy=policy)
        rng = rng or random.Random(0)
        per_scenario: dict[str, float] = {}
        total = 0.0

        for scenario in self._scenarios:
            reward = self._score_one(brain, scenario, rng)
            per_scenario[scenario.name] = reward
            total += reward

        return EvalResult(total_reward=total, per_scenario=per_scenario)

    def _score_one(
        self,
        brain: MonsterCombatBrain,
        scenario: SyntheticScenario,
        rng: random.Random,
    ) -> float:
        payloads = brain.decide_turn(scenario.bot, None, scenario.targets)
        if not payloads:
            return -1.0

        expected_by_target = {item.target_id: item.expected_tags for item in scenario.expected}
        reward = 0.0

        for payload in payloads:
            target_id = str(payload.get("target_id"))
            expected_tags = expected_by_target.get(target_id, frozenset())
            feint_id = payload.get("feint_id")
            target = next((t for t in scenario.targets if str(t.meta.id) == target_id), None)
            if target is None:
                reward -= 0.2
                continue

            chosen_tags: frozenset[str] = frozenset()
            chosen_cost = 0
            for action in build_legal_actions_for_target(scenario.bot, target):
                if action.feint_id == feint_id:
                    chosen_tags = action.tags
                    chosen_cost = sum(action.cost.values())
                    break

            if expected_tags:
                if expected_tags & chosen_tags:
                    reward += 1.0
                else:
                    reward -= 0.4
            else:
                # The scenario wants no feint here — reward staying clean.
                if feint_id is None:
                    reward += 0.6
                else:
                    reward -= 0.3

            # Mild penalty for spending tokens when not asked to.
            if not expected_tags and chosen_cost > 0:
                reward -= 0.1 * chosen_cost

        # Per-scenario consistency bonus: every target plan exists.
        if len(payloads) == len(scenario.targets):
            reward += 0.1

        # Touch the rng to keep the API deterministic-but-evolvable for future noise.
        _ = rng.random()

        return reward

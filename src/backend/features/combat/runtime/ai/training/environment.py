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

from src.backend.features.combat.runtime.ai.action_space import (
    build_legal_actions_for_target,
    build_legal_instant_actions_for_target,
)
from src.backend.features.combat.runtime.ai.brain import MonsterCombatBrain
from src.backend.features.combat.runtime.ai.policy import Policy  # noqa: TC001
from src.backend.features.combat.runtime.ai.team_awareness import extract_team_state
from src.backend.features.combat.runtime.ai.training.scenarios import (  # noqa: TC001
    ScenarioTarget,
    SyntheticScenario,
)


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

        total += self._policy_regularization(policy)

        return EvalResult(total_reward=total, per_scenario=per_scenario)

    def _score_one(
        self,
        brain: MonsterCombatBrain,
        scenario: SyntheticScenario,
        rng: random.Random,
    ) -> float:
        payloads = brain.decide_turn(scenario.bot, scenario.battle, scenario.targets)
        if not payloads:
            return -1.0

        unmatched_expected = list(scenario.expected)
        reward = 0.0

        for payload in payloads:
            target_id = str(payload.get("target_id"))
            expected = self._match_expected(payload, unmatched_expected)
            if expected is not None:
                unmatched_expected.remove(expected)
            expected_tags = expected.expected_tags if expected is not None else frozenset()
            expected_feint_id = expected.expected_feint_id if expected is not None else None
            expected_ability_id = expected.expected_ability_id if expected is not None else None
            reward_weight = expected.reward_weight if expected is not None else 1.0
            resource_penalty = expected.resource_penalty if expected is not None else 0.1
            feint_id = payload.get("feint_id")
            ability_id = payload.get("ability_id")
            target = next((t for t in scenario.targets if str(t.meta.id) == target_id), None)
            if target is None and target_id == str(scenario.bot.meta.id):
                target = scenario.targets[0] if scenario.targets else None
            if target is None:
                reward -= 0.2
                continue

            chosen_tags: frozenset[str] = frozenset()
            chosen_token_cost = 0
            chosen_stamina_cost = 0
            chosen_energy_cost = 0
            chosen_actions = (
                build_legal_instant_actions_for_target(scenario.bot, target)
                if ability_id is not None
                else build_legal_actions_for_target(scenario.bot, target)
            )
            for action in chosen_actions:
                if action.feint_id == feint_id and action.ability_id == ability_id:
                    chosen_tags = action.tags
                    chosen_token_cost = sum(action.cost.values())
                    chosen_stamina_cost = action.stamina_cost
                    chosen_energy_cost = action.energy_cost
                    break

            if expected_ability_id is not None:
                if ability_id == expected_ability_id:
                    reward += 1.0 * reward_weight
                else:
                    reward -= 1.0 * reward_weight
            elif ability_id is not None:
                reward -= 0.3 * reward_weight
            elif expected_feint_id is not None:
                if feint_id == expected_feint_id:
                    reward += 1.0 * reward_weight
                else:
                    reward -= 1.0 * reward_weight
            elif expected_tags:
                if expected_tags & chosen_tags:
                    reward += 1.0 * reward_weight
                else:
                    reward -= 0.4 * reward_weight
            else:
                # The scenario wants no feint here — reward staying clean.
                if feint_id is None and ability_id is None:
                    reward += 0.6 * reward_weight
                else:
                    reward -= 0.6 * reward_weight

            # Penalty for spending resources when the expected answer did not
            # ask for a resource-backed action. Stamina and energy are scaled
            # down because their unit size is larger than combat-token costs.
            if not expected_tags:
                resource_units = chosen_token_cost + chosen_stamina_cost / 10.0 + chosen_energy_cost / 10.0
                if resource_units > 0:
                    reward -= resource_penalty * resource_units
                if target.meta.hp <= max(1, int(target.meta.max_hp * 0.25)) and (
                    feint_id is not None or ability_id is not None
                ):
                    reward -= 8.0
                if "control" in chosen_tags and target_id in self._ally_pending_control_targets(scenario):
                    reward -= 8.0
            if "heal" in expected_tags and "heal" not in chosen_tags:
                reward -= 8.0
            if "dispel_prep" in expected_tags and target.statuses.effects and "dispel_prep" not in chosen_tags:
                reward -= 8.0

        for expected in unmatched_expected:
            if (
                expected.expected_ability_id is not None
                or expected.expected_feint_id is not None
                or expected.expected_tags
            ):
                reward -= 0.6 * expected.reward_weight

        # Per-scenario consistency bonus: every target plan exists.
        exchange_payload_count = sum(1 for payload in payloads if payload.get("action") != "instant")
        if exchange_payload_count == len(scenario.targets):
            reward += 0.1

        # Touch the rng to keep the API deterministic-but-evolvable for future noise.
        _ = rng.random()

        return reward

    @staticmethod
    def _ally_pending_control_targets(scenario: SyntheticScenario) -> frozenset[str]:
        if scenario.battle is None:
            return frozenset()
        return extract_team_state(scenario.battle, scenario.bot).allies_pending_control_targets

    @staticmethod
    def _match_expected(payload: dict[str, object], expected: list[ScenarioTarget]) -> ScenarioTarget | None:
        """Match expected rows without collapsing ability+exchange on one target."""
        target_id = str(payload.get("target_id"))
        ability_id = payload.get("ability_id")
        feint_id = payload.get("feint_id")

        if ability_id is not None:
            for item in expected:
                if item.target_id == target_id and item.expected_ability_id == ability_id:
                    return item
            for item in expected:
                if item.target_id == target_id and item.expected_ability_id is not None:
                    return item
        if feint_id is not None:
            for item in expected:
                if item.target_id == target_id and item.expected_feint_id == feint_id:
                    return item
            for item in expected:
                if item.target_id == target_id and item.expected_ability_id is None:
                    return item
        for item in expected:
            if item.target_id == target_id and item.expected_ability_id is None:
                return item
        return None

    @staticmethod
    def _policy_regularization(policy: Policy) -> float:
        """Penalise weights that have no action-specific signal yet.

        Some weights are not fully identifiable from the current per-target
        synthetic planner. Anchor their sign so evolution cannot "win" by
        drifting into nonsense such as expensive-is-better or duplicate-control
        being rewarded. Battle fine-tune may still move these later, but the
        synthetic base should start from a sane sign.
        """
        penalty = 0.0
        penalty += 8.0 * max(0.0, policy.get("stamina_cost"))
        penalty += 12.0 * max(0.0, policy.get("energy_cost"))
        penalty += 4.0 * max(0.0, policy.get("token_cost"))

        for key in (
            "finishable",
            "target_low_hp",
            "anti_parry",
            "anti_evasion",
            "anti_block",
            "armor_bypass",
            "ranged_reposition",
            "ranged_keep_far",
            "ranged_stabilize",
            "ranged_pressure_reduce",
            "ranged_position_damage",
            "observed_parry_rate",
            "observed_evasion_rate",
            "observed_block_rate",
            "team_focus",
            "team_focus_pile_on",
            "team_dedup_control",
            "control",
            "heal",
            "defense",
            "debuff",
            "preparation",
            "heal_dedup_penalty",
            "prep_threat_penalty",
            "dispel_prep",
            "repeat_feint_penalty",
            "sticky_target_bonus",
        ):
            penalty += 8.0 * max(0.0, -policy.get(key))

        # This weight is added only when a feint is used on a finishable target.
        # Positive values literally reward burning resources on dying targets;
        # the useful sign is <= 0.
        penalty += 8.0 * max(0.0, policy.get("finishable_resource_save"))

        # These are context-wide resource presence signals, not action-specific
        # spend/value signals in the current action space. Keep them close to
        # neutral until a real spend scenario can identify a useful sign.
        penalty += 3.0 * abs(policy.get("gift_resource"))
        penalty += 3.0 * abs(policy.get("blood_resource"))
        penalty += 4.0 * max(0.0, policy.get("randomness"))
        return -penalty

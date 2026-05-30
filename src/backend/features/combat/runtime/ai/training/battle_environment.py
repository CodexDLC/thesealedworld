"""Battle-simulation training environment for combat AI policies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.backend.features.combat.runtime.ai.brain import MonsterCombatBrain
from src.backend.features.combat.runtime.simulation import (
    AiSimulationIntentProvider,
    InMemoryBattleState,
    InMemoryCombatSimulator,
    SimulationRunResult,
)

if TYPE_CHECKING:
    from src.backend.features.combat.runtime.ai.policy import Policy


@dataclass(frozen=True)
class BattleSimulationScenario:
    """One in-memory battle fixture used for policy evaluation."""

    name: str
    state_factory: Callable[[], InMemoryBattleState]
    expected_winner: str | None = None


@dataclass(frozen=True)
class BattleEvalResult:
    """Aggregate battle-simulation training result."""

    total_reward: float
    per_scenario: dict[str, float]
    reports: dict[str, SimulationRunResult]


class BattleTrainingEnvironment:
    """Evaluate policies by running bounded in-memory battles."""

    def __init__(self, scenarios: list[BattleSimulationScenario]) -> None:
        self._scenarios = list(scenarios)

    async def evaluate(self, policy: Policy) -> BattleEvalResult:
        per_scenario: dict[str, float] = {}
        reports: dict[str, SimulationRunResult] = {}
        total = 0.0

        for scenario in self._scenarios:
            state = scenario.state_factory()
            simulator = InMemoryCombatSimulator(
                intent_provider=AiSimulationIntentProvider(brain=MonsterCombatBrain(policy=policy))
            )
            result = await simulator.run(state)
            reward = self._score_result(scenario, result)
            per_scenario[scenario.name] = reward
            reports[scenario.name] = result
            total += reward

        return BattleEvalResult(total_reward=total, per_scenario=per_scenario, reports=reports)

    @staticmethod
    def _score_result(scenario: BattleSimulationScenario, result: SimulationRunResult) -> float:
        telemetry = result.telemetry
        reward = 0.0

        if scenario.expected_winner is not None:
            reward += 10.0 if result.winner == scenario.expected_winner else -10.0
        elif result.winner != "draw":
            reward += 2.0

        reward += 0.02 * sum(telemetry.damage_by_actor.values())
        reward += 0.02 * sum(telemetry.healing_by_actor.values())
        reward += 0.5 * len(telemetry.deaths)
        reward += 0.25 * telemetry.control_applied
        reward += 0.15 * telemetry.buff_applied
        reward -= 0.02 * sum(telemetry.resource_spent_by_actor.values())
        reward -= 1.0 * telemetry.failed_action_count
        reward -= 0.05 * result.rounds_completed
        return reward

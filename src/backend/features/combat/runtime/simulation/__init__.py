"""In-memory combat simulation layer for auto battle and training."""

from src.backend.features.combat.runtime.simulation.action_collector import SimulationActionCollector
from src.backend.features.combat.runtime.simulation.factory import InMemoryBattleFactory
from src.backend.features.combat.runtime.simulation.intent_provider import (
    AiSimulationIntentProvider,
    SimulationIntentProvider,
)
from src.backend.features.combat.runtime.simulation.live_simulator import (
    LiveInMemoryCombatSimulator,
    LiveSimulationStepResult,
    LiveSimulationTiming,
    SimulationMoveRegistrar,
)
from src.backend.features.combat.runtime.simulation.reports import render_simulation_report
from src.backend.features.combat.runtime.simulation.simulator import (
    InMemoryCombatSimulator,
    SimulationRunResult,
    SimulationStepResult,
)
from src.backend.features.combat.runtime.simulation.starting_imprint_actors import (
    BALANCE_SIMULATION_IMPRINTS,
    BALANCE_TEST_SIMULATION_IMPRINTS,
    DEFAULT_STARTER_SIMULATION_IMPRINTS,
    STARTER_5V5_BLUE,
    STARTER_5V5_RED,
    STARTER_SKILL_PROFILE_BASELINE,
    STARTER_SKILL_PROFILE_MAXED_EXISTING,
    StartingImprintSimulationActor,
    StartingImprintSimulationActorBuilder,
    all_starting_imprint_keys,
    random_starter_5v5_imprints,
    random_starter_roster_imprints,
)
from src.backend.features.combat.runtime.simulation.state import InMemoryBattleLimits, InMemoryBattleState
from src.backend.features.combat.runtime.simulation.telemetry import CombatTelemetry

__all__ = [
    "AiSimulationIntentProvider",
    "CombatTelemetry",
    "InMemoryBattleFactory",
    "InMemoryBattleLimits",
    "InMemoryBattleState",
    "InMemoryCombatSimulator",
    "LiveInMemoryCombatSimulator",
    "LiveSimulationStepResult",
    "LiveSimulationTiming",
    "SimulationActionCollector",
    "SimulationIntentProvider",
    "SimulationMoveRegistrar",
    "SimulationRunResult",
    "SimulationStepResult",
    "BALANCE_SIMULATION_IMPRINTS",
    "BALANCE_TEST_SIMULATION_IMPRINTS",
    "DEFAULT_STARTER_SIMULATION_IMPRINTS",
    "STARTER_5V5_BLUE",
    "STARTER_5V5_RED",
    "STARTER_SKILL_PROFILE_BASELINE",
    "STARTER_SKILL_PROFILE_MAXED_EXISTING",
    "StartingImprintSimulationActor",
    "StartingImprintSimulationActorBuilder",
    "all_starting_imprint_keys",
    "random_starter_5v5_imprints",
    "random_starter_roster_imprints",
    "render_simulation_report",
]

"""In-memory combat simulation layer for auto battle and training."""

from src.backend.features.combat.runtime.simulation.action_collector import SimulationActionCollector
from src.backend.features.combat.runtime.simulation.factory import InMemoryBattleFactory
from src.backend.features.combat.runtime.simulation.family_pressure import (
    FamilyPressureComposition,
    FamilyPressureCompositionReport,
    FamilyPressureConfig,
    FamilyPressureReport,
    FamilyPressureSimulator,
    FamilyPressureTrial,
    build_family_pressure_compositions,
    format_family_pressure_report,
    select_members_for_composition,
)
from src.backend.features.combat.runtime.simulation.intent_provider import (
    AiSimulationIntentProvider,
    SimulationIntentProvider,
)
from src.backend.features.combat.runtime.simulation.live_simulator import (
    LiveInMemoryCombatSimulator,
    LiveSimulationNoExchangeWorkError,
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
    DEFAULT_STARTER_SIMULATION_IMPRINTS,
    STARTER_5V5_BLUE,
    STARTER_5V5_RED,
    STARTER_SIMULATION_BEHAVIOR_PROFILES,
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
    "FamilyPressureComposition",
    "FamilyPressureCompositionReport",
    "FamilyPressureConfig",
    "FamilyPressureReport",
    "FamilyPressureSimulator",
    "FamilyPressureTrial",
    "InMemoryBattleFactory",
    "InMemoryBattleLimits",
    "InMemoryBattleState",
    "InMemoryCombatSimulator",
    "LiveInMemoryCombatSimulator",
    "LiveSimulationNoExchangeWorkError",
    "LiveSimulationStepResult",
    "LiveSimulationTiming",
    "SimulationActionCollector",
    "SimulationIntentProvider",
    "SimulationMoveRegistrar",
    "SimulationRunResult",
    "SimulationStepResult",
    "DEFAULT_STARTER_SIMULATION_IMPRINTS",
    "STARTER_5V5_BLUE",
    "STARTER_5V5_RED",
    "STARTER_SIMULATION_BEHAVIOR_PROFILES",
    "STARTER_SKILL_PROFILE_BASELINE",
    "STARTER_SKILL_PROFILE_MAXED_EXISTING",
    "StartingImprintSimulationActor",
    "StartingImprintSimulationActorBuilder",
    "all_starting_imprint_keys",
    "build_family_pressure_compositions",
    "format_family_pressure_report",
    "random_starter_5v5_imprints",
    "random_starter_roster_imprints",
    "render_simulation_report",
    "select_members_for_composition",
]

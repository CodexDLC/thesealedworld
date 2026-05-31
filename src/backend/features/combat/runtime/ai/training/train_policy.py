"""CLI + library entry point for offline combat AI policy training."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from src.backend.features.combat.runtime.ai.policy import Policy
from src.backend.features.combat.runtime.ai.training.environment import ScoringEnvironment
from src.backend.features.combat.runtime.ai.training.evolution import TrainingRun, evolve
from src.backend.features.combat.runtime.ai.training.scenarios import default_scenario_set


@dataclass
class TrainArgs:
    generations: int = 10
    population: int = 20
    seed: int = 0
    start_from: Path | None = None
    duration_seconds: float | None = None
    sigma: float = 0.25


def train(args: TrainArgs) -> TrainingRun:
    """Run an evolutionary search and return the in-memory training result."""
    seed_policy = _load_seed_policy(args.start_from)
    scenarios = default_scenario_set(seed=args.seed)
    environment = ScoringEnvironment(scenarios)

    return evolve(
        seed_policy,
        environment,
        population=args.population,
        generations=args.generations,
        seed=args.seed,
        sigma=args.sigma,
        duration_seconds=args.duration_seconds,
    )


def _load_seed_policy(path: Path | None) -> Policy:
    if path is not None and path.exists():
        return Policy.from_path(path)
    return Policy.with_defaults(policy_id="train_seed")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a combat AI policy offline.")
    parser.add_argument("--generations", type=int, default=10)
    parser.add_argument("--population", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--start-from", type=Path, default=None)
    parser.add_argument("--duration-seconds", type=float, default=None)
    parser.add_argument("--sigma", type=float, default=0.25)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    namespace = parser.parse_args(argv)
    args = TrainArgs(
        generations=namespace.generations,
        population=namespace.population,
        seed=namespace.seed,
        start_from=namespace.start_from,
        duration_seconds=namespace.duration_seconds,
        sigma=namespace.sigma,
    )
    run = train(args)
    print(f"Best reward: {run.best_policy.metadata.get('final_reward')}")
    print(f"Generations recorded: {len(run.metrics)}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual CLI entry
    sys.exit(main())

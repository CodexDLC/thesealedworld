"""Evolutionary policy search for the MVP trainer."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from src.backend.features.combat.runtime.ai.policy import DEFAULT_WEIGHT_KEYS, Policy
from src.backend.features.combat.runtime.ai.training.environment import ScoringEnvironment  # noqa: TC001


@dataclass
class GenerationMetric:
    generation: int
    best_reward: float
    mean_reward: float
    elapsed_seconds: float


@dataclass
class LeaderboardEntry:
    policy_id: str
    reward: float
    weights: dict[str, float]


@dataclass
class TrainingRun:
    best_policy: Policy
    leaderboard: list[LeaderboardEntry]
    metrics: list[GenerationMetric] = field(default_factory=list)


def _mutate(weights: dict[str, float], rng: random.Random, sigma: float) -> dict[str, float]:
    return {key: float(value) + rng.gauss(0.0, sigma) for key, value in weights.items()}


def _seed_population(
    seed_policy: Policy,
    population_size: int,
    rng: random.Random,
    sigma: float,
) -> list[Policy]:
    base = {key: seed_policy.get(key) for key in DEFAULT_WEIGHT_KEYS}
    # Inject any extra keys the seed policy carried in.
    base.update({k: seed_policy.get(k) for k in seed_policy.weights})

    population: list[Policy] = [seed_policy.model_copy(deep=True)]
    for index in range(1, population_size):
        weights = _mutate(base, rng, sigma)
        population.append(
            Policy(
                policy_id=f"{seed_policy.policy_id}_gen0_{index}",
                version=seed_policy.version,
                weights=weights,
                metadata={"parent": seed_policy.policy_id},
            )
        )
    return population


def _tournament_select(
    rewards: list[tuple[Policy, float]],
    rng: random.Random,
    k: int = 3,
) -> Policy:
    competitors = rng.sample(rewards, k=min(k, len(rewards)))
    competitors.sort(key=lambda item: item[1], reverse=True)
    return competitors[0][0]


def evolve(
    seed_policy: Policy,
    environment: ScoringEnvironment,
    *,
    population: int,
    generations: int,
    seed: int,
    sigma: float = 0.25,
    sigma_decay: float = 0.9,
    duration_seconds: float | None = None,
) -> TrainingRun:
    """Run an evolutionary search and return the best policy plus history."""
    if population < 2:
        raise ValueError("population must be >= 2")
    if generations < 1:
        raise ValueError("generations must be >= 1")

    rng = random.Random(seed)
    eval_rng = random.Random(seed + 1)

    members = _seed_population(seed_policy, population, rng, sigma)
    metrics: list[GenerationMetric] = []
    started = time.perf_counter()

    best_member: Policy = members[0]
    best_reward = float("-inf")
    last_rewarded: list[tuple[Policy, float]] = []

    for generation in range(generations):
        if duration_seconds is not None and (time.perf_counter() - started) >= duration_seconds:
            break

        scored: list[tuple[Policy, float]] = []
        for member in members:
            result = environment.evaluate(member, eval_rng)
            scored.append((member, result.total_reward))

        scored.sort(key=lambda item: item[1], reverse=True)
        top_member, top_reward = scored[0]
        if top_reward > best_reward:
            best_reward = top_reward
            best_member = top_member.model_copy(deep=True)
            best_member.metadata = {**best_member.metadata, "trained_generation": generation}

        mean_reward = sum(reward for _, reward in scored) / len(scored)
        metrics.append(
            GenerationMetric(
                generation=generation,
                best_reward=top_reward,
                mean_reward=mean_reward,
                elapsed_seconds=time.perf_counter() - started,
            )
        )

        last_rewarded = scored

        # Build next generation: elitism + tournament-selected mutations.
        next_members: list[Policy] = [top_member.model_copy(deep=True)]
        current_sigma = sigma * (sigma_decay**generation)
        while len(next_members) < population:
            parent = _tournament_select(scored, rng)
            mutated_weights = _mutate(parent.weights, rng, current_sigma)
            child = Policy(
                policy_id=f"{seed_policy.policy_id}_g{generation + 1}_{len(next_members)}",
                version=seed_policy.version,
                weights=mutated_weights,
                metadata={"parent": parent.policy_id},
            )
            next_members.append(child)
        members = next_members

    leaderboard = [
        LeaderboardEntry(policy_id=policy.policy_id, reward=reward, weights=dict(policy.weights))
        for policy, reward in sorted(last_rewarded, key=lambda item: item[1], reverse=True)
    ]
    if not leaderboard:
        leaderboard = [
            LeaderboardEntry(policy_id=best_member.policy_id, reward=best_reward, weights=dict(best_member.weights))
        ]

    best_member.metadata = {**best_member.metadata, "final_reward": best_reward}

    return TrainingRun(best_policy=best_member, leaderboard=leaderboard, metrics=metrics)

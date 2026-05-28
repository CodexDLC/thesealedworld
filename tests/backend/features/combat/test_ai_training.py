"""Smoke + determinism tests for the offline policy trainer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.backend.features.combat.runtime.ai.policy import Policy
from src.backend.features.combat.runtime.ai.training import TrainArgs, train


@pytest.mark.unit
def test_train_smoke_writes_expected_artifacts(tmp_path: Path) -> None:
    args = TrainArgs(generations=2, population=4, seed=0, output_dir=tmp_path / "run_a")
    run = train(args)

    best_path = tmp_path / "run_a" / "best_policy.json"
    leaderboard_path = tmp_path / "run_a" / "leaderboard.json"
    metrics_path = tmp_path / "run_a" / "metrics.jsonl"

    assert best_path.exists()
    assert leaderboard_path.exists()
    assert metrics_path.exists()

    best_payload = json.loads(best_path.read_text(encoding="utf-8"))
    Policy.model_validate(best_payload)  # schema valid

    leaderboard = json.loads(leaderboard_path.read_text(encoding="utf-8"))
    assert isinstance(leaderboard, list)
    assert leaderboard, "Leaderboard should have at least one entry"

    metrics_lines = [
        json.loads(line) for line in metrics_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert metrics_lines, "Metrics file should contain at least one generation"
    assert {"generation", "best_reward", "mean_reward"} <= set(metrics_lines[0])
    assert run.best_policy.metadata.get("final_reward") is not None


@pytest.mark.unit
def test_train_is_deterministic_for_same_seed(tmp_path: Path) -> None:
    args_a = TrainArgs(generations=3, population=6, seed=42, output_dir=tmp_path / "run_a")
    args_b = TrainArgs(generations=3, population=6, seed=42, output_dir=tmp_path / "run_b")

    train(args_a)
    train(args_b)

    weights_a = json.loads((tmp_path / "run_a" / "best_policy.json").read_text(encoding="utf-8"))["weights"]
    weights_b = json.loads((tmp_path / "run_b" / "best_policy.json").read_text(encoding="utf-8"))["weights"]
    assert weights_a == weights_b

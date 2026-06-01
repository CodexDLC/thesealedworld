from __future__ import annotations

from src.backend.features.exploration.runtime.experience import ExplorationExperienceService, flat_attribute_snapshot


def test_exploration_experience_calculates_catalog_skill_rewards() -> None:
    rewards = ExplorationExperienceService().calculate_rewards(
        action_power_by_skill={"skill_pathfinder": 1.0, "skill_hunting": 0.5, "missing": 10.0},
        current_skills={},
        attributes={
            "perception": 8.0,
            "endurance": 8.0,
            "agility": 8.0,
        },
    )

    assert rewards == {
        "skill_pathfinder": 0.0012,
        "skill_hunting": 0.0006,
    }


def test_flat_attribute_snapshot_accepts_runtime_attribute_payloads() -> None:
    assert flat_attribute_snapshot(
        {
            "perception": {"base": 5, "source": {"item": 2}, "temp": {"buff": 1}},
            "agility": "4",
        }
    ) == {"perception": 8.0, "agility": 4.0}

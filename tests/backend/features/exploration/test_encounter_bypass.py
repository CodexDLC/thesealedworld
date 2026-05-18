from __future__ import annotations

import pytest

from src.backend.features.exploration.runtime.encounter.bypass import calculate_bypass_chance


def test_bypass_chance_uses_scouting_and_hunting_average() -> None:
    chance = calculate_bypass_chance({"skill_scouting": 0.8, "skill_pathfinder": 1.0, "skill_hunting": 0.2})

    assert chance == pytest.approx(0.57)


def test_bypass_chance_keeps_unknown_skills_as_base_chance() -> None:
    assert calculate_bypass_chance({"skill_pathfinder": 1.0}) == pytest.approx(0.14)

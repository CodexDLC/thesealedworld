from __future__ import annotations

import pytest

from src.backend.features.combat.dto import ActorLoadoutDTO, ActorMetaDTO, ActorRawDTO, ActorSnapshot
from src.backend.features.combat.dto.actor import ActorStats
from src.backend.features.combat.runtime.ai.policy import Policy
from src.backend.features.combat.runtime.ai.training.battle_environment import (
    BattleEvalResult,
    BattleSimulationScenario,
    BattleTrainingEnvironment,
)
from src.backend.features.combat.runtime.engine.math_core import MathCore
from src.backend.features.combat.runtime.simulation import InMemoryBattleFactory, InMemoryBattleLimits
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


def training_actor(actor_id: str, team: str, *, hp: int, damage: float, is_ai: bool = True) -> ActorSnapshot:
    return ActorSnapshot(
        meta=ActorMetaDTO(
            id=actor_id,
            name=actor_id,
            type="monster" if is_ai else "player",
            team=team,
            is_ai=is_ai,
            hp=hp,
            max_hp=hp,
            stamina=100,
            max_stamina=100,
        ),
        raw=ActorRawDTO(
            modifiers={
                "main_hand_damage_base": damage,
                "main_hand_damage_spread": 0.0,
                "main_hand_accuracy": 1.0,
            }
        ),
        loadout=ActorLoadoutDTO(layout={"main_hand": "skill_swords"}),
        stats=ActorStats(
            mods=CombatModifiersDTO(
                main_hand_damage_base=damage,
                main_hand_damage_spread=0.0,
                main_hand_accuracy=1.0,
            ),
            skills=CombatSkillsDTO(skill_swords=1.0),
        ),
    )


def duel_state():
    return InMemoryBattleFactory.from_actors(
        [
            training_actor("bot", "red", hp=30, damage=30.0),
            training_actor("player_model", "blue", hp=20, damage=3.0, is_ai=False),
        ],
        session_id="training-duel",
        limits=InMemoryBattleLimits(max_rounds=4),
    )


@pytest.mark.unit
async def test_battle_training_environment_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, _max_d: min_d))
    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(lambda chance: (0.0, chance >= 0.7)))
    scenario = BattleSimulationScenario(
        name="monster_duel",
        state_factory=duel_state,
        expected_winner="red",
    )
    environment = BattleTrainingEnvironment([scenario])
    policy = Policy.with_defaults(policy_id="deterministic")

    first = await environment.evaluate(policy)
    second = await environment.evaluate(policy)

    assert isinstance(first, BattleEvalResult)
    assert first.total_reward == second.total_reward
    assert first.per_scenario == second.per_scenario
    assert first.reports["monster_duel"].winner == "red"


@pytest.mark.unit
async def test_battle_training_environment_rewards_expected_winner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, _max_d: min_d))
    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(lambda chance: (0.0, chance >= 0.7)))
    win_scenario = BattleSimulationScenario("win", duel_state, expected_winner="red")
    lose_scenario = BattleSimulationScenario("lose", duel_state, expected_winner="blue")
    policy = Policy.with_defaults(policy_id="baseline")

    result = await BattleTrainingEnvironment([win_scenario, lose_scenario]).evaluate(policy)

    assert result.per_scenario["win"] > result.per_scenario["lose"]
    assert result.total_reward == pytest.approx(result.per_scenario["win"] + result.per_scenario["lose"])


@pytest.mark.unit
async def test_battle_training_environment_rewards_any_non_draw_winner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, _max_d: min_d))
    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(lambda chance: (0.0, chance >= 0.7)))
    scenario = BattleSimulationScenario("open_winner", duel_state)

    result = await BattleTrainingEnvironment([scenario]).evaluate(Policy.with_defaults(policy_id="open"))

    assert result.reports["open_winner"].winner == "red"
    assert result.per_scenario["open_winner"] > 0

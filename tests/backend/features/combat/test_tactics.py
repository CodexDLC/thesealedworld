"""Tests for per-turn tactic selection and policy overlays (PR3)."""

from __future__ import annotations

import pytest

from src.backend.features.combat.dto.actor import (
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    ActorStats,
    FeintHandDTO,
)
from src.backend.features.combat.dto.session import BattleContext, BattleMeta
from src.backend.features.combat.runtime.ai.archetypes import Archetype
from src.backend.features.combat.runtime.ai.brain import MonsterCombatBrain
from src.backend.features.combat.runtime.ai.observation import SelfObservation
from src.backend.features.combat.runtime.ai.policy import Policy
from src.backend.features.combat.runtime.ai.tactics import (
    TACTIC_OVERLAYS,
    Tactic,
    choose_tactic,
)
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


def _self_obs(
    *, hp_pct: float = 1.0, stamina_pct: float = 1.0, alive_enemy_count: int = 1
) -> SelfObservation:
    return SelfObservation(
        hp_pct=hp_pct,
        stamina_pct=stamina_pct,
        en_pct=1.0,
        tokens={},
        alive_enemy_count=alive_enemy_count,
    )


def _actor(
    actor_id: str,
    *,
    team: str,
    ai_archetype: str = "balanced",
    hp: int = 100,
    max_hp: int = 100,
    stamina: int = 50,
) -> ActorSnapshot:
    return ActorSnapshot(
        meta=ActorMetaDTO(
            id=actor_id,
            name=actor_id,
            type="monster",
            team=team,
            is_ai=True,
            hp=hp,
            max_hp=max_hp,
            en=10,
            max_en=10,
            stamina=stamina,
            max_stamina=50,
            tactics=0,
            tokens={},
            feints=FeintHandDTO(hand={}, arsenal=[]),
            ai_archetype=ai_archetype,
        ),
        raw=ActorRawDTO(),
        skills={},
        loadout=ActorLoadoutDTO(),
        stats=ActorStats(mods=CombatModifiersDTO(), skills=CombatSkillsDTO()),
    )


def _battle(actors: list[ActorSnapshot]) -> BattleContext:
    return BattleContext(
        session_id="t1",
        meta=BattleMeta(
            active=1,
            step_counter=0,
            active_actors_count=len(actors),
            teams={
                "red": [a.meta.id for a in actors if a.meta.team == "red"],
                "blue": [a.meta.id for a in actors if a.meta.team == "blue"],
            },
            battle_type="arena",
            location_id="arena",
        ),
        actors={str(a.meta.id): a for a in actors},
    )


# ---------------------------------------------------------------------------
# choose_tactic rules
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_choose_tactic_low_hp_triggers_defensive_for_balanced() -> None:
    assert (
        choose_tactic(_self_obs(hp_pct=0.2), Archetype.BALANCED) is Tactic.DEFENSIVE
    )


@pytest.mark.unit
def test_choose_tactic_high_hp_and_stamina_triggers_aggressive() -> None:
    assert (
        choose_tactic(_self_obs(hp_pct=0.9, stamina_pct=0.8), Archetype.BALANCED)
        is Tactic.AGGRESSIVE
    )


@pytest.mark.unit
def test_choose_tactic_middle_state_is_balanced() -> None:
    assert (
        choose_tactic(_self_obs(hp_pct=0.5, stamina_pct=0.5), Archetype.BALANCED)
        is Tactic.BALANCED
    )


@pytest.mark.unit
def test_choose_tactic_berserker_is_aggressive_even_at_low_hp() -> None:
    # Berserker stays aggressive down to 0.15 HP.
    assert choose_tactic(_self_obs(hp_pct=0.2), Archetype.BERSERKER) is Tactic.AGGRESSIVE


@pytest.mark.unit
def test_choose_tactic_berserker_falls_back_to_balanced_at_critical_hp() -> None:
    assert choose_tactic(_self_obs(hp_pct=0.1), Archetype.BERSERKER) is Tactic.BALANCED


@pytest.mark.unit
def test_choose_tactic_bulwark_is_always_defensive() -> None:
    assert choose_tactic(_self_obs(hp_pct=1.0), Archetype.BULWARK) is Tactic.DEFENSIVE
    assert choose_tactic(_self_obs(hp_pct=0.2), Archetype.BULWARK) is Tactic.DEFENSIVE


# ---------------------------------------------------------------------------
# Overlay application via Policy.with_overlay
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_aggressive_overlay_amplifies_damage_weights() -> None:
    base = Policy.with_defaults({"expected_damage": 1.0, "defense": 1.0, "heal": 1.0})
    aggressive = base.with_overlay(TACTIC_OVERLAYS[Tactic.AGGRESSIVE])
    assert aggressive.get("expected_damage") > base.get("expected_damage")
    assert aggressive.get("defense") < base.get("defense")
    assert aggressive.get("heal") < base.get("heal")


@pytest.mark.unit
def test_defensive_overlay_amplifies_survival_weights() -> None:
    base = Policy.with_defaults({"defense": 1.0, "heal": 1.0, "expected_damage": 1.0})
    defensive = base.with_overlay(TACTIC_OVERLAYS[Tactic.DEFENSIVE])
    assert defensive.get("defense") > base.get("defense")
    assert defensive.get("heal") > base.get("heal")
    assert defensive.get("expected_damage") < base.get("expected_damage")


@pytest.mark.unit
def test_balanced_overlay_is_identity() -> None:
    base = Policy.with_defaults({"expected_damage": 1.0, "defense": 1.0})
    balanced = base.with_overlay(TACTIC_OVERLAYS[Tactic.BALANCED])
    assert balanced.get("expected_damage") == pytest.approx(base.get("expected_damage"))
    assert balanced.get("defense") == pytest.approx(base.get("defense"))


@pytest.mark.unit
def test_with_overlay_does_not_mutate_source_policy() -> None:
    base = Policy.with_defaults({"expected_damage": 2.0})
    _ = base.with_overlay({"expected_damage": 10.0})
    assert base.get("expected_damage") == pytest.approx(2.0)


@pytest.mark.unit
def test_with_overlay_ignores_unknown_keys() -> None:
    base = Policy.with_defaults({"expected_damage": 1.0})
    derived = base.with_overlay({"unknown_weight_xyz": 5.0})
    assert "unknown_weight_xyz" not in derived.weights


# ---------------------------------------------------------------------------
# Brain integration: decide_turn computes tactic once and applies overlay.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decide_turn_logs_archetype_and_tactic(caplog) -> None:
    """End-to-end smoke: a tactician bot at low HP should pick DEFENSIVE
    and emit the structured log line. We can't grep loguru's bind output
    via caplog cleanly here, so we just assert the call runs without error
    and returns one payload per target."""
    bot = _actor(
        "bot", team="red", ai_archetype="tactician", hp=25, max_hp=100, stamina=50
    )
    target = _actor("t1", team="blue")
    battle = _battle([bot, target])

    payloads = MonsterCombatBrain().decide_turn(bot, battle, [target])
    assert len(payloads) == 1
    assert payloads[0]["target_id"] == "t1"


@pytest.mark.unit
def test_decide_turn_does_not_mutate_bot_archetype() -> None:
    """The planning path runs against a deep copy; the caller's snapshot
    must retain its ``ai_archetype`` untouched."""
    bot = _actor("bot", team="red", ai_archetype="berserker")
    target = _actor("t1", team="blue")
    battle = _battle([bot, target])

    MonsterCombatBrain().decide_turn(bot, battle, [target])
    assert bot.meta.ai_archetype == "berserker"

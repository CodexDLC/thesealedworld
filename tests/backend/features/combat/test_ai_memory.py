"""Tests for cross-turn AI memory (PR5)."""

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
from src.backend.features.combat.dto.ai_memory_dto import AiMemoryDTO
from src.backend.features.combat.dto.session import BattleContext, BattleMeta
from src.backend.features.combat.runtime.ai.action_space import LegalAction
from src.backend.features.combat.runtime.ai.ai_memory import (
    DEFENCE_MEMORY_WINDOW,
    FEINT_MEMORY_WINDOW,
    defence_rate,
    get_memory,
    record_exchange_outcome,
)
from src.backend.features.combat.runtime.ai.observation import (
    extract_self,
    extract_target,
)
from src.backend.features.combat.runtime.ai.policy import Policy
from src.backend.features.combat.runtime.ai.scorer import PolicyScorer
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


def _actor(actor_id: str, *, team: str = "red", hp: int = 100) -> ActorSnapshot:
    return ActorSnapshot(
        meta=ActorMetaDTO(
            id=actor_id,
            name=actor_id,
            type="monster",
            team=team,
            is_ai=True,
            hp=hp,
            max_hp=100,
            en=10,
            max_en=10,
            stamina=50,
            max_stamina=50,
            tactics=0,
            tokens={},
            feints=FeintHandDTO(hand={}, arsenal=[]),
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
# record_exchange_outcome + rolling windows
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_record_writes_defender_outcome_and_attacker_feint() -> None:
    battle = _battle([_actor("a"), _actor("d", team="blue")])
    record_exchange_outcome(battle, "a", "d", "parry", "sword_blade_bind")

    defender = battle.ai_memory["d"]
    attacker = battle.ai_memory["a"]
    assert defender.defence_outcomes == ["parry"]
    assert attacker.feints_used == ["sword_blade_bind"]
    assert attacker.last_target_id == "d"


@pytest.mark.unit
def test_record_updates_sticky_target_even_without_feint() -> None:
    battle = _battle([_actor("a"), _actor("d", team="blue")])
    record_exchange_outcome(battle, "a", "d", "hit", None)
    assert battle.ai_memory["a"].last_target_id == "d"
    assert battle.ai_memory["a"].feints_used == []


@pytest.mark.unit
def test_record_silent_no_op_on_missing_ids() -> None:
    battle = _battle([_actor("a")])
    record_exchange_outcome(battle, None, "d", "hit", None)
    record_exchange_outcome(battle, "a", None, "hit", None)
    record_exchange_outcome(None, "a", "d", "hit", None)
    assert battle.ai_memory == {}


@pytest.mark.unit
def test_record_ignores_non_resolver_outcomes_for_defence() -> None:
    """The hook is called for every exchange; only outcomes that belong to
    the resolver's defence vocabulary contribute to the defender's history."""
    battle = _battle([_actor("a"), _actor("d", team="blue")])
    record_exchange_outcome(battle, "a", "d", "heal", None)
    record_exchange_outcome(battle, "a", "d", "none", None)
    # Defender's history stays empty; attacker still recorded the sticky target.
    assert battle.ai_memory.get("d", AiMemoryDTO()).defence_outcomes == []
    assert battle.ai_memory["a"].last_target_id == "d"


@pytest.mark.unit
def test_defence_outcomes_rolls_at_window_size() -> None:
    battle = _battle([_actor("a"), _actor("d", team="blue")])
    for _ in range(DEFENCE_MEMORY_WINDOW + 3):
        record_exchange_outcome(battle, "a", "d", "parry", None)
    assert len(battle.ai_memory["d"].defence_outcomes) == DEFENCE_MEMORY_WINDOW


@pytest.mark.unit
def test_feints_used_rolls_at_window_size() -> None:
    battle = _battle([_actor("a"), _actor("d", team="blue")])
    for i in range(FEINT_MEMORY_WINDOW + 4):
        record_exchange_outcome(battle, "a", "d", "hit", f"feint_{i}")
    assert len(battle.ai_memory["a"].feints_used) == FEINT_MEMORY_WINDOW
    # Newest at right end — last id must be the most recently recorded one.
    assert battle.ai_memory["a"].feints_used[-1] == f"feint_{FEINT_MEMORY_WINDOW + 3}"


# ---------------------------------------------------------------------------
# defence_rate / get_memory
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_defence_rate_zero_on_empty_memory() -> None:
    assert defence_rate(AiMemoryDTO(), "parry") == 0.0


@pytest.mark.unit
def test_defence_rate_uses_window_size_denominator() -> None:
    memory = AiMemoryDTO(defence_outcomes=["parry", "parry", "hit", "dodge"])
    assert defence_rate(memory, "parry") == pytest.approx(0.5)
    assert defence_rate(memory, "dodge") == pytest.approx(0.25)
    assert defence_rate(memory, "block") == pytest.approx(0.0)


@pytest.mark.unit
def test_get_memory_returns_empty_for_unknown_actor() -> None:
    battle = _battle([_actor("a")])
    assert get_memory(battle, "ghost").defence_outcomes == []
    assert get_memory(None, "a").last_target_id is None


# ---------------------------------------------------------------------------
# Observation extraction with memory
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_extract_target_populates_observed_rates_from_memory() -> None:
    target = _actor("t", team="blue")
    memory = AiMemoryDTO(
        defence_outcomes=["parry", "parry", "hit", "dodge", "block", "hit", "miss", "parry"]
    )
    obs = extract_target(target, memory=memory)
    assert obs.observed_parry_rate == pytest.approx(3 / 8)
    assert obs.observed_dodge_rate == pytest.approx(1 / 8)
    assert obs.observed_block_rate == pytest.approx(1 / 8)


@pytest.mark.unit
def test_extract_target_defaults_rates_to_zero_without_memory() -> None:
    obs = extract_target(_actor("t", team="blue"))
    assert obs.observed_parry_rate == 0.0
    assert obs.observed_dodge_rate == 0.0
    assert obs.observed_block_rate == 0.0


@pytest.mark.unit
def test_extract_self_populates_last_target_and_recent_feints() -> None:
    bot = _actor("bot")
    memory = AiMemoryDTO(
        feints_used=["sword_blade_bind", "sword_low_angle"],
        last_target_id="t1",
    )
    obs = extract_self(bot, alive_enemy_count=1, memory=memory)
    assert obs.last_target_id == "t1"
    assert obs.recently_used_feints == frozenset({"sword_blade_bind", "sword_low_angle"})


# ---------------------------------------------------------------------------
# Scorer branches
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scorer_observed_parry_rate_amplifies_anti_parry() -> None:
    bot = _actor("bot")
    target = _actor("t", team="blue")
    base_obs = extract_target(target)  # observed_parry_rate = 0
    memory = AiMemoryDTO(defence_outcomes=["parry"] * 4 + ["hit"] * 4)  # 0.5 parry rate
    memorised_obs = extract_target(target, memory=memory)

    policy = Policy.with_defaults(
        {
            "anti_parry": 0.0,  # isolate observed-rate contribution
            "observed_parry_rate": 2.0,
            "expected_damage": 0.0,
            "damage_tag": 0.0,
            "randomness": 0.0,
        }
    )
    self_obs = extract_self(bot, alive_enemy_count=1)
    action = LegalAction(
        "attack", "t", "sword_blade_bind", tags=frozenset({"anti_parry", "damage_tag"})
    )

    score_no_memory = PolicyScorer.score(self_obs, base_obs, action, policy)
    score_with_memory = PolicyScorer.score(self_obs, memorised_obs, action, policy)
    # Diff = observed_parry_rate weight × observed rate = 2.0 * 0.5 = 1.0.
    assert score_with_memory - score_no_memory == pytest.approx(1.0)


@pytest.mark.unit
def test_scorer_sticky_target_bonus_applies_only_to_last_target() -> None:
    bot = _actor("bot")
    target_obs = extract_target(_actor("focus", team="blue"))

    policy = Policy.with_defaults(
        {
            "sticky_target_bonus": 0.5,
            "expected_damage": 0.0,
            "damage_tag": 0.0,
            "randomness": 0.0,
        }
    )
    obs_sticky = extract_self(
        bot, alive_enemy_count=2, memory=AiMemoryDTO(last_target_id="focus")
    )
    obs_other = extract_self(
        bot, alive_enemy_count=2, memory=AiMemoryDTO(last_target_id="other")
    )
    action = LegalAction("attack", "focus", None, tags=frozenset({"damage_tag"}))

    score_match = PolicyScorer.score(obs_sticky, target_obs, action, policy)
    score_other = PolicyScorer.score(obs_other, target_obs, action, policy)
    assert score_match - score_other == pytest.approx(0.5)


@pytest.mark.unit
def test_scorer_repeat_feint_penalty_subtracts_for_recently_used_feint() -> None:
    bot = _actor("bot")
    target_obs = extract_target(_actor("t", team="blue"))

    policy = Policy.with_defaults(
        {
            "repeat_feint_penalty": 0.7,
            "expected_damage": 0.0,
            "damage_tag": 0.0,
            "randomness": 0.0,
        }
    )
    memory = AiMemoryDTO(feints_used=["sword_blade_bind"])
    self_obs_repeat = extract_self(bot, alive_enemy_count=1, memory=memory)
    self_obs_fresh = extract_self(bot, alive_enemy_count=1)

    repeat_action = LegalAction(
        "attack", "t", "sword_blade_bind", tags=frozenset({"damage_tag"})
    )
    fresh_action = LegalAction(
        "attack", "t", "sword_low_angle", tags=frozenset({"damage_tag"})
    )

    # Same action vs no memory: penalty kicks in.
    assert PolicyScorer.score(self_obs_repeat, target_obs, repeat_action, policy) == pytest.approx(
        PolicyScorer.score(self_obs_fresh, target_obs, repeat_action, policy) - 0.7
    )
    # Same memory, different feint id: no penalty.
    assert PolicyScorer.score(self_obs_repeat, target_obs, fresh_action, policy) == pytest.approx(
        PolicyScorer.score(self_obs_fresh, target_obs, fresh_action, policy)
    )


@pytest.mark.unit
def test_scorer_repeat_feint_penalty_skips_basic_attack() -> None:
    """A plain basic attack (feint_id=None) must never trigger the repeat
    penalty even if it matches a remembered feint slot."""
    bot = _actor("bot")
    target_obs = extract_target(_actor("t", team="blue"))
    policy = Policy.with_defaults(
        {
            "repeat_feint_penalty": 100.0,
            "expected_damage": 0.0,
            "damage_tag": 0.0,
            "randomness": 0.0,
        }
    )
    obs = extract_self(
        bot, alive_enemy_count=1, memory=AiMemoryDTO(feints_used=["any"])
    )
    obs_clean = extract_self(bot, alive_enemy_count=1)
    basic = LegalAction("attack", "t", None, tags=frozenset({"damage_tag"}))
    assert PolicyScorer.score(obs, target_obs, basic, policy) == pytest.approx(
        PolicyScorer.score(obs_clean, target_obs, basic, policy)
    )


# ---------------------------------------------------------------------------
# Default policy carries non-zero weights.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_default_policy_exposes_memory_weights() -> None:
    from src.backend.features.combat.runtime.ai.policy_store import PolicyStore

    policy = PolicyStore().load()
    assert policy.get("observed_parry_rate") > 0.0
    assert policy.get("observed_evasion_rate") > 0.0
    assert policy.get("observed_block_rate") > 0.0
    assert policy.get("sticky_target_bonus") > 0.0
    assert policy.get("repeat_feint_penalty") > 0.0


# ---------------------------------------------------------------------------
# End-to-end: brain reads memory via get_memory and behaves accordingly.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_brain_reads_memory_through_battle_context() -> None:
    """After three recorded exchanges where target parried every time, the
    scorer's anti_parry contribution against that target rises (compared to
    a battle without any memory)."""
    from src.backend.features.combat.runtime.ai.brain import MonsterCombatBrain

    bot = _actor("bot")
    target = _actor("t", team="blue")
    battle = _battle([bot, target])
    for _ in range(4):
        record_exchange_outcome(battle, "bot", "t", "parry", "sword_blade_bind")

    # Sanity: memory exists.
    assert battle.ai_memory["t"].defence_outcomes.count("parry") == 4

    # decide_exchange runs end-to-end without raising and produces a payload.
    brain = MonsterCombatBrain()
    payload = brain.decide_exchange(bot, target, battle)
    assert payload["target_id"] == "t"

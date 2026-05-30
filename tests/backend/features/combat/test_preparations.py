"""Tests for preparation-aware extraction and scorer branches (PR2)."""

from __future__ import annotations

import pytest

from src.backend.features.combat.dto.actor import (
    ActiveEffectDTO,
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    ActorStats,
    ActorStatusesDTO,
    FeintHandDTO,
)
from src.backend.features.combat.runtime.ai.action_space import LegalAction
from src.backend.features.combat.runtime.ai.observation import extract_self, extract_target
from src.backend.features.combat.runtime.ai.policy import Policy
from src.backend.features.combat.runtime.ai.preparations import (
    COUNTER_ON_HIT_PREPS,
    DAMAGE_REDUCTION_PREPS,
    FORCED_DEFENCE_PREPS,
    HEAL_PREPS,
    THREATENING_PREPS,
    extract_preparations,
)
from src.backend.features.combat.runtime.ai.scorer import PolicyScorer
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


def _effect(effect_id: str) -> ActiveEffectDTO:
    return ActiveEffectDTO(
        uid=f"uid_{effect_id}",
        effect_id=effect_id,
        source_id="self",
        expire_at_exchange=99,
    )


def _actor(
    actor_id: str,
    *,
    team: str = "red",
    effect_ids: list[str] | None = None,
    mods: dict[str, float] | None = None,
    hp: int = 100,
    max_hp: int = 100,
) -> ActorSnapshot:
    effects = [_effect(eid) for eid in (effect_ids or [])]
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
            stamina=50,
            max_stamina=50,
            tactics=0,
            tokens={},
            feints=FeintHandDTO(hand={}, arsenal=[]),
        ),
        raw=ActorRawDTO(),
        skills={},
        loadout=ActorLoadoutDTO(),
        stats=ActorStats(mods=CombatModifiersDTO(**(mods or {})), skills=CombatSkillsDTO()),
        statuses=ActorStatusesDTO(effects=effects),
    )


# ---------------------------------------------------------------------------
# Static set contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_threatening_preps_is_union_of_three_groups() -> None:
    assert THREATENING_PREPS == (
        COUNTER_ON_HIT_PREPS | DAMAGE_REDUCTION_PREPS | FORCED_DEFENCE_PREPS
    )


@pytest.mark.unit
def test_counter_on_hit_includes_perfect_riposte_and_2h_answering_stance() -> None:
    assert "prep_perfect_riposte" in COUNTER_ON_HIT_PREPS
    assert "prep_2h_answering_stance" in COUNTER_ON_HIT_PREPS


@pytest.mark.unit
def test_heal_preps_contains_second_breath_and_perfect_riposte() -> None:
    assert HEAL_PREPS == frozenset({"prep_second_breath", "prep_perfect_riposte"})


# ---------------------------------------------------------------------------
# extract_preparations
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_extract_preparations_filters_by_prefix() -> None:
    actor = _actor(
        "a",
        effect_ids=["prep_counter_on_dodge", "bleed", "prep_active_defense", "stun"],
    )
    assert extract_preparations(actor) == frozenset(
        {"prep_counter_on_dodge", "prep_active_defense"}
    )


@pytest.mark.unit
def test_extract_preparations_empty_when_no_effects() -> None:
    actor = _actor("a")
    assert extract_preparations(actor) == frozenset()


@pytest.mark.unit
def test_extract_self_populates_my_preparations() -> None:
    bot = _actor("bot", effect_ids=["prep_foresight_parry"])
    obs = extract_self(bot, alive_enemy_count=1)
    assert obs.my_preparations == frozenset({"prep_foresight_parry"})


@pytest.mark.unit
def test_extract_target_populates_active_preparations() -> None:
    target = _actor("t", effect_ids=["prep_counter_on_dodge"])
    obs = extract_target(target)
    assert obs.active_preparations == frozenset({"prep_counter_on_dodge"})


# ---------------------------------------------------------------------------
# Scorer: prep_threat_penalty
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scorer_subtracts_prep_threat_when_attacking_through_counter_prep() -> None:
    """Attacking a target with ``prep_counter_on_dodge`` (no dispel) must
    be scored lower than attacking a clean target — same action, same target
    stats — by exactly ``prep_threat_penalty``.
    """
    threatened = _actor("threat", effect_ids=["prep_counter_on_dodge"])
    clean = _actor("clean")
    bot = _actor("bot")
    self_obs = extract_self(bot, alive_enemy_count=1)

    policy = Policy.with_defaults(
        {
            "prep_threat_penalty": 1.5,
            # Zero noise / damage so the only contribution to score-diff is
            # the prep branch.
            "expected_damage": 0.0,
            "damage_tag": 0.0,
            "randomness": 0.0,
        }
    )

    action = LegalAction("attack", "t", None, tags=frozenset({"damage_tag"}))
    score_threatened = PolicyScorer.score(self_obs, extract_target(threatened), action, policy)
    score_clean = PolicyScorer.score(self_obs, extract_target(clean), action, policy)
    assert score_threatened == pytest.approx(score_clean - 1.5)


@pytest.mark.unit
def test_scorer_does_not_penalise_dispel_action_against_threatening_prep() -> None:
    target = _actor("t", effect_ids=["prep_counter_on_dodge"])
    bot = _actor("bot")
    self_obs = extract_self(bot, alive_enemy_count=1)
    target_obs = extract_target(target)

    policy = Policy.with_defaults(
        {
            "prep_threat_penalty": 5.0,
            "dispel_prep": 0.0,
            "expected_damage": 0.0,
            "damage_tag": 0.0,
            "randomness": 0.0,
        }
    )

    plain = LegalAction("attack", "t", None, tags=frozenset({"damage_tag"}))
    dispel = LegalAction(
        "attack", "t", "read_tactic", tags=frozenset({"damage_tag", "dispel_prep"})
    )
    plain_score = PolicyScorer.score(self_obs, target_obs, plain, policy)
    dispel_score = PolicyScorer.score(self_obs, target_obs, dispel, policy)
    assert dispel_score > plain_score


# ---------------------------------------------------------------------------
# Scorer: dispel_prep stacks with number of active preps
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scorer_dispel_bonus_scales_with_number_of_active_preps() -> None:
    one_prep = _actor("a", effect_ids=["prep_active_defense"])
    three_preps = _actor(
        "b",
        effect_ids=["prep_active_defense", "prep_foresight_parry", "prep_counter_on_dodge"],
    )
    bot = _actor("bot")
    self_obs = extract_self(bot, alive_enemy_count=1)

    policy = Policy.with_defaults(
        {
            "dispel_prep": 2.0,
            "prep_threat_penalty": 0.0,
            "expected_damage": 0.0,
            "damage_tag": 0.0,
            "randomness": 0.0,
        }
    )

    action = LegalAction("attack", "x", None, tags=frozenset({"dispel_prep"}))
    one_score = PolicyScorer.score(self_obs, extract_target(one_prep), action, policy)
    three_score = PolicyScorer.score(self_obs, extract_target(three_preps), action, policy)
    # dispel_prep weight * count, so the diff is exactly 2 * 2.0.
    assert three_score - one_score == pytest.approx(4.0)


@pytest.mark.unit
def test_scorer_dispel_bonus_is_zero_when_target_has_no_preps() -> None:
    clean = _actor("c")
    bot = _actor("bot")
    self_obs = extract_self(bot, alive_enemy_count=1)
    target_obs = extract_target(clean)

    policy = Policy.with_defaults(
        {
            "dispel_prep": 10.0,
            "prep_threat_penalty": 0.0,
            "expected_damage": 0.0,
            "damage_tag": 0.0,
            "randomness": 0.0,
        }
    )
    with_dispel = LegalAction("attack", "c", None, tags=frozenset({"dispel_prep"}))
    without_dispel = LegalAction("attack", "c", None, tags=frozenset())
    assert PolicyScorer.score(self_obs, target_obs, with_dispel, policy) == pytest.approx(
        PolicyScorer.score(self_obs, target_obs, without_dispel, policy)
    )


# ---------------------------------------------------------------------------
# Scorer: heal_dedup_penalty
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scorer_penalises_heal_when_bot_already_has_heal_prep() -> None:
    """If the bot already has ``prep_second_breath`` queued, a second heal
    feint must be scored *strictly below* the same heal feint when the bot
    has no active heal prep — by exactly ``heal_dedup_penalty``.
    """
    bot_with_prep = _actor("bot_a", effect_ids=["prep_second_breath"], hp=40, max_hp=100)
    bot_clean = _actor("bot_b", hp=40, max_hp=100)
    target = _actor("t")
    target_obs = extract_target(target)

    policy = Policy.with_defaults(
        {
            "heal": 1.0,
            "heal_dedup_penalty": 2.5,
            "expected_damage": 0.0,
            "damage_tag": 0.0,
            "randomness": 0.0,
            "self_buff": 0.0,
        }
    )

    heal_action = LegalAction("attack", "t", "second_breath", tags=frozenset({"heal"}))
    score_with_prep = PolicyScorer.score(
        extract_self(bot_with_prep, alive_enemy_count=1), target_obs, heal_action, policy
    )
    score_clean = PolicyScorer.score(
        extract_self(bot_clean, alive_enemy_count=1), target_obs, heal_action, policy
    )
    assert score_clean - score_with_prep == pytest.approx(2.5)


@pytest.mark.unit
def test_scorer_no_heal_dedup_when_active_prep_is_not_a_heal_prep() -> None:
    """``prep_active_defense`` is a damage-reduction prep, not a heal prep —
    a heal feint must NOT trigger the dedup penalty against it."""
    bot = _actor("bot", effect_ids=["prep_active_defense"], hp=40, max_hp=100)
    clean = _actor("bot_clean", hp=40, max_hp=100)
    target = _actor("t")
    target_obs = extract_target(target)
    policy = Policy.with_defaults(
        {
            "heal": 1.0,
            "heal_dedup_penalty": 10.0,
            "expected_damage": 0.0,
            "damage_tag": 0.0,
            "randomness": 0.0,
        }
    )

    heal_action = LegalAction("attack", "t", "second_breath", tags=frozenset({"heal"}))
    assert PolicyScorer.score(
        extract_self(bot, alive_enemy_count=1), target_obs, heal_action, policy
    ) == pytest.approx(
        PolicyScorer.score(
            extract_self(clean, alive_enemy_count=1), target_obs, heal_action, policy
        )
    )


# ---------------------------------------------------------------------------
# Default policy carries non-zero weights for new keys.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_default_policy_exposes_prep_aware_weights() -> None:
    from src.backend.features.combat.runtime.ai.policy_store import PolicyStore

    policy = PolicyStore().load()
    assert policy.get("prep_threat_penalty") > 0.0
    assert policy.get("dispel_prep") > 0.0
    assert policy.get("heal_dedup_penalty") > 0.0

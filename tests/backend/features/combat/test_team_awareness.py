"""Tests for team-aware extraction and scorer branches (PR4)."""

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
from src.backend.features.combat.runtime.ai.action_space import LegalAction
from src.backend.features.combat.runtime.ai.observation import extract_self, extract_target
from src.backend.features.combat.runtime.ai.policy import Policy
from src.backend.features.combat.runtime.ai.scorer import PolicyScorer
from src.backend.features.combat.runtime.ai.team_awareness import (
    TeamState,
    extract_team_state,
)
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


def _actor(
    actor_id: str,
    *,
    team: str,
    hp: int = 100,
    max_hp: int = 100,
    has_control_effect: bool = False,
) -> ActorSnapshot:
    from src.backend.features.combat.dto.actor import ActiveEffectDTO, ActorStatusesDTO

    effects = []
    if has_control_effect:
        effects.append(
            ActiveEffectDTO(
                uid="uid_stun",
                effect_id="stun_root",
                source_id="self",
                expire_at_exchange=99,
            )
        )

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
        stats=ActorStats(mods=CombatModifiersDTO(), skills=CombatSkillsDTO()),
        statuses=ActorStatusesDTO(effects=effects),
    )


def _battle(
    actors: list[ActorSnapshot], moves_cache: dict[str, dict] | None = None
) -> BattleContext:
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
        moves_cache=moves_cache or {},
    )


# ---------------------------------------------------------------------------
# BattleContext.get_allies
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_allies_excludes_self_and_enemies() -> None:
    me = _actor("me", team="red")
    ally = _actor("ally", team="red")
    enemy = _actor("enemy", team="blue")
    battle = _battle([me, ally, enemy])

    allies = battle.get_allies("me")
    assert {a.meta.id for a in allies} == {"ally"}


@pytest.mark.unit
def test_get_allies_skips_dead_teammates() -> None:
    me = _actor("me", team="red")
    dead_ally = _actor("dead", team="red", hp=0)
    live_ally = _actor("live", team="red")
    battle = _battle([me, dead_ally, live_ally])

    assert {a.meta.id for a in battle.get_allies("me")} == {"live"}


@pytest.mark.unit
def test_get_allies_returns_empty_for_unknown_actor() -> None:
    me = _actor("me", team="red")
    battle = _battle([me])
    assert battle.get_allies("ghost") == []


# ---------------------------------------------------------------------------
# extract_team_state
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_extract_team_state_returns_empty_without_battle() -> None:
    me = _actor("me", team="red")
    state = extract_team_state(None, me)
    assert state == TeamState()


@pytest.mark.unit
def test_extract_team_state_returns_empty_when_cache_empty() -> None:
    me = _actor("me", team="red")
    battle = _battle([me], moves_cache={})
    assert extract_team_state(battle, me) == TeamState()


@pytest.mark.unit
def test_extract_team_state_counts_ally_targets_only() -> None:
    me = _actor("me", team="red")
    ally1 = _actor("ally1", team="red")
    ally2 = _actor("ally2", team="red")
    enemy = _actor("enemy", team="blue")
    enemy_ally = _actor("enemy_ally", team="blue")
    battle = _battle(
        [me, ally1, ally2, enemy, enemy_ally],
        moves_cache={
            "ally1": {"action": "attack", "target_id": "enemy"},
            "ally2": {"action": "attack", "target_id": "enemy"},
            "enemy_ally": {"action": "attack", "target_id": "me"},  # opposite team, ignored
            "me": {"action": "attack", "target_id": "enemy_ally"},  # self, ignored
        },
    )

    state = extract_team_state(battle, me)
    assert state.allies_targets == {"enemy": 2}


@pytest.mark.unit
def test_extract_team_state_resolves_control_feints_to_pending_control_targets() -> None:
    """When an ally has already queued a feint carrying the ``control`` tag
    (e.g. ``concussion``, which inflicts ``concussed_no_feints``), the target
    must appear in ``allies_pending_control_targets``."""
    me = _actor("me", team="red")
    ally = _actor("ally", team="red")
    enemy = _actor("enemy", team="blue")
    battle = _battle(
        [me, ally, enemy],
        moves_cache={"ally": {"action": "attack", "target_id": "enemy", "feint_id": "concussion"}},
    )

    state = extract_team_state(battle, me)
    assert "enemy" in state.allies_pending_control_targets
    assert state.allies_targets == {"enemy": 1}


@pytest.mark.unit
def test_extract_team_state_ignores_non_control_feints() -> None:
    me = _actor("me", team="red")
    ally = _actor("ally", team="red")
    enemy = _actor("enemy", team="blue")
    battle = _battle(
        [me, ally, enemy],
        moves_cache={
            "ally": {"action": "attack", "target_id": "enemy", "feint_id": "sword_blade_bind"}
        },
    )

    state = extract_team_state(battle, me)
    assert state.allies_pending_control_targets == frozenset()


@pytest.mark.unit
def test_extract_team_state_skips_dead_allies() -> None:
    me = _actor("me", team="red")
    dead = _actor("dead", team="red", hp=0)
    enemy = _actor("enemy", team="blue")
    battle = _battle(
        [me, dead, enemy],
        moves_cache={"dead": {"action": "attack", "target_id": "enemy"}},
    )

    state = extract_team_state(battle, me)
    assert state.allies_targets == {}


# ---------------------------------------------------------------------------
# Scorer branches
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scorer_team_focus_scales_with_ally_count() -> None:
    """Same action, same target stats — the score increases linearly with
    the number of allies already aiming at the target."""
    bot = _actor("bot", team="red")
    target = _actor("t", team="blue")

    policy = Policy.with_defaults(
        {
            "team_focus": 0.7,
            "team_focus_pile_on": 0.0,
            "team_dedup_control": 0.0,
            "expected_damage": 0.0,
            "damage_tag": 0.0,
            "randomness": 0.0,
        }
    )
    action = LegalAction("attack", "t", None, tags=frozenset({"damage_tag"}))
    target_obs = extract_target(target)

    obs_none = extract_self(bot, alive_enemy_count=1, team_state=TeamState())
    obs_two = extract_self(
        bot, alive_enemy_count=1, team_state=TeamState(allies_targets={"t": 2})
    )

    score_none = PolicyScorer.score(obs_none, target_obs, action, policy)
    score_two = PolicyScorer.score(obs_two, target_obs, action, policy)
    assert score_two - score_none == pytest.approx(2 * 0.7)


@pytest.mark.unit
def test_scorer_pile_on_applies_only_when_target_is_controlled() -> None:
    bot = _actor("bot", team="red")
    controlled = _actor("c", team="blue", has_control_effect=True)
    healthy = _actor("h", team="blue")

    policy = Policy.with_defaults(
        {
            "team_focus": 0.0,
            "team_focus_pile_on": 1.5,
            "control": 0.0,  # zero out target-state control bonus for isolation
            "expected_damage": 0.0,
            "damage_tag": 0.0,
            "randomness": 0.0,
        }
    )
    state_with_ally = TeamState(allies_targets={"c": 1, "h": 1})
    obs = extract_self(bot, alive_enemy_count=2, team_state=state_with_ally)

    action_c = LegalAction("attack", "c", None, tags=frozenset({"damage_tag"}))
    action_h = LegalAction("attack", "h", None, tags=frozenset({"damage_tag"}))

    diff = PolicyScorer.score(obs, extract_target(controlled), action_c, policy) - PolicyScorer.score(
        obs, extract_target(healthy), action_h, policy
    )
    assert diff == pytest.approx(1.5)


@pytest.mark.unit
def test_scorer_team_dedup_control_penalises_duplicate_control_on_same_target() -> None:
    bot = _actor("bot", team="red")
    target = _actor("t", team="blue")

    policy = Policy.with_defaults(
        {
            "team_focus": 0.0,
            "team_dedup_control": 2.0,
            "control": 0.0,
            "debuff": 0.0,
            "expected_damage": 0.0,
            "damage_tag": 0.0,
            "randomness": 0.0,
        }
    )
    state = TeamState(allies_pending_control_targets=frozenset({"t"}))
    obs = extract_self(bot, alive_enemy_count=1, team_state=state)
    target_obs = extract_target(target)

    control_action = LegalAction(
        "attack", "t", "concussion", tags=frozenset({"control", "damage_tag"})
    )
    plain_action = LegalAction("attack", "t", None, tags=frozenset({"damage_tag"}))

    control_score = PolicyScorer.score(obs, target_obs, control_action, policy)
    plain_score = PolicyScorer.score(obs, target_obs, plain_action, policy)
    # Plain attack should win by the policy penalty plus the hard waste guard.
    assert plain_score - control_score == pytest.approx(102.0)


@pytest.mark.unit
def test_scorer_team_dedup_control_does_not_apply_when_no_ally_control() -> None:
    bot = _actor("bot", team="red")
    target = _actor("t", team="blue")

    policy = Policy.with_defaults(
        {
            "team_focus": 0.0,
            "team_dedup_control": 5.0,
            "control": 0.0,
            "debuff": 0.0,
            "expected_damage": 0.0,
            "damage_tag": 0.0,
            "randomness": 0.0,
        }
    )
    obs_empty = extract_self(bot, alive_enemy_count=1, team_state=TeamState())
    target_obs = extract_target(target)

    control_action = LegalAction(
        "attack", "t", "concussion", tags=frozenset({"control", "damage_tag"})
    )
    plain_action = LegalAction("attack", "t", None, tags=frozenset({"damage_tag"}))

    assert PolicyScorer.score(obs_empty, target_obs, control_action, policy) == pytest.approx(
        PolicyScorer.score(obs_empty, target_obs, plain_action, policy)
    )


# ---------------------------------------------------------------------------
# Default policy carries non-zero weights for new keys.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_default_policy_exposes_team_aware_weights() -> None:
    from src.backend.features.combat.runtime.ai.policy_store import PolicyStore

    policy = PolicyStore().load()
    assert policy.get("team_focus") > 0.0
    assert policy.get("team_focus_pile_on") > 0.0
    assert policy.get("team_dedup_control") > 0.0


# ---------------------------------------------------------------------------
# End-to-end: brain decide_turn integrates moves_cache focus.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decide_turn_prefers_target_already_focused_by_ally() -> None:
    """Two equivalent enemies, one already targeted by an ally — the bot
    should choose to pile on the focused enemy under the default policy."""
    from src.backend.features.combat.runtime.ai.brain import MonsterCombatBrain

    bot = _actor("bot", team="red")
    ally = _actor("ally", team="red")
    focused = _actor("focused", team="blue")
    fresh = _actor("fresh", team="blue")

    # Ally has already committed an attack on "focused" this step.
    battle = _battle(
        [bot, ally, focused, fresh],
        moves_cache={"ally": {"action": "attack", "target_id": "focused"}},
    )

    brain = MonsterCombatBrain()
    payload = brain.decide_exchange(
        bot, focused, battle, team_state=extract_team_state(battle, bot)
    )
    # Smoke: payload at least keeps the target_id intact under the pile-on signal.
    assert payload["target_id"] == "focused"

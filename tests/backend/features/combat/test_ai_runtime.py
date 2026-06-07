"""Tests for the runtime combat AI package.

Covers observation extraction, legal-action enumeration, scorer behaviour
under the post-overhaul feint catalog, the per-exchange decide_exchange
contract, planning-budget semantics of decide_turn, and the policy store
fallback chain.

The product-level contracts asserted here:

* A dodger target draws the anti_evasion feint.
* A blocker target draws the anti_block feint.
* A finishable target (low HP) gets a basic attack, not an expensive feint.
* decide_turn never over-commits stamina across the batch.
* With zero stamina the brain emits only basic attacks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.backend.features.combat.dto.actor import (
    ActiveEffectDTO,
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    ActorStats,
    FeintHandDTO,
)
from src.backend.features.combat.dto.session import BattleContext, BattleMeta
from src.backend.features.combat.runtime.ai import MonsterCombatBrain, Policy, PolicyStore
from src.backend.features.combat.runtime.ai.action_space import (
    LegalAction,
    build_legal_actions_for_target,
    build_legal_instant_actions_for_target,
)
from src.backend.features.combat.runtime.ai.observation import extract_self, extract_target
from src.backend.features.combat.runtime.ai.scorer import PolicyScorer
from src.backend.features.combat.runtime.ai.team_awareness import TeamState
from src.backend.features.combat.runtime.engine.feint_service import FeintService
from src.backend.features.combat.runtime.processors.ai_processor import AiProcessor
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


def _actor(
    actor_id: str,
    *,
    team: str,
    hp: int = 100,
    max_hp: int = 100,
    stamina: int = 50,
    max_stamina: int = 50,
    tokens: dict[str, int] | None = None,
    hand: dict[str, dict[str, int]] | None = None,
    mods: dict[str, float] | None = None,
    skills: dict[str, float] | None = None,
    layout: dict[str, str] | None = None,
    ranged_position: str | None = None,
    is_ai: bool = False,
    known_abilities: list[str] | None = None,
) -> ActorSnapshot:
    feints = FeintHandDTO(hand=dict(hand or {}), arsenal=list((hand or {}).keys()))
    meta = ActorMetaDTO(
        id=actor_id,
        name=actor_id,
        type="monster" if is_ai else "player",
        team=team,
        is_ai=is_ai,
        hp=hp,
        max_hp=max_hp,
        en=10,
        max_en=10,
        stamina=stamina,
        max_stamina=max_stamina,
        tactics=0,
        tokens=dict(tokens or {}),
        feints=feints,
    )
    stats = ActorStats(
        mods=CombatModifiersDTO(**(mods or {})),
        skills=CombatSkillsDTO(**(skills or {})),
    )
    effects = []
    if ranged_position is not None:
        effects.append(
            ActiveEffectDTO(
                uid=f"ranged_position:{actor_id}",
                effect_id="ranged_position",
                source_id=actor_id,
                active_from_exchange=0,
                expire_at_exchange=99,
                params={"position": ranged_position},
            )
        )
    return ActorSnapshot(
        meta=meta,
        raw=ActorRawDTO(),
        skills={},
        loadout=ActorLoadoutDTO(layout=dict(layout or {}), known_abilities=list(known_abilities or [])),
        statuses={"effects": effects},
        stats=stats,
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
# Observation extraction
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_observation_target_features_match_known_stats() -> None:
    target = _actor(
        "t1", team="blue", hp=20, max_hp=80, mods={"armor": 12.0, "evasion": 0.3, "parry": 0.1, "block": 0.4}
    )
    obs = extract_target(target)

    assert obs.hp_pct == pytest.approx(0.25)
    assert obs.armor == pytest.approx(12.0)
    assert obs.evasion == pytest.approx(0.3)
    assert obs.parry == pytest.approx(0.1)
    assert obs.block == pytest.approx(0.4)
    assert obs.finishable is True  # 0.25 boundary inclusive


@pytest.mark.unit
def test_observation_uses_effective_evasion_after_dodge_cap() -> None:
    target = _actor("t1", team="blue", mods={"evasion": 0.90, "dodge_cap": 0.35})

    obs = extract_target(target)

    assert obs.evasion == pytest.approx(0.35)


@pytest.mark.unit
def test_observation_exposes_ranged_position_and_shield_guard_contracts() -> None:
    archer = _actor(
        "archer",
        team="blue",
        layout={"main_hand": "skill_archery", "tactical_style": "skill_ranged_combat"},
        skills={"skill_ranged_combat": 0.7},
        ranged_position="close",
    )
    shield = _actor(
        "shield",
        team="blue",
        layout={"off_hand": "skill_shield_mastery", "tactical_style": "skill_shield_mastery"},
        mods={"shield_guard_power": 24.0, "counter_attack_chance": 0.6},
        skills={"skill_shield_mastery": 0.8},
    )

    archer_obs = extract_target(archer)
    shield_obs = extract_target(shield)

    assert archer_obs.is_ranged_style is True
    assert archer_obs.ranged_position == "close"
    assert shield_obs.is_shield_style is True
    assert shield_obs.shield_guard_power == pytest.approx(24.0)
    assert shield_obs.shield_mastery == pytest.approx(0.8)


@pytest.mark.unit
def test_observation_self_features_include_resources_and_enemy_count() -> None:
    bot = _actor(
        "bot", team="red", is_ai=True, hp=30, max_hp=100, stamina=10, max_stamina=50, tokens={"hit": 2}
    )
    obs = extract_self(bot, alive_enemy_count=3)

    assert obs.hp_pct == pytest.approx(0.3)
    assert obs.stamina_pct == pytest.approx(0.2)
    assert obs.low_hp is True
    assert obs.low_stamina is True
    assert obs.tokens == {"hit": 2}
    assert obs.alive_enemy_count == 3


# ---------------------------------------------------------------------------
# Legal actions
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_legal_actions_include_basic_and_each_affordable_hand_feint() -> None:
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        stamina=50,
        hand={
            "sword_blade_bind": {"hit": 3, "parry": 2},
            "sword_low_angle": {"hit": 3, "dodge": 2},
        },
    )
    target = _actor("t1", team="blue")
    actions = build_legal_actions_for_target(bot, target)

    feint_ids = {a.feint_id for a in actions}
    assert None in feint_ids
    assert "sword_blade_bind" in feint_ids
    assert "sword_low_angle" in feint_ids
    assert len(actions) == 3


@pytest.mark.unit
def test_legal_actions_exclude_feints_when_stamina_insufficient() -> None:
    # 5 tokens * 3 = 15 stamina required; bot has only 10.
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        stamina=10,
        max_stamina=60,
        hand={"sword_blade_bind": {"hit": 3, "parry": 2}},
    )
    target = _actor("t1", team="blue")
    actions = build_legal_actions_for_target(bot, target)

    assert len(actions) == 1
    assert actions[0].feint_id is None
    assert actions[0].action_type == "attack"


@pytest.mark.unit
def test_legal_instant_actions_include_affordable_known_abilities() -> None:
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        stamina=20,
        tokens={"blood": 3, "block": 1, "gift": 1, "tempo": 3, "hit": 2},
        known_abilities=["basic_wipe_blood", "basic_break_stance"],
    )
    bot.meta.en = 20
    target = _actor("t1", team="blue")

    actions = build_legal_instant_actions_for_target(bot, target)

    by_id = {action.ability_id: action for action in actions}
    assert set(by_id) == {"basic_wipe_blood", "basic_break_stance"}
    assert by_id["basic_wipe_blood"].target_id == "bot"
    assert by_id["basic_wipe_blood"].energy_cost == 5
    assert by_id["basic_wipe_blood"].stamina_cost == 0
    assert by_id["basic_wipe_blood"].cost == {"blood": 3, "block": 1, "gift": 1}
    assert {"heal", "blood"} <= set(by_id["basic_wipe_blood"].tags)
    assert by_id["basic_break_stance"].target_id == "t1"
    assert by_id["basic_break_stance"].energy_cost == 0
    assert by_id["basic_break_stance"].stamina_cost == 0


@pytest.mark.unit
def test_legal_instant_actions_exclude_abilities_when_combat_tokens_are_missing() -> None:
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        tokens={"blood": 1},
        known_abilities=["basic_break_stance"],
    )
    bot.meta.en = 20
    target = _actor("t1", team="blue")

    assert build_legal_instant_actions_for_target(bot, target) == []


@pytest.mark.unit
def test_legal_instant_actions_exclude_abilities_on_cooldown() -> None:
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        tokens={"tempo": 3, "hit": 2},
        known_abilities=["basic_break_stance"],
    )
    bot.meta.en = 20
    bot.meta.exchange_counter = 1
    bot.meta.ability_cooldowns["basic_break_stance"] = 2
    target = _actor("t1", team="blue")

    assert build_legal_instant_actions_for_target(bot, target) == []


@pytest.mark.unit
def test_legal_instant_actions_allow_token_abilities_without_stamina() -> None:
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        stamina=0,
        tokens={"tempo": 3, "hit": 2},
        known_abilities=["basic_break_stance"],
    )
    bot.meta.en = 20
    target = _actor("t1", team="blue")

    actions = build_legal_instant_actions_for_target(bot, target)

    assert [action.ability_id for action in actions] == ["basic_break_stance"]
    assert actions[0].stamina_cost == 0


# ---------------------------------------------------------------------------
# Scorer: anti-defence axes
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scorer_prefers_anti_block_against_high_block_target() -> None:
    target = _actor("t1", team="blue", mods={"block": 0.6})
    bot = _actor("bot", team="red", is_ai=True)
    target_obs = extract_target(target)
    self_obs = extract_self(bot, alive_enemy_count=1)

    policy = Policy.with_defaults(
        {"anti_block": 2.0, "damage_tag": 0.5, "stamina_cost": 0.0, "token_cost": 0.0}
    )

    basic = LegalAction(action_type="attack", target_id="t1", feint_id=None, tags=frozenset({"damage_tag"}))
    anti_block = LegalAction(
        action_type="attack",
        target_id="t1",
        feint_id="sword_low_angle",
        cost={"hit": 3, "dodge": 2},
        stamina_cost=15,
        tags=frozenset({"anti_block", "damage_tag"}),
    )

    score_basic = PolicyScorer.score(self_obs, target_obs, basic, policy)
    score_anti = PolicyScorer.score(self_obs, target_obs, anti_block, policy)
    assert score_anti > score_basic


@pytest.mark.unit
def test_scorer_prefers_ranged_reposition_when_archer_is_close() -> None:
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        layout={"main_hand": "skill_archery", "tactical_style": "skill_ranged_combat"},
        ranged_position="close",
    )
    target = _actor("shield", team="blue", mods={"counter_attack_chance": 0.6})
    self_obs = extract_self(bot, alive_enemy_count=1)
    target_obs = extract_target(target)
    policy = Policy.with_defaults(
        {
            "damage_tag": 0.2,
            "ranged_reposition": 3.0,
            "ranged_keep_far": 2.0,
            "ranged_position_damage": 1.0,
            "token_cost": 0.0,
            "stamina_cost": 0.0,
        }
    )

    basic = LegalAction("attack", "shield", None, tags=frozenset({"damage_tag"}))
    open_distance = LegalAction(
        "attack",
        "shield",
        "open_distance",
        cost={"dodge": 5, "tempo": 2},
        stamina_cost=21,
        tags=frozenset({"ranged_reposition", "ranged_keep_far"}),
    )

    assert PolicyScorer.score(self_obs, target_obs, open_distance, policy) > PolicyScorer.score(
        self_obs, target_obs, basic, policy
    )


@pytest.mark.unit
def test_scorer_prefers_armor_bypass_against_shield_guard_target() -> None:
    bot = _actor("bot", team="red", is_ai=True)
    shield = _actor(
        "shield",
        team="blue",
        layout={"off_hand": "skill_shield_mastery", "tactical_style": "skill_shield_mastery"},
        mods={"shield_guard_power": 30.0, "armor": 5.0},
        skills={"skill_shield_mastery": 0.9},
    )
    self_obs = extract_self(bot, alive_enemy_count=1)
    target_obs = extract_target(shield)
    policy = Policy.with_defaults({"armor_bypass": 3.0, "damage_tag": 0.2, "token_cost": 0.0, "stamina_cost": 0.0})

    basic = LegalAction("attack", "shield", None, tags=frozenset({"damage_tag"}))
    armor_bypass = LegalAction(
        "attack",
        "shield",
        "macing_armor_crush",
        cost={"hit": 3, "crit": 2},
        stamina_cost=15,
        tags=frozenset({"armor_bypass", "damage_tag"}),
    )

    assert PolicyScorer.score(self_obs, target_obs, armor_bypass, policy) > PolicyScorer.score(
        self_obs, target_obs, basic, policy
    )


@pytest.mark.unit
def test_scorer_prefers_finishable_target_for_same_action() -> None:
    low_hp_target = _actor("low", team="blue", hp=15)
    healthy_target = _actor("high", team="blue", hp=95)
    bot = _actor("bot", team="red", is_ai=True)
    self_obs = extract_self(bot, alive_enemy_count=2)

    policy = Policy.with_defaults({"finishable": 3.0, "damage_tag": 0.5})

    action_low = LegalAction("attack", "low", None, tags=frozenset({"damage_tag"}))
    action_high = LegalAction("attack", "high", None, tags=frozenset({"damage_tag"}))

    score_low = PolicyScorer.score(self_obs, extract_target(low_hp_target), action_low, policy)
    score_high = PolicyScorer.score(self_obs, extract_target(healthy_target), action_high, policy)
    assert score_low > score_high


@pytest.mark.unit
def test_high_token_cost_makes_basic_attack_win_over_feint() -> None:
    target = _actor("t1", team="blue", mods={"block": 0.4})
    bot = _actor("bot", team="red", is_ai=True)
    target_obs = extract_target(target)
    self_obs = extract_self(bot, alive_enemy_count=1)

    policy = Policy.with_defaults(
        {"anti_block": 0.5, "damage_tag": 0.3, "token_cost": -3.0, "stamina_cost": 0.0}
    )

    basic = LegalAction("attack", "t1", None, tags=frozenset({"damage_tag"}))
    feint = LegalAction(
        "attack",
        "t1",
        "sword_blade_bind",
        cost={"hit": 3, "parry": 2},
        stamina_cost=15,
        tags=frozenset({"anti_block", "damage_tag"}),
    )

    assert PolicyScorer.score(self_obs, target_obs, basic, policy) > PolicyScorer.score(
        self_obs, target_obs, feint, policy
    )


@pytest.mark.unit
def test_non_execute_feint_is_blocked_on_finishable_target_even_with_group_bonus() -> None:
    target = _actor("t1", team="blue", hp=10, max_hp=100)
    bot = _actor("bot", team="red", is_ai=True)
    target_obs = extract_target(target)
    self_obs = extract_self(bot, alive_enemy_count=1)

    policy = Policy.with_defaults(
        {
            "damage_tag": 0.5,
            "group_basic": 10.0,
            "finishable_resource_save": 0.0,
            "token_cost": 0.0,
            "stamina_cost": 0.0,
        }
    )

    basic = LegalAction("attack", "t1", None, tags=frozenset({"damage_tag"}))
    feint = LegalAction(
        "attack",
        "t1",
        "measured_strike",
        cost={"hit": 3},
        stamina_cost=9,
        tags=frozenset({"damage_tag", "group_basic"}),
    )

    assert PolicyScorer.score(self_obs, target_obs, basic, policy) > PolicyScorer.score(
        self_obs, target_obs, feint, policy
    )


@pytest.mark.unit
def test_execute_feint_is_penalized_before_finishable_window() -> None:
    target = _actor("t1", team="blue", hp=80, max_hp=100)
    bot = _actor("bot", team="red", is_ai=True)
    target_obs = extract_target(target)
    self_obs = extract_self(bot, alive_enemy_count=1)

    policy = Policy.with_defaults(
        {
            "damage_tag": 0.5,
            "group_weapon": 10.0,
            "token_cost": 0.0,
            "stamina_cost": 0.0,
        }
    )

    basic = LegalAction("attack", "t1", None, tags=frozenset({"damage_tag"}))
    execute_feint = LegalAction(
        "attack",
        "t1",
        "sword_clean_path",
        cost={"hit": 3, "crit": 5},
        stamina_cost=24,
        tags=frozenset({"damage_tag", "execute", "group_weapon"}),
    )

    assert PolicyScorer.score(self_obs, target_obs, basic, policy) > PolicyScorer.score(
        self_obs, target_obs, execute_feint, policy
    )


@pytest.mark.unit
def test_duplicate_control_is_blocked_even_with_large_control_bonus() -> None:
    target = _actor("t1", team="blue")
    bot = _actor("bot", team="red", is_ai=True)
    target_obs = extract_target(target)
    self_obs = extract_self(
        bot,
        alive_enemy_count=1,
        team_state=TeamState(
            allies_targets={"t1": 1},
            allies_pending_control_targets=frozenset({"t1"}),
        ),
    )

    policy = Policy.with_defaults(
        {
            "damage_tag": 0.5,
            "control": 50.0,
            "team_dedup_control": 0.0,
            "token_cost": 0.0,
            "stamina_cost": 0.0,
        }
    )

    basic = LegalAction("attack", "t1", None, tags=frozenset({"damage_tag"}))
    duplicate_control = LegalAction(
        "attack",
        "t1",
        "concussion",
        cost={"block": 3},
        stamina_cost=9,
        tags=frozenset({"control", "damage_tag"}),
    )

    assert PolicyScorer.score(self_obs, target_obs, basic, policy) > PolicyScorer.score(
        self_obs, target_obs, duplicate_control, policy
    )


# ---------------------------------------------------------------------------
# Product contracts on the brain (decide_exchange)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decide_exchange_picks_anti_evasion_feint_against_dodger() -> None:
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},  # basic, no defence tag
            "sword_low_angle": {"hit": 3, "dodge": 2},  # weapon, anti_evasion via dodge token
        },
    )
    target = _actor("dodger", team="blue", hp=80, mods={"evasion": 0.5, "block": 0.05, "parry": 0.05})
    battle = _battle([bot, target])

    brain = MonsterCombatBrain()  # bundled default_policy
    payload = brain.decide_exchange(bot, target, battle)

    assert payload["target_id"] == "dodger"
    assert payload.get("feint_id") == "sword_low_angle"


@pytest.mark.unit
def test_decide_exchange_picks_anti_parry_feint_against_blocker() -> None:
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "sword_blade_bind": {"hit": 3, "parry": 2},  # anti_parry via parry token
        },
    )
    target = _actor("parry_master", team="blue", hp=80, mods={"parry": 0.5, "block": 0.05})
    battle = _battle([bot, target])

    brain = MonsterCombatBrain()  # bundled default_policy
    payload = brain.decide_exchange(bot, target, battle)

    assert payload["target_id"] == "parry_master"
    assert payload.get("feint_id") == "sword_blade_bind"


@pytest.mark.unit
def test_decide_exchange_avoids_expensive_feint_on_dying_target() -> None:
    """3-HP target → basic attack, not the expensive feint.

    With ``finishable_resource_save`` negative and `finishable` constant
    bonus applied to any action, the cheap basic attack must outscore the
    expensive feint against a target already in the finishing window.
    """
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},  # cheap basic
            "sword_blade_bind": {"hit": 3, "parry": 2},  # would normally win on parry, but target is dying
        },
    )
    target = _actor("dying_blocker", team="blue", hp=3, max_hp=100, mods={"parry": 0.6})
    battle = _battle([bot, target])

    brain = MonsterCombatBrain()  # bundled default_policy
    payload = brain.decide_exchange(bot, target, battle)

    assert payload["target_id"] == "dying_blocker"
    assert "feint_id" not in payload


# ---------------------------------------------------------------------------
# decide_turn: planning-budget semantics
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decide_turn_does_not_overcommit_stamina_across_targets() -> None:
    """Anchor test for the planning-budget contract.

    Bot has stamina 60. Two targets both ideal for an anti_parry feint that
    costs 5 tokens × 3 = 15 stamina each. With two such feints the bot can
    only pay 30 stamina total, which is fine. But with one expensive
    (sword_clean_path, 8 tokens × 3 = 24 stam) and one cheaper
    (sword_blade_bind, 15 stam), the planner must pick actions that fit the
    budget, not greedily overcommit expensive actions.
    """
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},  # cheap basic, 9 stam
            "sword_clean_path": {"hit": 3, "crit": 5},  # expensive, 24 stam
            "sword_blade_bind": {"hit": 3, "parry": 2},  # mid, 15 stam, anti_parry
        },
    )
    t1 = _actor("t1", team="blue", hp=80, mods={"parry": 0.55})
    t2 = _actor("t2", team="blue", hp=80, mods={"parry": 0.55})
    battle = _battle([bot, t1, t2])

    brain = MonsterCombatBrain()
    payloads = brain.decide_turn(bot, battle, [t1, t2])

    # Budget contract: total planned stamina ≤ original 60.
    total_stamina = 0
    for payload in payloads:
        feint_id = payload.get("feint_id")
        if not feint_id:
            continue
        # In a real flow the cost dict would come from catalog; in the test
        # bot hand we know each feint's cost.
        cost = bot.meta.feints.hand.get(feint_id) or {
            "sword_clean_path": {"hit": 3, "crit": 5},
            "sword_blade_bind": {"hit": 3, "parry": 2},
            "measured_strike": {"hit": 3},
        }[feint_id]
        total_stamina += FeintService.activation_stamina_cost(cost)

    assert total_stamina <= 60, (
        f"Planner over-committed stamina: {total_stamina} > 60. Payloads: {payloads}"
    )

    # And the original bot snapshot must NOT have been mutated by planning.
    assert int(bot.meta.stamina) == 60
    assert "sword_clean_path" in bot.meta.feints.hand
    assert "sword_blade_bind" in bot.meta.feints.hand


@pytest.mark.unit
def test_decide_turn_can_emit_instant_before_exchange_without_consuming_the_turn() -> None:
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        hp=25,
        max_hp=100,
        tokens={"blood": 3, "block": 1, "gift": 1},
        known_abilities=["basic_wipe_blood"],
    )
    bot.meta.en = 20
    target = _actor("t1", team="blue")
    battle = _battle([bot, target])
    policy = Policy.with_defaults({"heal": 8.0, "token_cost": 0.0, "blood_resource": 0.0, "expected_damage": 0.0})

    payloads = MonsterCombatBrain(policy=policy).decide_turn(bot, battle, [target])

    assert payloads == [
        {"action": "instant", "target_id": "bot", "ability_id": "basic_wipe_blood"},
        {"action": "attack", "target_id": "t1"},
    ]
    assert bot.meta.tokens == {"blood": 3, "block": 1, "gift": 1}
    assert bot.meta.en == 20


@pytest.mark.unit
def test_decide_turn_does_not_overcommit_instant_resources_across_targets() -> None:
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        hp=25,
        max_hp=100,
        tokens={"blood": 3, "block": 1, "gift": 1},
        known_abilities=["basic_wipe_blood"],
    )
    bot.meta.en = 20
    t1 = _actor("t1", team="blue")
    t2 = _actor("t2", team="blue")
    battle = _battle([bot, t1, t2])
    policy = Policy.with_defaults({"heal": 8.0, "token_cost": 0.0, "blood_resource": 0.0, "expected_damage": 0.0})

    payloads = MonsterCombatBrain(policy=policy).decide_turn(bot, battle, [t1, t2])

    assert [payload.get("ability_id") for payload in payloads if payload.get("action") == "instant"] == [
        "basic_wipe_blood"
    ]
    assert [payload["target_id"] for payload in payloads if payload.get("action") == "attack"] == ["t1", "t2"]


@pytest.mark.unit
def test_decide_turn_does_not_use_the_same_feint_twice() -> None:
    """Across a batch the same feint id must not appear twice."""
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "sword_blade_bind": {"hit": 3, "parry": 2},
        },
    )
    t1 = _actor("t1", team="blue", hp=80, mods={"parry": 0.55})
    t2 = _actor("t2", team="blue", hp=80, mods={"parry": 0.55})
    battle = _battle([bot, t1, t2])

    payloads = MonsterCombatBrain().decide_turn(bot, battle, [t1, t2])
    chosen_feints = [p.get("feint_id") for p in payloads if p.get("feint_id")]
    assert len(chosen_feints) == len(set(chosen_feints)), (
        f"Same feint emitted twice: {payloads}"
    )


@pytest.mark.unit
def test_decide_turn_with_zero_initial_stamina_emits_only_basic_attacks() -> None:
    """Alternate path: stamina=0 → no feint candidates clear the filter."""
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        stamina=0,
        max_stamina=60,
        hand={
            "sword_blade_bind": {"hit": 3, "parry": 2},
            "sword_low_angle": {"hit": 3, "dodge": 2},
        },
    )
    targets = [_actor(f"t{i}", team="blue", mods={"parry": 0.5}) for i in range(3)]
    battle = _battle([bot, *targets])

    payloads = MonsterCombatBrain().decide_turn(bot, battle, targets)

    assert len(payloads) == 3
    for payload in payloads:
        assert "feint_id" not in payload
        assert payload["action"] == "attack"


# ---------------------------------------------------------------------------
# Payload shape / AiProcessor wiring
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decide_turn_emits_one_payload_per_target() -> None:
    bot = _actor("bot", team="red", is_ai=True)
    targets = [_actor(f"t{i}", team="blue") for i in range(3)]
    battle = _battle([bot, *targets])

    payloads = AiProcessor().decide_turn(bot, battle, targets)
    assert len(payloads) == 3
    target_ids = {p["target_id"] for p in payloads}
    assert target_ids == {"t0", "t1", "t2"}


@pytest.mark.unit
def test_payload_shape_is_turn_manager_compatible() -> None:
    bot = _actor(
        "bot", team="red", is_ai=True, hand={"sword_blade_bind": {"hit": 3, "parry": 2}}
    )
    target = _actor("t1", team="blue", mods={"parry": 0.5})
    battle = _battle([bot, target])

    payloads = AiProcessor().decide_turn(bot, battle, [target])
    assert payloads, "Expected at least one payload"
    for payload in payloads:
        assert payload["action"] == "attack"
        assert "target_id" in payload
        assert set(payload.keys()) <= {"action", "target_id", "feint_id"}


@pytest.mark.unit
def test_decide_exchange_returns_legacy_payload_shape() -> None:
    bot = _actor("bot", team="red", is_ai=True)
    target = _actor("t1", team="blue")

    payload = AiProcessor().decide_exchange(bot, target)
    assert payload["action"] == "attack"
    assert payload["target_id"] == "t1"


@pytest.mark.unit
def test_brain_caches_default_archetype_policy_per_instance() -> None:
    class CountingPolicyStore:
        def __init__(self) -> None:
            self.calls: list[str | None] = []

        def load(self, path=None, *, archetype=None, policy_id=None):  # noqa: ANN001, ANN202
            self.calls.append(archetype)
            return Policy.with_defaults(policy_id=f"policy-{archetype or 'base'}")

    store = CountingPolicyStore()
    brain = MonsterCombatBrain(policy_store=store)  # type: ignore[arg-type]
    bot = _actor("bot", team="red", is_ai=True)
    bot.meta.ai_archetype = "duelist"
    target = _actor("t1", team="blue")
    battle = _battle([bot, target])

    brain.decide_exchange(bot, target, battle)
    brain.decide_exchange(bot, target, battle)
    brain.decide_turn(bot, battle, [target])

    assert store.calls == ["duelist"]


# ---------------------------------------------------------------------------
# PolicyStore
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_policy_store_loads_bundled_default() -> None:
    store = PolicyStore()
    policy = store.load()
    assert policy.policy_id
    assert isinstance(policy.weights, dict)
    assert policy.get("finishable") >= 0.0


@pytest.mark.unit
def test_policy_store_loads_explicit_path(tmp_path: Path) -> None:
    custom = Policy.with_defaults({"finishable": 9.0}, policy_id="custom_v1")
    target_path = tmp_path / "custom.json"
    custom.write(target_path)

    loaded = PolicyStore().load(target_path)
    assert loaded.policy_id == "custom_v1"
    assert loaded.get("finishable") == pytest.approx(9.0)


@pytest.mark.unit
def test_policy_store_falls_back_to_default_on_malformed_external(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")

    fallback = PolicyStore().load(bad)
    assert isinstance(fallback.weights, dict)
    assert fallback.get("randomness") >= 0.0


@pytest.mark.unit
def test_policy_round_trips_through_json(tmp_path: Path) -> None:
    policy = Policy.with_defaults({"target_low_hp": 2.0}, policy_id="rt", version=2)
    path = tmp_path / "policy.json"
    policy.write(path)

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["policy_id"] == "rt"
    assert raw["version"] == 2
    reloaded = Policy.from_path(path)
    assert reloaded.get("target_low_hp") == pytest.approx(2.0)

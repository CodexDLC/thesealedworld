"""Tests for the runtime combat AI package.

Covers observation extraction, legal-action enumeration, scorer behaviour,
greedy resource allocation, and the policy store fallback chain.
"""

from __future__ import annotations

import json
from pathlib import Path

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
from src.backend.features.combat.runtime.ai import MonsterCombatBrain, Policy, PolicyStore
from src.backend.features.combat.runtime.ai.action_space import (
    LegalAction,
    build_legal_actions_for_target,
)
from src.backend.features.combat.runtime.ai.observation import extract_self, extract_target
from src.backend.features.combat.runtime.ai.scorer import PolicyScorer
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
    is_ai: bool = False,
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
        skills=CombatSkillsDTO(),
    )
    return ActorSnapshot(
        meta=meta,
        raw=ActorRawDTO(),
        skills={},
        loadout=ActorLoadoutDTO(),
        stats=stats,
    )


def _battle(actors: list[ActorSnapshot]) -> BattleContext:
    return BattleContext(
        session_id="t1",
        meta=BattleMeta(
            active=1,
            step_counter=0,
            active_actors_count=len(actors),
            teams={"red": [a.meta.id for a in actors if a.meta.team == "red"], "blue": [a.meta.id for a in actors if a.meta.team == "blue"]},
            battle_type="arena",
            location_id="arena",
        ),
        actors={str(a.meta.id): a for a in actors},
    )


# ---------------------------------------------------------------------------
# 1. Observation extraction
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_observation_target_features_match_known_stats() -> None:
    target = _actor("t1", team="blue", hp=20, max_hp=80, mods={"armor": 12.0, "evasion": 0.3, "parry": 0.1, "block": 0.4})
    obs = extract_target(target)

    assert obs.hp_pct == pytest.approx(0.25)
    assert obs.armor == pytest.approx(12.0)
    assert obs.evasion == pytest.approx(0.3)
    assert obs.parry == pytest.approx(0.1)
    assert obs.block == pytest.approx(0.4)
    assert obs.finishable is True  # 0.25 boundary inclusive


@pytest.mark.unit
def test_observation_self_features_include_resources_and_enemy_count() -> None:
    bot = _actor("bot", team="red", is_ai=True, hp=30, max_hp=100, stamina=10, max_stamina=50, tokens={"hit": 2})
    obs = extract_self(bot, alive_enemy_count=3)

    assert obs.hp_pct == pytest.approx(0.3)
    assert obs.stamina_pct == pytest.approx(0.2)
    assert obs.low_hp is True
    assert obs.low_stamina is True
    assert obs.tokens == {"hit": 2}
    assert obs.alive_enemy_count == 3


# ---------------------------------------------------------------------------
# 2-3. Legal actions: include basic + affordable feints, exclude unaffordable
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
    assert None in feint_ids  # basic attack always present
    assert "sword_blade_bind" in feint_ids
    assert "sword_low_angle" in feint_ids
    assert len(actions) == 3


@pytest.mark.unit
def test_legal_actions_exclude_feints_when_stamina_insufficient() -> None:
    # 5 tokens * 5 = 25 stamina required; bot has only 10.
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


# ---------------------------------------------------------------------------
# 4. Scorer prefers anti_block tag against high-block target
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scorer_prefers_anti_block_against_high_block_target() -> None:
    target = _actor("t1", team="blue", mods={"block": 0.6})
    bot = _actor("bot", team="red", is_ai=True)
    target_obs = extract_target(target)
    self_obs = extract_self(bot, alive_enemy_count=1)

    policy = Policy.with_defaults({"anti_block": 2.0, "damage_tag": 0.5, "stamina_cost": 0.0, "token_cost": 0.0})

    basic = LegalAction(action_type="attack", target_id="t1", feint_id=None, tags=frozenset({"damage_tag"}))
    anti_block = LegalAction(
        action_type="attack",
        target_id="t1",
        feint_id="sword_low_angle",
        cost={"hit": 3, "dodge": 2},
        stamina_cost=25,
        tags=frozenset({"anti_block", "damage_tag"}),
    )

    score_basic = PolicyScorer.score(self_obs, target_obs, basic, policy)
    score_anti = PolicyScorer.score(self_obs, target_obs, anti_block, policy)
    assert score_anti > score_basic


# ---------------------------------------------------------------------------
# 5. Scorer prefers low-hp / finishable target across the population.
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 6. High cost flips the choice toward basic attack.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_high_token_cost_makes_basic_attack_win_over_feint() -> None:
    target = _actor("t1", team="blue", mods={"block": 0.4})
    bot = _actor("bot", team="red", is_ai=True)
    target_obs = extract_target(target)
    self_obs = extract_self(bot, alive_enemy_count=1)

    policy = Policy.with_defaults({"anti_block": 0.5, "damage_tag": 0.3, "token_cost": -3.0, "stamina_cost": 0.0})

    basic = LegalAction("attack", "t1", None, tags=frozenset({"damage_tag"}))
    feint = LegalAction(
        "attack",
        "t1",
        "sword_blade_bind",
        cost={"hit": 3, "parry": 2},
        stamina_cost=25,
        tags=frozenset({"anti_block", "damage_tag"}),
    )

    assert PolicyScorer.score(self_obs, target_obs, basic, policy) > PolicyScorer.score(
        self_obs, target_obs, feint, policy
    )


# ---------------------------------------------------------------------------
# 7. Greedy allocation prefers high-defence target for the only feint.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_greedy_allocator_sends_anti_parry_feint_to_high_parry_target() -> None:
    bot = _actor(
        "bot",
        team="red",
        is_ai=True,
        hand={"sword_blade_bind": {"hit": 3, "parry": 2}},
    )
    high_parry = _actor("hp", team="blue", mods={"parry": 0.5})
    low_def = _actor("ld", team="blue", mods={"parry": 0.05})
    battle = _battle([bot, high_parry, low_def])

    policy = Policy.with_defaults(
        {
            "anti_parry": 2.0,
            "damage_tag": 0.5,
            "token_cost": -0.1,
            "stamina_cost": -0.01,
        }
    )
    brain = MonsterCombatBrain(policy=policy)

    payloads = brain.decide_turn(bot, battle, [high_parry, low_def])
    by_target = {p["target_id"]: p for p in payloads}

    assert by_target["hp"].get("feint_id") == "sword_blade_bind"
    assert "feint_id" not in by_target["ld"]


# ---------------------------------------------------------------------------
# 8. decide_turn emits one payload per target.
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


# ---------------------------------------------------------------------------
# 9. Payload shape stays TurnManager-compatible.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_payload_shape_is_turn_manager_compatible() -> None:
    bot = _actor("bot", team="red", is_ai=True, hand={"sword_blade_bind": {"hit": 3, "parry": 2}})
    target = _actor("t1", team="blue", mods={"parry": 0.5})
    battle = _battle([bot, target])

    payloads = AiProcessor().decide_turn(bot, battle, [target])
    assert payloads, "Expected at least one payload"
    for payload in payloads:
        assert payload["action"] == "attack"
        assert "target_id" in payload
        assert set(payload.keys()) <= {"action", "target_id", "feint_id"}


# ---------------------------------------------------------------------------
# 10. decide_exchange backward compatibility.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decide_exchange_returns_legacy_payload_shape() -> None:
    bot = _actor("bot", team="red", is_ai=True)
    target = _actor("t1", team="blue")

    payload = AiProcessor().decide_exchange(bot, target)
    assert payload["action"] == "attack"
    assert payload["target_id"] == "t1"


# ---------------------------------------------------------------------------
# 11. PolicyStore: default, explicit path, malformed → fallback.
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
    # The default policy uses a specific id; either way we should get a valid policy.
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

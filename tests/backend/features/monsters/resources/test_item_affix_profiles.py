import pytest

from src.backend.features.items.resources.affixes.catalog import AFFIX_CATALOG
from src.backend.features.monsters.resources.item_affix_profiles import (
    MONSTER_AFFIX_POOLS,
    get_monster_affix_count,
    get_monster_affix_pool,
    get_monster_affix_step_count,
    get_monster_allowed_affixes,
    get_monster_boss_forced_affixes,
)


@pytest.mark.unit
def test_monster_affix_profiles_reference_existing_affixes() -> None:
    missing = [
        (family_id, item_kind, affix_id)
        for family_id, pools in MONSTER_AFFIX_POOLS.items()
        for item_kind, affix_ids in pools.items()
        for affix_id in affix_ids
        if affix_id not in AFFIX_CATALOG
    ]

    assert missing == []


@pytest.mark.unit
def test_monster_affix_profiles_have_enough_choice_for_mvp_pools() -> None:
    for family_id, pools in MONSTER_AFFIX_POOLS.items():
        assert len(pools["weapon"]) >= 4
        assert len(pools["armor"]) >= 6
        if family_id in {"bandit_gang", "goblin_tribe"}:
            assert len(pools["shield"]) >= 6


@pytest.mark.unit
def test_monster_affix_policy_counts_and_steps_match_current_balance_rule() -> None:
    assert get_monster_affix_count("minion") == 1
    assert get_monster_affix_count("veteran") == 2
    assert get_monster_affix_count("elite") == 3
    assert get_monster_affix_count("boss") == 4

    assert get_monster_affix_step_count(0) == 2
    assert get_monster_affix_step_count(1) == 3
    assert get_monster_affix_step_count(4) == 7
    assert get_monster_affix_step_count(7) == 14


@pytest.mark.unit
def test_monster_affix_profiles_expose_family_pool_and_boss_forced_sets() -> None:
    assert "crit_chance" in get_monster_affix_pool("rat_swarm", "weapon")
    assert get_monster_affix_pool("rat_swarm", "shield") == ()
    assert get_monster_boss_forced_affixes("rat_swarm", "main_hand") == (
        "weapon_accuracy",
        "crit_chance",
        "armor_penetration_bonus",
        "control_chance_bonus",
    )


@pytest.mark.unit
def test_monster_weapon_affix_pool_is_slot_aware_for_off_hand_accuracy() -> None:
    assert "off_hand_accuracy" not in get_monster_allowed_affixes("rat_swarm", "weapon", "main_hand")
    assert "off_hand_accuracy" in get_monster_allowed_affixes("rat_swarm", "weapon", "off_hand")

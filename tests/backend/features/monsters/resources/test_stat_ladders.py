import pytest

from src.backend.features.monsters.resources import get_family_config, get_starter_family_ids
from src.backend.features.monsters.resources.stat_ladders import (
    ATTRIBUTE_LADDER,
    ORGANIZATION_ATTRIBUTE_OFFSETS,
    ROLE_ATTRIBUTE_BASE,
    role_attribute_base,
)


@pytest.mark.unit
def test_starter_monster_stats_use_role_ladder_contract() -> None:
    expected_ladder = sorted(ATTRIBUTE_LADDER)

    for family_id in get_starter_family_ids():
        family = get_family_config(family_id)
        assert family is not None

        for variant in family.variants.values():
            role_base = role_attribute_base(variant.role, family.organization_type)
            values = variant.base_stats.model_dump(mode="json").values()

            assert sorted(value - role_base for value in values) == expected_ladder


@pytest.mark.unit
def test_starter_monster_role_stat_totals_include_organization_mass_offset() -> None:
    expected_neutral_totals = {
        "minion": 99,
        "veteran": 108,
        "elite": 117,
        "boss": 162,
    }

    for family_id in get_starter_family_ids():
        family = get_family_config(family_id)
        assert family is not None

        for variant in family.variants.values():
            organization_offset = 0 if variant.role == "boss" else ORGANIZATION_ATTRIBUTE_OFFSETS[family.organization_type]
            assert (
                sum(variant.base_stats.model_dump(mode="json").values())
                == expected_neutral_totals[variant.role] + organization_offset * len(ATTRIBUTE_LADDER)
            )


@pytest.mark.unit
def test_monster_role_bases_are_player_baseline_offsets() -> None:
    assert ROLE_ATTRIBUTE_BASE == {
        "minion": 6,
        "veteran": 7,
        "elite": 8,
        "boss": 13,
    }
    assert ORGANIZATION_ATTRIBUTE_OFFSETS == {
        "swarm": -2,
        "horde": -1,
        "pack": 0,
        "gang": 1,
        "solitary": 2,
    }
    assert role_attribute_base("minion", "swarm") == 4
    assert role_attribute_base("minion", "gang") == 7
    assert role_attribute_base("elite", "horde") == 7
    assert role_attribute_base("boss", "swarm") == 13

import pytest

from src.backend.features.monsters.resources import get_family_config, get_starter_family_ids
from src.backend.features.monsters.resources.stat_ladders import ATTRIBUTE_LADDER, ROLE_ATTRIBUTE_BASE


@pytest.mark.unit
def test_starter_monster_stats_use_role_ladder_contract() -> None:
    expected_ladder = sorted(ATTRIBUTE_LADDER)

    for family_id in get_starter_family_ids():
        family = get_family_config(family_id)
        assert family is not None

        for variant in family.variants.values():
            role_base = ROLE_ATTRIBUTE_BASE[variant.role]
            values = variant.base_stats.model_dump(mode="json").values()

            assert sorted(value - role_base for value in values) == expected_ladder


@pytest.mark.unit
def test_starter_monster_role_stat_totals_are_fixed() -> None:
    expected_totals = {
        "minion": 81,
        "veteran": 99,
        "elite": 117,
        "boss": 153,
    }

    for family_id in get_starter_family_ids():
        family = get_family_config(family_id)
        assert family is not None

        for variant in family.variants.values():
            assert sum(variant.base_stats.model_dump(mode="json").values()) == expected_totals[variant.role]

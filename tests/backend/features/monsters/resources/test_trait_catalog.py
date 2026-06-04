from __future__ import annotations

from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.resources.traits import (
    MONSTER_CLAN_TRAIT_CATALOG_VERSION,
    get_monster_clan_trait_catalog,
    select_monster_clan_traits,
)


def test_trait_catalog_keys_conflicts_and_modifier_targets_are_valid() -> None:
    catalog = get_monster_clan_trait_catalog()

    assert MONSTER_CLAN_TRAIT_CATALOG_VERSION >= 1
    assert 8 <= len(catalog) <= 20
    assert len(catalog) == len({trait.key for trait in catalog})
    catalog_keys = {trait.key for trait in catalog}
    for trait in catalog:
        assert trait.weight > 0
        assert set(trait.conflicts) <= catalog_keys
        assert trait.modifiers
        for modifier in trait.modifiers:
            assert modifier.normalized_target


def test_trait_selection_is_deterministic_and_limited_to_two_traits() -> None:
    family = get_family_config("rat_swarm")
    assert family is not None

    first = select_monster_clan_traits(
        family,
        biome_id="city_ruins",
        context_tags=["sewer", "rot", "disease", "rat_swarm"],
        seed="rat-city-sewer",
    )
    second = select_monster_clan_traits(
        family,
        biome_id="city_ruins",
        context_tags=["disease", "rot", "sewer", "rat_swarm"],
        seed="rat-city-sewer",
    )

    assert [trait.key for trait in first] == [trait.key for trait in second]
    assert 1 <= len(first) <= 2
    assert any({"plague", "rot", "swarm"} & set(trait.tags) for trait in first)


def test_trait_selection_respects_family_and_archetype_denies() -> None:
    wolf_family = get_family_config("wolf_pack")
    bandit_family = get_family_config("bandit_gang")
    assert wolf_family is not None
    assert bandit_family is not None

    wolves = select_monster_clan_traits(
        wolf_family,
        biome_id="outer_wall",
        context_tags=["bastion", "guard_ruins", "wolf_pack"],
        seed="wolf-wall",
    )
    bandits = select_monster_clan_traits(
        bandit_family,
        biome_id="outer_wall",
        context_tags=["bastion", "guard_ruins", "bandit_gang"],
        seed="bandit-wall",
    )

    assert "fortified_scavengers" not in {trait.key for trait in wolves}
    assert "fortified_scavengers" in {trait.key for trait in bandits}

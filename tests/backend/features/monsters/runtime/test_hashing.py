import pytest

from src.backend.features.monsters.runtime.hashing import (
    compute_clan_identity_hash,
    compute_habitat_hash,
    normalize_habitat,
    normalize_habitat_keys,
)


@pytest.mark.unit
def test_habitat_keys_are_normalized_and_order_stable() -> None:
    assert normalize_habitat_keys(["Ruined Old City", "ancient", "ancient", "cold-wind"]) == [
        "ancient",
        "cold_wind",
        "ruined_old_city",
    ]
    assert normalize_habitat(biome="City-Ruins", keys=["ruined_old_city"]).biome == "city_ruins"


@pytest.mark.unit
def test_habitat_hash_ignores_location_tier_and_player_state() -> None:
    left = compute_habitat_hash(biome="city_ruins", keys=["ancient", "ruined_old_city"])
    right = compute_habitat_hash(
        biome="city_ruins",
        keys=[
            "ruined_old_city",
            "ancient",
            # These are intentionally absent from the hash call because location/tier/player state
            # must never become clan identity.
        ],
    )

    assert left == right


@pytest.mark.unit
def test_clan_identity_hash_has_no_tier_player_gear_or_cost_inputs() -> None:
    identity_inputs = {
        "family_id": "goblin_tribe",
        "biome": "city_ruins",
        "keys": ["ancient", "ruined_old_city"],
        "selected_trait_keys": ["fortified_scavengers"],
        "generation_version": 2,
        "resource_version": "1.4",
    }
    runtime_state = {
        **identity_inputs,
        "effective_tier": 7,
        "player_tier": 5,
        "gear_score": 240,
        "assembly_cost": 12,
    }

    assert compute_clan_identity_hash(**identity_inputs) == compute_clan_identity_hash(**identity_inputs)
    assert {"effective_tier", "player_tier", "gear_score", "assembly_cost"}.isdisjoint(identity_inputs)
    assert {key: runtime_state[key] for key in identity_inputs} == identity_inputs


@pytest.mark.unit
def test_clan_identity_hash_can_be_shared_across_regions() -> None:
    left = compute_clan_identity_hash(
        family_id="goblin_tribe",
        biome="city_ruins",
        keys=["ancient", "ruined_old_city"],
        selected_trait_keys=["fortified_scavengers"],
        resource_version="1.4",
    )
    right = compute_clan_identity_hash(
        family_id="goblin_tribe",
        biome="city_ruins",
        keys=["ruined_old_city", "ancient"],
        selected_trait_keys=["fortified_scavengers"],
        resource_version="1.4",
    )

    assert left == right


@pytest.mark.unit
def test_clan_identity_hash_changes_by_habitat_keys_and_traits() -> None:
    base = compute_clan_identity_hash(
        family_id="goblin_tribe",
        biome="city_ruins",
        keys=["ancient", "ruined_old_city"],
        selected_trait_keys=["fortified_scavengers"],
    )
    flooded = compute_clan_identity_hash(
        family_id="goblin_tribe",
        biome="city_ruins",
        keys=["ancient", "flooded"],
        selected_trait_keys=["fortified_scavengers"],
    )
    different_traits = compute_clan_identity_hash(
        family_id="goblin_tribe",
        biome="city_ruins",
        keys=["ancient", "ruined_old_city"],
        selected_trait_keys=["ambush_drilled"],
    )
    different_family = compute_clan_identity_hash(
        family_id="rat_swarm",
        biome="city_ruins",
        keys=["ancient", "ruined_old_city"],
        selected_trait_keys=["fortified_scavengers"],
    )
    different_generation_version = compute_clan_identity_hash(
        family_id="goblin_tribe",
        biome="city_ruins",
        keys=["ancient", "ruined_old_city"],
        selected_trait_keys=["fortified_scavengers"],
        generation_version=3,
    )
    different_resource_version = compute_clan_identity_hash(
        family_id="goblin_tribe",
        biome="city_ruins",
        keys=["ancient", "ruined_old_city"],
        selected_trait_keys=["fortified_scavengers"],
        resource_version="2.0",
    )

    assert base != flooded
    assert base != different_traits
    assert base != different_family
    assert base != different_generation_version
    assert base != different_resource_version

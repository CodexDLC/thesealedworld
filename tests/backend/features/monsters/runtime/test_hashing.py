import pytest

from src.backend.features.monsters.runtime.hashing import (
    compute_context_hash,
    compute_rift_context_hash,
    compute_unique_clan_hash,
    normalize_tags,
)


@pytest.mark.unit
def test_context_hash_is_stable_for_tag_order_and_ignores_non_mutation_tags() -> None:
    left_tags = normalize_tags(["mana_leak", "road", "ancient_tech"])
    right_tags = normalize_tags(["ancient_tech", "mana_leak", "decorative_noise"])

    assert left_tags == ["ancient_tech", "mana_leak"]
    assert compute_context_hash(1, "forest", left_tags) == compute_context_hash(1, "forest", right_tags)


@pytest.mark.unit
def test_unique_clan_hash_depends_on_family_and_context() -> None:
    context_hash = compute_context_hash(2, "forest", ["mana_leak"])

    assert compute_unique_clan_hash("wolf_pack", context_hash) == compute_unique_clan_hash("wolf_pack", context_hash)
    assert compute_unique_clan_hash("wolf_pack", context_hash) != compute_unique_clan_hash("rat_swarm", context_hash)


@pytest.mark.unit
def test_rift_context_hash_keeps_rift_tags_without_world_whitelist() -> None:
    left_hash = compute_rift_context_hash(
        setting_key="starter_rift",
        biome_id="broken_road",
        tier=1,
        tags=["broken_caravan", "roadside_camp", "starter_rift"],
    )
    right_hash = compute_rift_context_hash(
        setting_key="starter_rift",
        biome_id="broken_road",
        tier=1,
        tags=["starter_rift", "roadside_camp", "broken_caravan"],
    )
    world_hash = compute_context_hash(1, "broken_road", normalize_tags(["broken_caravan", "roadside_camp"]))

    assert normalize_tags(["broken_caravan", "roadside_camp"]) == []
    assert left_hash == right_hash
    assert left_hash != world_hash


@pytest.mark.unit
def test_rift_context_hash_depends_on_setting_key() -> None:
    starter_hash = compute_rift_context_hash(
        setting_key="starter_rift",
        biome_id="broken_road",
        tier=1,
        tags=["broken_caravan"],
    )
    quarry_hash = compute_rift_context_hash(
        setting_key="quarry_rift",
        biome_id="broken_road",
        tier=1,
        tags=["broken_caravan"],
    )

    assert starter_hash != quarry_hash

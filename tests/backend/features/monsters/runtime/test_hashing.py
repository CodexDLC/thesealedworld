import pytest

from src.backend.features.monsters.runtime.hashing import (
    compute_context_hash,
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


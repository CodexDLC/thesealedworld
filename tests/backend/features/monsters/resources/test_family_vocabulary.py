from src.backend.features.monsters.resources.family_vocabulary import (
    ANCHOR_BOSS_FAMILY_IDS,
    FUTURE_FAMILY_VOCABULARY,
    STARTER_ACTIVE_FAMILY_IDS,
    WORLD_FAMILY_VOCABULARY,
    is_world_family_vocabulary_id,
)


def test_world_family_vocabulary_separates_active_and_future_ids():
    assert STARTER_ACTIVE_FAMILY_IDS == ("bandit_gang", "goblin_tribe", "rat_swarm", "wolf_pack")
    assert ANCHOR_BOSS_FAMILY_IDS == ("anchor_sovereigns",)
    assert "spider_colony" in FUTURE_FAMILY_VOCABULARY
    assert "snake_den" in FUTURE_FAMILY_VOCABULARY
    assert "elemental_rift" in FUTURE_FAMILY_VOCABULARY
    assert len(WORLD_FAMILY_VOCABULARY) == len(set(WORLD_FAMILY_VOCABULARY))
    assert is_world_family_vocabulary_id("rat_swarm") is True
    assert is_world_family_vocabulary_id("unknown_family") is False

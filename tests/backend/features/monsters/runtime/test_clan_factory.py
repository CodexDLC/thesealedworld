import pytest

from src.backend.features.monsters.dto.generation import MonsterGenerationContext
from src.backend.features.monsters.runtime.clan_factory import ClanFactory
from src.backend.features.monsters.runtime.hashing import compute_context_hash, compute_unique_clan_hash, normalize_tags


@pytest.mark.unit
def test_factory_creates_clan_with_members_from_resource_data() -> None:
    context = MonsterGenerationContext(
        zone_id="D4_0_1",
        biome_id="forest",
        tier=1,
        tags=["mana_leak"],
        difficulty="mid",
    )
    tags = normalize_tags(context.tags)
    context_hash = compute_context_hash(context.tier, context.biome_id, tags)
    family_id = ClanFactory().select_family_id(context, context_hash)
    assert family_id is not None

    clan, members = ClanFactory().build_clan_with_members(
        family_id=family_id,
        context=context,
        context_hash=context_hash,
        unique_hash=compute_unique_clan_hash(family_id, context_hash),
        normalized_tags=tags,
    )

    assert clan.zone_id == "D4_0_1"
    assert clan.context_hash == context_hash
    assert members
    assert all(member.clan_id == clan.id for member in members)
    assert all(member.scaled_base_stats for member in members)

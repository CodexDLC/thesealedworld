from __future__ import annotations

import pytest

from src.backend.features.items.dto.instance import RuntimeItemProjectionDTO
from src.backend.features.monsters.dto.generation import GeneratedClan, MonsterGenerationContext
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.runtime.clan_factory import ClanFactory
from src.backend.features.monsters.runtime.generation_builder import MonsterClanGenerationBuilder
from src.backend.features.monsters.runtime.hashing import compute_context_hash, compute_unique_clan_hash, normalize_tags


class FakeRepository:
    def __init__(self) -> None:
        self.created: tuple[GeneratedClan, list] | None = None
        self.by_identity: dict[str, GeneratedClan] = {}

    async def get_clan_by_identity_hash(self, identity_hash: str) -> GeneratedClan | None:
        return self.by_identity.get(identity_hash)

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClan]:
        del context_hash
        return []

    async def get_clan_members(self, clan_id) -> list:
        del clan_id
        return []

    async def create_clan_with_members(self, clan: GeneratedClan, members: list) -> GeneratedClan:
        self.created = (clan, members)
        clan.members.extend(member for member in members if member not in clan.members)
        for member in clan.members:
            member.clan = clan
        self.by_identity[clan.identity_hash] = clan
        return clan

    async def update_clan_narrative(self, clan: GeneratedClan) -> GeneratedClan:
        return clan


class FakeItemGeneration:
    async def generate_runtime_projections(self, requests):
        return [
            RuntimeItemProjectionDTO(
                item_id=f"item-{index}",
                owner_key=str(request.runtime_metadata["owner_key"]),
                base_id=request.base_id,
                item_type="weapon" if request.target_slot in {"main_hand", "off_hand"} else "armor",
                slot=str(request.target_slot),
                combat={"power": 1, "implicit_bonuses": {}, "bonuses": {}, "tags": []},
                generation={"item_grade": request.item_grade, "rarity_tier": request.rarity_tier, "affixes": []},
            )
            for index, request in enumerate(requests)
        ]


@pytest.mark.unit
async def test_clan_factory_builds_full_db_template_without_encounter_budget() -> None:
    repository = FakeRepository()
    builder = MonsterClanGenerationBuilder(repository=repository, item_generation=FakeItemGeneration())
    factory = ClanFactory(builder)
    context = MonsterGenerationContext(
        zone_id="D4_0_1",
        biome_id="city_ruins",
        tier=1,
        tags=["wolf_pack", "mana_leak"],
        context_meta={
            "clan_flavor": {
                "name_ru": "Wolf Test Clan",
                "description": "Authored wolf clan flavor.",
                "encounter_texts": {
                    "patrol": "Patrol text.",
                    "ambush": "Ambush text.",
                    "lair": "Lair text.",
                    "random_meeting": "Random meeting text.",
                },
            }
        },
    )
    tags = normalize_tags(context.tags)
    context_hash = compute_context_hash(context.tier, context.biome_id, tags)
    identity_hash = compute_unique_clan_hash("wolf_pack", context_hash)

    clan = await factory.build_clan_template(
        family_id="wolf_pack",
        context=context,
        context_hash=context_hash,
        identity_hash=identity_hash,
        normalized_tags=tags,
    )

    family = get_family_config("wolf_pack")
    assert family is not None
    expected_variant_ids = set(family.variants)
    assert "target_budget" not in clan.context_identity
    assert clan.context_identity["variant_window"] == {"min_tier": 0, "max_tier": 7}
    assert 1 <= len(clan.selected_traits) <= 2
    assert {member.variant_id for member in clan.members} == expected_variant_ids
    assert len(clan.members) == len(expected_variant_ids)
    assert repository.created is not None

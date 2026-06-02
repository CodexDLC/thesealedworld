import uuid

import pytest

from src.backend.core.calculators.stats_waterfall_calculator import COMBAT_MATH_VERSION
from src.backend.features.items.dto.instance import RuntimeItemProjectionDTO
from src.backend.features.monsters.dto.generation import GeneratedClan, MonsterGenerationContext
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.runtime.generation_builder import MonsterClanGenerationBuilder, _MemberPlan
from src.backend.features.monsters.runtime.hashing import compute_context_hash, normalize_tags
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService


class FakeRepository:
    def __init__(self) -> None:
        self.created: tuple[GeneratedClan, list] | None = None
        self.by_unique: dict[str, GeneratedClan] = {}

    async def get_clan_by_unique_hash(self, unique_hash: str) -> GeneratedClan | None:
        return self.by_unique.get(unique_hash)

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClan]:
        return []

    async def get_clan_members(self, clan_id: uuid.UUID | str) -> list:
        return []

    async def create_clan_with_members(self, clan: GeneratedClan, members: list) -> GeneratedClan:
        self.created = (clan, members)
        clan.members.extend(member for member in members if member not in clan.members)
        for member in clan.members:
            member.clan = clan
        self.by_unique[clan.unique_hash] = clan
        return clan

    async def update_clan_flavor(self, clan: GeneratedClan) -> GeneratedClan:
        return clan


class FakeItemGeneration:
    def __init__(self) -> None:
        self.batches = []

    async def generate_runtime_projections(self, requests):
        self.batches.append(list(requests))
        projections = []
        for index, request in enumerate(requests):
            owner_key = str(request.runtime_metadata["owner_key"])
            projections.append(
                RuntimeItemProjectionDTO(
                    item_id=f"item-{index}",
                    owner_key=owner_key,
                    base_id=request.base_id,
                    item_type="accessory"
                    if request.target_slot == "amulet"
                    else ("weapon" if request.target_slot in {"main_hand", "off_hand", "two_hand"} else "armor"),
                    slot=str(request.target_slot),
                    combat={
                        "power": 3,
                        "implicit_bonuses": {},
                        "bonuses": {"main_hand_accuracy": "+0.01"},
                        "tags": list(request.extra_narrative_tags),
                    },
                    generation={
                        "item_grade": request.item_grade,
                        "rarity_tier": request.rarity_tier,
                        "affixes": [{"affix_id": request.allowed_affix_ids[0]}] if request.allowed_affix_ids else [],
                        "natural_key": request.runtime_metadata.get("natural_key"),
                        "source_context": request.source_context,
                    },
                )
            )
        return projections


@pytest.mark.unit
async def test_generation_builder_creates_clan_template_with_all_available_members_and_items() -> None:
    repository = FakeRepository()
    item_generation = FakeItemGeneration()
    builder = MonsterClanGenerationBuilder(repository=repository, item_generation=item_generation)
    context = MonsterGenerationContext(
        zone_id="zone-a",
        biome_id="city_ruins",
        tier=1,
        tags=["sewer"],
        threat=18,
        difficulty="mid",
    )

    clan = await builder.generate_clan_template(
        context,
        family_id="rat_swarm",
        context_hash="a" * 32,
        unique_hash="b" * 32,
        reuse_existing=False,
    )

    family = get_family_config("rat_swarm")
    assert family is not None
    max_tier = context.tier + 1
    expected_variants = [
        variant
        for variant in family.variants.values()
        if variant.min_tier <= max_tier and variant.max_tier >= 0
    ]
    assert repository.created is not None
    assert clan.family_id == "rat_swarm"
    assert clan.flavor_content["loot_culture"]["craft_style"]
    assert clan.flavor_content["loot_culture"]["tone_hints"]
    assert "target_budget" not in clan.raw_tags
    assert clan.raw_tags["variant_window"] == {"min_tier": 0, "max_tier": max_tier}
    assert len(clan.members) == len(expected_variants)
    assert {member.variant_key for member in clan.members} == {variant.id for variant in expected_variants}
    assert len(item_generation.batches) == 1
    expected_item_count = sum(
        len(variant.fixed_loadout.model_dump(exclude_none=True)) for variant in expected_variants
    )
    assert len(item_generation.batches[0]) == expected_item_count
    # transmog: natural keys resolve to player item base_ids
    rat_weapon_bases = {"knife", "dagger", "katar", "rapier", "shortbow", "warhammer"}
    rat_shield_bases = {"buckler", "shield"}
    rat_ammo_bases = {"quiver_training"}
    rat_accessory_bases = {"amulet"}
    rat_armor_bases = {"leather_armor", "jerkin", "plate_chest"}
    actual_base_ids = {request.base_id for request in item_generation.batches[0]}
    assert actual_base_ids <= (
        rat_weapon_bases | rat_shield_bases | rat_ammo_bases | rat_accessory_bases | rat_armor_bases
    )

    first = clan.members[0]
    assert first.items["layout"]["equipment"]
    assert clan.raw_tags["combat_math_version"] == COMBAT_MATH_VERSION
    assert first.generation_meta["schema_version"] == 2
    assert first.generation_meta["combat_math_version"] == COMBAT_MATH_VERSION
    assert first.generation_meta["family_resource_version"] == family.resource_version
    assert first.generation_meta["visual"]["status"] == "fallback"
    assert first.generation_meta["visual"]["image_url"] == "/static/images/monsters/families/rat_swarm.svg"
    assert first.items["by_id"]
    assert first.scaled_attributes["endurance"] > 0
    assert first.vitals["hp"]["max"] > 0
    assert first.text_content["detected_ru"]
    assert first.text_content["ambush_ru"]
    assert first.text_content["idle_ru"]
    assert first.generation_meta["balance"]["gear_score"] > 0
    assert first.generation_meta["balance"]["gear_score_version"] == MonsterGearScoreService.VERSION
    assert first.threat_rating == first.generation_meta["balance"]["gear_score"]
    assert "base_cost" not in first.generation_meta["balance"]
    assert "effective_cost" not in first.generation_meta["balance"]


@pytest.mark.unit
def test_generation_builder_uses_natural_mapping_item_kind_for_wolf_offhand_and_amulet() -> None:
    family = get_family_config("wolf_pack")
    assert family is not None
    variant = family.variants["pack_leader"]
    builder = MonsterClanGenerationBuilder(repository=FakeRepository(), item_generation=FakeItemGeneration())
    plan = _MemberPlan(
        member_id=uuid.uuid4(),
        owner_key="member-0",
        variant=variant,
        member_model=None,
        member_tier=3,
    )

    item_requests = builder._build_item_requests(family, [plan], "wolf-clan")
    by_slot = {str(request.target_slot): request for request in item_requests}

    assert by_slot["off_hand"].base_id == "buckler"
    assert by_slot["off_hand"].source_context["item_kind"] == "shield"
    assert by_slot["amulet"].base_id == "amulet"
    assert by_slot["amulet"].source_context["item_kind"] == "accessory"


@pytest.mark.unit
async def test_generation_builder_reuses_existing_unique_clan_when_requested() -> None:
    existing = GeneratedClan(
        id=uuid.uuid4(),
        family_id="rat_swarm",
        tier=1,
        zone_id="zone-a",
        context_hash="a" * 32,
        unique_hash="b" * 32,
        raw_tags={},
        flavor_content={},
        name_ru="Existing",
        description="Existing",
    )
    repository = FakeRepository()
    repository.by_unique[existing.unique_hash] = existing
    item_generation = FakeItemGeneration()
    builder = MonsterClanGenerationBuilder(repository=repository, item_generation=item_generation)

    clan = await builder.generate_clan_template(
        MonsterGenerationContext(zone_id="zone-a", biome_id="city_ruins", tier=1, tags=[]),
        family_id="rat_swarm",
        context_hash=existing.context_hash,
        unique_hash=existing.unique_hash,
    )

    assert clan is existing
    assert repository.created is None
    assert item_generation.batches == []


@pytest.mark.unit
async def test_generation_builder_creates_humanoid_item_orders_from_fixed_loadout() -> None:
    repository = FakeRepository()
    item_generation = FakeItemGeneration()
    builder = MonsterClanGenerationBuilder(repository=repository, item_generation=item_generation)

    await builder.generate_clan_template(
        MonsterGenerationContext(zone_id="zone-a", biome_id="city_ruins", tier=1, tags=[], threat=10),
        family_id="bandit_gang",
        context_hash="c" * 32,
        unique_hash="d" * 32,
        reuse_existing=False,
    )

    assert item_generation.batches
    requests = item_generation.batches[0]
    requested_base_ids = {request.base_id for request in requests}
    assert requested_base_ids & {"hatchet", "buckler", "jerkin", "shortbow", "belt"}

    amulet_requests = [request for request in requests if request.target_slot == "amulet"]
    assert amulet_requests
    assert {request.base_id for request in amulet_requests} == {"amulet"}
    assert {request.source_context["item_kind"] for request in amulet_requests} == {"accessory"}
    assert all("natural_key" not in request.runtime_metadata for request in amulet_requests)


@pytest.mark.unit
def test_d4_context_tags_are_preserved_for_clan_hashing() -> None:
    tags = normalize_tags(["d4_rift_rat_king", "rat_swarm", "unknown_noise"])

    assert tags == ["d4_rift_rat_king", "rat_swarm"]
    assert compute_context_hash(2, "city_ruins", tags) != compute_context_hash(2, "city_ruins", [])


@pytest.mark.unit
def test_d4_rat_rift_family_is_available_at_tier_two() -> None:
    builder = MonsterClanGenerationBuilder(repository=FakeRepository(), item_generation=FakeItemGeneration())
    context = MonsterGenerationContext(
        zone_id="D4_0_0",
        biome_id="city_ruins",
        tier=2,
        tags=["d4_rift_rat_king", "rat_swarm"],
    )

    assert builder.get_available_family_ids(context) == ["rat_swarm"]


@pytest.mark.unit
def test_broken_road_allows_authored_starter_goblins_without_tier_one_fallback() -> None:
    builder = MonsterClanGenerationBuilder(repository=FakeRepository(), item_generation=FakeItemGeneration())
    context = MonsterGenerationContext(
        zone_id="rift:starter_rift:secondary",
        biome_id="broken_road",
        tier=1,
        tags=[],
    )

    assert builder.get_available_family_ids(context) == ["bandit_gang", "goblin_tribe", "rat_swarm"]

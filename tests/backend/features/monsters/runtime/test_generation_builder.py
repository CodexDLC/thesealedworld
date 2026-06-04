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
        self.by_identity: dict[str, GeneratedClan] = {}

    async def get_clan_by_identity_hash(self, identity_hash: str) -> GeneratedClan | None:
        return self.by_identity.get(identity_hash)

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClan]:
        return []

    async def get_clan_members(self, clan_id: uuid.UUID | str) -> list:
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


def _clan_flavor(name: str = "Test Clan") -> dict[str, object]:
    return {
        "name_ru": name,
        "description": "Authored clan flavor for generation tests.",
        "encounter_texts": {
            "patrol": "Patrol text.",
            "ambush": "Ambush text.",
            "lair": "Lair text.",
            "random_meeting": "Random meeting text.",
        },
    }


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
        context_meta={"clan_flavor": _clan_flavor("Rat Test Clan")},
    )

    clan = await builder.generate_clan_template(
        context,
        family_id="rat_swarm",
        context_hash="a" * 32,
        identity_hash="b" * 32,
        reuse_existing=False,
    )

    family = get_family_config("rat_swarm")
    assert family is not None
    expected_variants = list(family.variants.values())
    assert repository.created is not None
    assert clan.family_id == "rat_swarm"
    assert "target_budget" not in clan.context_identity
    assert clan.context_identity["variant_window"] == {"min_tier": 0, "max_tier": 7}
    assert 1 <= len(clan.selected_traits) <= 2
    assert any(trait["key"] in {"plague_borne", "rot_adapted", "swarm_pressure"} for trait in clan.selected_traits)
    assert len(clan.members) == len(family.variants)
    assert {member.variant_id for member in clan.members} == set(family.variants)
    assert len(item_generation.batches) == 1
    expected_item_count = sum(
        len(variant.fixed_loadout.model_dump(exclude_none=True))
        * len(builder._snapshot_tiers(family, variant))
        for variant in expected_variants
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
    assert first.active_snapshot["items"]["layout"]["equipment"]
    assert clan.context_identity["combat_math_version"] == COMBAT_MATH_VERSION
    assert first.metadata_["schema_version"] == 2
    assert first.metadata_["combat_math_version"] == COMBAT_MATH_VERSION
    assert first.metadata_["family_resource_version"] == family.resource_version
    assert first.metadata_["visual"]["status"] == "placeholder"
    assert first.metadata_["visual"]["image_url"] == "/static/images/monsters/families/rat_swarm.svg"
    assert "family_modifiers" not in first.metadata_
    assert first.actor_document["document_kind"] == "monster_actor_projection"
    assert first.actor_document["snapshot_version"] == 1
    assert first.actor_document["base_projection"]["selected_traits_applied"] == clan.selected_traits
    assert set(first.actor_document["tier_snapshots"]) == {
        f"tier_{tier}" for tier in builder._snapshot_tiers(family, family.variants[first.variant_id])
    }
    assert first.active_snapshot["combat_snapshot_input"]["meta"]["actor_type"] == "monster"
    assert first.active_snapshot["items"]["by_id"]
    assert first.active_snapshot["attributes"]["endurance"] > 0
    assert first.active_snapshot["combat_snapshot_input"]["status"]["hp"]["max"] > 0
    assert clan.encounter_texts["patrol"]
    assert clan.encounter_texts["ambush"]
    assert clan.encounter_texts["lair"]
    assert clan.encounter_texts["random_meeting"]
    assert "detected_ru" not in first.active_snapshot
    assert "ambush_ru" not in first.active_snapshot
    assert "idle_ru" not in first.active_snapshot
    assert first.active_snapshot["gear_score"] > 0


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
        identity_hash="b" * 32,
        context_identity={"tier": 1, "zone_id": "zone-a"},
        context_hash="a" * 32,
        selected_traits=[],
        title="Existing",
        description="Existing",
        encounter_texts={},
        generation_version=2,
        resource_version="1",
    )
    repository = FakeRepository()
    repository.by_identity[existing.identity_hash] = existing
    item_generation = FakeItemGeneration()
    builder = MonsterClanGenerationBuilder(repository=repository, item_generation=item_generation)

    clan = await builder.generate_clan_template(
        MonsterGenerationContext(
            zone_id="zone-a",
            biome_id="city_ruins",
            tier=1,
            tags=[],
            context_meta={"clan_flavor": _clan_flavor()},
        ),
        family_id="rat_swarm",
        context_hash=existing.context_hash,
        identity_hash=existing.identity_hash,
    )

    assert clan is existing
    assert repository.created is None
    assert item_generation.batches == []


@pytest.mark.unit
async def test_generation_builder_rejects_tier_zero_clan_templates() -> None:
    builder = MonsterClanGenerationBuilder(repository=FakeRepository(), item_generation=FakeItemGeneration())

    with pytest.raises(ValueError, match="tier must be >= 1"):
        await builder.generate_clan_template(
            MonsterGenerationContext(zone_id="D4_tier0_start", biome_id="city_ruins", tier=0, tags=[]),
            family_id="rat_swarm",
            context_hash="0" * 32,
            identity_hash="1" * 32,
            reuse_existing=False,
        )


@pytest.mark.unit
async def test_generation_builder_creates_humanoid_item_orders_from_fixed_loadout() -> None:
    repository = FakeRepository()
    item_generation = FakeItemGeneration()
    builder = MonsterClanGenerationBuilder(repository=repository, item_generation=item_generation)

    await builder.generate_clan_template(
        MonsterGenerationContext(
            zone_id="zone-a",
            biome_id="city_ruins",
            tier=1,
            tags=[],
            threat=10,
            context_meta={"clan_flavor": _clan_flavor("Bandit Test Clan")},
        ),
        family_id="bandit_gang",
        context_hash="c" * 32,
        identity_hash="d" * 32,
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
def test_d4_context_tags_are_preserved_for_context_metadata() -> None:
    tags = normalize_tags(["d4_rift_rat_king", "rat_swarm", "unknown_noise"])

    assert tags == ["d4_rift_rat_king", "rat_swarm", "unknown_noise"]
    assert compute_context_hash(2, "city_ruins", tags) != compute_context_hash(2, "city_ruins", [])
    assert compute_context_hash(2, "city_ruins", tags) == compute_context_hash(7, "city_ruins", tags)


@pytest.mark.unit
async def test_generation_builder_requires_authored_clan_flavor() -> None:
    builder = MonsterClanGenerationBuilder(repository=FakeRepository(), item_generation=FakeItemGeneration())

    with pytest.raises(ValueError, match="requires clan_flavor"):
        await builder.generate_clan_template(
            MonsterGenerationContext(zone_id="zone-a", biome_id="city_ruins", tier=1, tags=[]),
            family_id="rat_swarm",
            context_hash="e" * 32,
            identity_hash="f" * 32,
            reuse_existing=False,
        )

import uuid

import pytest

from src.backend.features.items.dto.instance import RuntimeItemProjectionDTO
from src.backend.features.monsters.dto.generation import GeneratedClan, MonsterGenerationContext
from src.backend.features.monsters.runtime.generation_builder import MonsterClanGenerationBuilder
from src.backend.features.monsters.runtime.hashing import compute_context_hash, normalize_tags


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
                    item_type="weapon" if request.target_slot in {"main_hand", "off_hand"} else "armor",
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


class FakeTextAI:
    def __init__(self) -> None:
        self.payload = None

    async def generate_clan_flavor(self, payload):
        from src.backend.features.monsters.integrations.text_ai_client import (
            MonsterClanFlavorDTO,
            MonsterVariantFlavorDTO,
        )

        self.payload = payload
        return MonsterClanFlavorDTO(
            name_ru="Рой Черного Камня",
            description="Крысы держатся у влажных плит и нападают из щелей.",
            variants_flavor={
                key: MonsterVariantFlavorDTO(
                    name="Каменная крыса",
                    appearance="Мокрая крыса с темной шерстью.",
                    detected="Крыса пятится к щели и следит за движением.",
                    ambush="Крыса бросается из щели первой.",
                    idle="Крыса грызет обломок у стены.",
                    encounter="Крыса показывается у камня.",
                    behavior="Она держится рядом с другими крысами.",
                )
                for key in payload["units_to_name"]
            },
        )


@pytest.mark.unit
async def test_generation_builder_creates_active_clan_with_budgeted_members_and_items() -> None:
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

    clan = await builder.generate_active_clan(
        context,
        family_id="rat_swarm",
        context_hash="a" * 32,
        unique_hash="b" * 32,
        target_budget=18,
        reuse_existing=False,
    )

    assert repository.created is not None
    assert clan.family_id == "rat_swarm"
    assert clan.raw_tags["target_budget"] == 18
    assert 1 <= len(clan.members) <= 12
    assert len(item_generation.batches) == 1
    assert len(item_generation.batches[0]) == len(clan.members) * 2
    assert {request.base_id for request in item_generation.batches[0]} <= {"rat_bite_claws", "light_hide"}

    first = clan.members[0]
    assert first.items["layout"]["equipment"]
    assert first.generation_meta["schema_version"] == 2
    assert first.generation_meta["visual"]["status"] == "fallback"
    assert first.generation_meta["visual"]["image_url"] == "/static/images/monsters/families/rat_swarm.svg"
    assert first.items["by_id"]
    assert first.scaled_attributes["endurance"] > 0
    assert first.vitals["hp"]["max"] > 0
    assert first.text_content["detected_ru"]
    assert first.text_content["ambush_ru"]
    assert first.text_content["idle_ru"]


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

    clan = await builder.generate_active_clan(
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

    await builder.generate_active_clan(
        MonsterGenerationContext(zone_id="zone-a", biome_id="city_ruins", tier=1, tags=[], threat=10),
        family_id="bandit_gang",
        context_hash="c" * 32,
        unique_hash="d" * 32,
        target_budget=10,
        reuse_existing=False,
    )

    assert item_generation.batches
    requested_base_ids = {request.base_id for request in item_generation.batches[0]}
    assert requested_base_ids & {"hatchet", "buckler", "jerkin", "shortbow", "belt"}


@pytest.mark.unit
async def test_generation_builder_uses_text_ai_flavor_for_new_template() -> None:
    repository = FakeRepository()
    item_generation = FakeItemGeneration()
    text_ai = FakeTextAI()
    builder = MonsterClanGenerationBuilder(
        repository=repository,
        item_generation=item_generation,
        text_ai=text_ai,
    )

    clan = await builder.generate_active_clan(
        MonsterGenerationContext(zone_id="zone-a", biome_id="city_ruins", tier=1, tags=["black_stone"], threat=8),
        family_id="rat_swarm",
        context_hash="e" * 32,
        unique_hash="f" * 32,
        target_budget=8,
        reuse_existing=False,
    )

    assert text_ai.payload["text_contract"]["member"] == [
        "name",
        "appearance",
        "detected",
        "ambush",
        "idle",
        "encounter",
        "behavior",
    ]
    assert clan.name_ru == "Рой Черного Камня"
    assert clan.flavor_content["visual"]["image_url"] == "/static/images/monsters/families/rat_swarm.svg"
    text = clan.members[0].text_content
    assert text["name_ru"] == "Каменная крыса"
    assert text["detected_ru"] == "Крыса пятится к щели и следит за движением."
    assert text["ambush_ru"] == "Крыса бросается из щели первой."
    assert text["idle_ru"] == "Крыса грызет обломок у стены."


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

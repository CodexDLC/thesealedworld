import uuid

import pytest

from src.backend.features.monsters.dto import GeneratedClan, HabitatClanPoolEntryDTO, MonsterHabitatDTO
from src.backend.features.monsters.resources import get_all_family_configs
from src.backend.features.monsters.services.habitat_clan_pool_materialization_service import (
    HabitatClanPoolMaterializationService,
    HabitatScopeConfig,
)
from src.backend.features.monsters.dto import ClanPoolPolicyDTO


class FakeRepository:
    def __init__(self) -> None:
        self.clans: dict[str, GeneratedClan] = {}
        self.entries: list[HabitatClanPoolEntryDTO] = []

    async def get_clan_by_identity_hash(self, identity_hash: str) -> GeneratedClan | None:
        return self.clans.get(identity_hash)

    async def upsert_habitat_clan_pool_entry(self, entry: HabitatClanPoolEntryDTO) -> HabitatClanPoolEntryDTO:
        self.entries = [item for item in self.entries if item.clan_identity_hash != entry.clan_identity_hash]
        self.entries.append(entry)
        return entry


class FakeFactory:
    def __init__(self, repository: FakeRepository) -> None:
        self.repository = repository
        self.calls: list[dict] = []

    async def build_clan_template(self, **kwargs) -> GeneratedClan:
        self.calls.append(dict(kwargs))
        clan = GeneratedClan(
            id=uuid.uuid4(),
            family_id=kwargs["family_id"],
            identity_hash=kwargs["identity_hash"],
            context_identity={"habitat": kwargs["context"].habitat.model_dump(mode="json")},
            context_hash=kwargs["context_hash"],
            selected_traits=[],
            title="Generated",
            description="Generated",
            encounter_texts={},
            generation_version=2,
            resource_version="1",
        )
        self.repository.clans[clan.identity_hash] = clan
        return clan


def _clan_flavors(*family_ids: str) -> dict[str, dict[str, object]]:
    return {
        family_id: {
            "name_ru": family_id.replace("_", " ").title(),
            "description": f"Authored {family_id} clan flavor.",
            "encounter_texts": {
                "patrol": f"{family_id} patrol.",
                "ambush": f"{family_id} ambush.",
                "lair": f"{family_id} lair.",
                "random_meeting": f"{family_id} random meeting.",
            },
        }
        for family_id in family_ids
    }


async def test_materializer_creates_pool_entries_and_skips_blocked_families() -> None:
    repository = FakeRepository()
    factory = FakeFactory(repository)
    service = HabitatClanPoolMaterializationService(repository=repository, factory=factory)  # type: ignore[arg-type]

    result = await service.ensure_scope_pool(
        HabitatScopeConfig(
            scope_type="region",
            scope_id="D4",
            habitat=MonsterHabitatDTO(biome="city_ruins", keys=["ancient", "ruined_old_city"]),
            clan_pool_policy=ClanPoolPolicyDTO.model_validate(
                {
                    "primary": [{"family_id": "goblin_tribe", "weight": 100}],
                    "secondary": [{"family_id": "rat_swarm", "weight": 30}],
                    "blocked": ["rat_swarm"],
                }
            ),
            tier=1,
            source_meta={"clan_flavors": _clan_flavors("goblin_tribe")},
        )
    )

    assert result.scopes == 1
    assert result.pool_entries == 1
    assert len(factory.calls) == 1
    assert [entry.family_id for entry in repository.entries] == ["goblin_tribe"]
    assert repository.entries[0].scope_type == "region"
    assert repository.entries[0].scope_id == "D4"
    assert repository.entries[0].habitat.biome == "city_ruins"
    assert repository.entries[0].habitat.keys == ["ancient", "ruined_old_city"]
    assert factory.calls[0]["context"].context_meta["clan_flavor"]["name_ru"] == "Goblin Tribe"


async def test_materializer_reuses_existing_clan_by_habitat_identity_hash() -> None:
    repository = FakeRepository()
    factory = FakeFactory(repository)
    service = HabitatClanPoolMaterializationService(repository=repository, factory=factory)  # type: ignore[arg-type]
    config = HabitatScopeConfig(
        scope_type="region",
        scope_id="D4",
        habitat=MonsterHabitatDTO(biome="city_ruins", keys=["ancient", "ruined_old_city"]),
        clan_pool_policy=ClanPoolPolicyDTO.model_validate({"primary": [{"family_id": "goblin_tribe", "weight": 100}]}),
        tier=1,
        source_meta={"clan_flavors": _clan_flavors("goblin_tribe")},
    )

    first = await service.ensure_scope_pool(config)
    second = await service.ensure_scope_pool(config)

    assert first.clans == 1
    assert second.clans == 0
    assert len(factory.calls) == 1
    assert len(repository.entries) == 1


async def test_materializer_requires_authored_clan_flavor_for_each_family() -> None:
    repository = FakeRepository()
    factory = FakeFactory(repository)
    service = HabitatClanPoolMaterializationService(repository=repository, factory=factory)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="requires authored clan_flavors"):
        await service.ensure_scope_pool(
            HabitatScopeConfig(
                scope_type="rift",
                scope_id="starter_rift",
                habitat=MonsterHabitatDTO(biome="broken_road", keys=["road_tract"]),
                clan_pool_policy=ClanPoolPolicyDTO.model_validate(
                    {"primary": [{"family_id": "goblin_tribe", "weight": 100}]}
                ),
                tier=1,
            )
        )


def test_old_family_tier_availability_helper_is_removed() -> None:
    import src.backend.features.monsters.resources as resources

    assert not hasattr(resources, "get_available_variants_for_family_tier")
    assert get_all_family_configs()

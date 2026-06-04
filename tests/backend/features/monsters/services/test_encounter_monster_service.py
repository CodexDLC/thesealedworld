from __future__ import annotations

import uuid

import pytest

from src.backend.features.monsters.dto.generation import GeneratedClan, MonsterGenerationContext, MonsterHabitatDTO
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.resources.traits import select_monster_clan_traits_for_habitat
from src.backend.features.monsters.runtime.hashing import compute_clan_identity_hash, compute_habitat_hash
from src.backend.features.monsters.services import EncounterMonsterService


class FakeClanFactory:
    def __init__(self, repository: FakeMonsterRepository) -> None:
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
        self.repository.clans_by_identity[clan.identity_hash] = clan
        return clan


class FakeMonsterRepository:
    def __init__(self) -> None:
        self.clans_by_identity: dict[str, GeneratedClan] = {}
        self.prune_requests: list[dict[str, set[tuple[str, str]]]] = []

    async def get_clan_by_identity_hash(self, identity_hash: str) -> GeneratedClan | None:
        return self.clans_by_identity.get(identity_hash)

    async def delete_generated_clans_outside_zone_contexts(self, expected: dict[str, set[tuple[str, str]]]) -> int:
        self.prune_requests.append(expected)
        return 3


def _context() -> MonsterGenerationContext:
    return MonsterGenerationContext(
        zone_id="rift:starter_rift",
        biome_id="broken_road",
        habitat=MonsterHabitatDTO(biome="broken_road", keys=["road_tract", "scavenger_camp"]),
        tier=1,
        tags=["road_tract", "scavenger_camp"],
        difficulty="mid",
        context_meta={"clan_flavor": {"name_ru": "Authored"}},
    )


@pytest.mark.unit
def test_prepare_encounter_monsters_legacy_api_is_removed() -> None:
    repo = FakeMonsterRepository()
    service = EncounterMonsterService(repo, factory=FakeClanFactory(repo))  # type: ignore[arg-type]

    assert not hasattr(service, "prepare_encounter_monsters")
    assert not hasattr(service, "ensure_clan_for_hash_context")


@pytest.mark.unit
async def test_ensure_clan_for_context_uses_habitat_identity_contract() -> None:
    repo = FakeMonsterRepository()
    factory = FakeClanFactory(repo)
    service = EncounterMonsterService(repo, factory=factory)  # type: ignore[arg-type]
    context = _context()

    clan = await service.ensure_clan_for_context(context, "goblin_tribe")

    assert clan.family_id == "goblin_tribe"
    assert clan.context_hash == compute_habitat_hash(biome="broken_road", keys=["road_tract", "scavenger_camp"])
    family = get_family_config("goblin_tribe")
    assert family is not None
    selected_trait_keys = [
        trait.key
        for trait in select_monster_clan_traits_for_habitat(
            family,
            biome_id="broken_road",
            habitat_keys=["road_tract", "scavenger_camp"],
        )
    ]
    assert clan.identity_hash == compute_clan_identity_hash(
        family_id="goblin_tribe",
        biome="broken_road",
        keys=["road_tract", "scavenger_camp"],
        selected_trait_keys=selected_trait_keys,
        generation_version=2,
        resource_version=1.4,
    )
    assert factory.calls[0]["normalized_tags"] == ["broken_road", "road_tract", "scavenger_camp"]


@pytest.mark.unit
async def test_ensure_clan_for_context_reuses_existing_identity_hash() -> None:
    repo = FakeMonsterRepository()
    factory = FakeClanFactory(repo)
    service = EncounterMonsterService(repo, factory=factory)  # type: ignore[arg-type]
    context = _context()

    first = await service.ensure_clan_for_context(context, "goblin_tribe")
    second = await service.ensure_clan_for_context(context, "goblin_tribe")

    assert second.id == first.id
    assert len(factory.calls) == 1


@pytest.mark.unit
async def test_prune_delegates_to_replacement_repository_contract() -> None:
    repo = FakeMonsterRepository()
    service = EncounterMonsterService(repo, factory=FakeClanFactory(repo))  # type: ignore[arg-type]
    expected = {"rift:starter_rift": {("goblin_tribe", "identity")}}

    assert await service.prune_generated_clans_for_zone_contexts(expected) == 3
    assert repo.prune_requests == [expected]

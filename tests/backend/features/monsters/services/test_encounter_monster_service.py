from __future__ import annotations

import uuid

import pytest

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster, MonsterGenerationContext
from src.backend.features.monsters.runtime.hashing import compute_context_hash, normalize_tags
from src.backend.features.monsters.services import EncounterMonsterService


class FakeMonsterRepository:
    def __init__(self) -> None:
        self.clans_by_context: dict[str, list[GeneratedClan]] = {}
        self.clans_by_unique: dict[str, GeneratedClan] = {}
        self.members_by_clan: dict[uuid.UUID, list[GeneratedMonster]] = {}
        self.created = False
        self.updated = False

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClan]:
        return self.clans_by_context.get(context_hash, [])

    async def get_clan_by_unique_hash(self, unique_hash: str) -> GeneratedClan | None:
        return self.clans_by_unique.get(unique_hash)

    async def create_clan_with_members(
        self,
        clan: GeneratedClan,
        members: list[GeneratedMonster],
    ) -> GeneratedClan:
        self.created = True
        self.clans_by_unique[clan.unique_hash] = clan
        self.clans_by_context.setdefault(clan.context_hash, []).append(clan)
        self.members_by_clan[clan.id] = members
        return clan

    async def get_clan_members(self, clan_id: uuid.UUID) -> list[GeneratedMonster]:
        return self.members_by_clan.get(clan_id, [])

    async def update_clan_flavor(self, clan: GeneratedClan) -> GeneratedClan:
        self.updated = True
        self.clans_by_unique[clan.unique_hash] = clan
        self.members_by_clan[clan.id] = list(clan.members)
        return clan


def _clan(context_hash: str, unique_hash: str = "unique") -> GeneratedClan:
    return GeneratedClan(
        id=uuid.uuid4(),
        family_id="wolf_pack",
        tier=1,
        zone_id="zone-a",
        context_hash=context_hash,
        unique_hash=unique_hash,
        raw_tags={},
        flavor_content={},
        name_ru="Wolves",
        description="Existing wolves",
    )


def _monster(clan_id: uuid.UUID, role: str = "minion", threat: int = 20) -> GeneratedMonster:
    return GeneratedMonster(
        id=uuid.uuid4(),
        clan_id=clan_id,
        variant_key=f"{role}_{threat}",
        role=role,
        threat_rating=threat,
        name_ru="Wolf",
        description="Wolf",
        scaled_base_stats={"strength": 10},
        loadout_ids={},
        skills_snapshot=["attack_basic"],
        current_state=None,
    )


@pytest.mark.unit
async def test_prepare_encounter_reuses_existing_clan() -> None:
    repo = FakeMonsterRepository()
    service = EncounterMonsterService(repo)
    context = MonsterGenerationContext(biome_id="forest", tier=1, tags=["mana_leak"], difficulty="easy")
    normalized = normalize_tags(context.tags)
    actual_hash = compute_context_hash(context.tier, context.biome_id, normalized)
    clan = _clan(actual_hash)
    monster = _monster(clan.id)
    clan.members.append(monster)
    repo.clans_by_context[actual_hash] = [clan]
    repo.members_by_clan[clan.id] = [monster]

    result = await service.prepare_encounter_monsters(context)

    assert result.reused_existing_clan is True
    assert result.clan_id == str(clan.id)
    assert result.monster_ids == [str(monster.id)]
    assert repo.created is False


@pytest.mark.unit
async def test_prepare_encounter_refreshes_stale_clan_flavor() -> None:
    repo = FakeMonsterRepository()
    service = EncounterMonsterService(repo)
    context = MonsterGenerationContext(biome_id="forest", tier=1, tags=["mana_leak"], difficulty="easy")
    normalized = normalize_tags(context.tags)
    actual_hash = compute_context_hash(context.tier, context.biome_id, normalized)
    clan = _clan(actual_hash)
    clan.name_ru = "Wolf Pack T1"
    clan.flavor_content = {"name": "Wolf Pack T1", "variants": ["runner"]}
    monster = _monster(clan.id, role="minion")
    monster.variant_key = "runner"
    monster.name_ru = "Runner T1"
    clan.members.append(monster)
    repo.clans_by_context[actual_hash] = [clan]
    repo.members_by_clan[clan.id] = [monster]

    result = await service.prepare_encounter_monsters(context)

    assert result.reused_existing_clan is True
    assert repo.updated is True
    assert repo.members_by_clan[clan.id][0].name_ru == "Runner"
    assert repo.clans_by_unique[clan.unique_hash].name_ru == "Ashen Wolves"


@pytest.mark.unit
async def test_prepare_encounter_creates_clan_and_returns_monster_ids() -> None:
    repo = FakeMonsterRepository()
    service = EncounterMonsterService(repo)
    context = MonsterGenerationContext(
        zone_id="D4_0_1",
        biome_id="forest",
        tier=1,
        tags=["mana_leak"],
        difficulty="easy",
        count=2,
    )

    result = await service.prepare_encounter_monsters(context)

    assert repo.created is True
    assert result.reused_existing_clan is False
    assert result.clan_id
    assert 1 <= len(result.monster_ids) <= 2


@pytest.mark.unit
async def test_ensure_clan_for_context_creates_one_requested_family() -> None:
    repo = FakeMonsterRepository()
    service = EncounterMonsterService(repo)
    context = MonsterGenerationContext(
        zone_id="D4_0_1",
        biome_id="city_ruins",
        tier=1,
        tags=["mana_leak"],
        difficulty="mid",
    )

    clan = await service.ensure_clan_for_context(context, "goblin_tribe")

    assert clan.family_id == "goblin_tribe"
    assert len(repo.clans_by_unique) == 1


@pytest.mark.unit
async def test_ensure_clan_for_context_reuses_existing_family_context_hash() -> None:
    repo = FakeMonsterRepository()
    service = EncounterMonsterService(repo)
    context = MonsterGenerationContext(
        zone_id="D4_0_1",
        biome_id="city_ruins",
        tier=1,
        tags=["mana_leak"],
        difficulty="mid",
    )

    first = await service.ensure_clan_for_context(context, "goblin_tribe")
    second = await service.ensure_clan_for_context(context, "goblin_tribe")

    assert second.id == first.id
    assert len(repo.clans_by_unique) == 1

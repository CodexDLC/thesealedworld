from __future__ import annotations

import uuid

import pytest

from src.backend.features.monsters.dto.generation import MonsterGenerationContext
from src.backend.features.monsters.runtime.hashing import compute_context_hash, normalize_tags
from src.backend.features.monsters.services import EncounterMonsterService
from src.backend.infrastructure.actor_state.models import GeneratedClanORM, GeneratedMonsterORM


class FakeMonsterRepository:
    def __init__(self) -> None:
        self.clans_by_context: dict[str, list[GeneratedClanORM]] = {}
        self.clans_by_unique: dict[str, GeneratedClanORM] = {}
        self.members_by_clan: dict[uuid.UUID, list[GeneratedMonsterORM]] = {}
        self.created = False

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClanORM]:
        return self.clans_by_context.get(context_hash, [])

    async def get_clan_by_unique_hash(self, unique_hash: str) -> GeneratedClanORM | None:
        return self.clans_by_unique.get(unique_hash)

    async def create_clan_with_members(
        self,
        clan: GeneratedClanORM,
        members: list[GeneratedMonsterORM],
    ) -> GeneratedClanORM:
        self.created = True
        self.clans_by_unique[clan.unique_hash] = clan
        self.clans_by_context.setdefault(clan.context_hash, []).append(clan)
        self.members_by_clan[clan.id] = members
        return clan

    async def get_clan_members(self, clan_id: uuid.UUID) -> list[GeneratedMonsterORM]:
        return self.members_by_clan.get(clan_id, [])


def _clan(context_hash: str, unique_hash: str = "unique") -> GeneratedClanORM:
    return GeneratedClanORM(
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


def _monster(clan_id: uuid.UUID, role: str = "minion", threat: int = 20) -> GeneratedMonsterORM:
    return GeneratedMonsterORM(
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
    service = EncounterMonsterService(repo)  # type: ignore[arg-type]
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
async def test_prepare_encounter_creates_clan_and_returns_monster_ids() -> None:
    repo = FakeMonsterRepository()
    service = EncounterMonsterService(repo)  # type: ignore[arg-type]
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

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
from src.backend.features.monsters.repositories import MonsterGenerationRepository
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM


@pytest.mark.unit
async def test_create_clan_with_members_persists_clan_and_members() -> None:
    session = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    repo = MonsterGenerationRepository(session)
    clan = GeneratedClan(
        id=uuid.uuid4(),
        family_id="wolf_pack",
        tier=1,
        zone_id="zone-a",
        context_hash="context",
        unique_hash="unique",
        raw_tags={},
        flavor_content={},
        name_ru="Wolves",
        description="Existing wolves",
    )
    member = GeneratedMonster(
        id=uuid.uuid4(),
        clan_id=clan.id,
        variant_key="wolf",
        role="minion",
        member_tier=0,
        threat_rating=20,
        name_ru="Wolf",
        description="Wolf",
        text_content={"name_ru": "Wolf"},
        scaled_attributes={"strength": 10},
        scaled_skills={"skill_unarmed": 0.10},
        items={},
        vitals={"hp": {"current": 10, "max": 10}},
        ai_profile={},
        generation_meta={"schema_version": 2},
    )

    result = await repo.create_clan_with_members(clan, [member])

    persisted_clan = session.add.call_args.args[0]
    persisted_members = session.add_all.call_args.args[0]
    assert isinstance(result, GeneratedClan)
    assert result.id == clan.id
    assert result.members[0].id == member.id
    assert result.members[0].clan is result
    assert result.members[0].scaled_skills == {"skill_unarmed": 0.10}
    assert isinstance(persisted_clan, GeneratedClanORM)
    assert isinstance(persisted_members[0], GeneratedMonsterORM)
    assert persisted_clan.id == clan.id
    assert persisted_members[0].id == member.id
    assert persisted_members[0].scaled_skills == {"skill_unarmed": 0.10}
    session.add.assert_called_once()
    session.add_all.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.unit
async def test_update_clan_flavor_updates_clan_and_member_text() -> None:
    session = MagicMock()
    session.flush = AsyncMock()
    clan_id = uuid.uuid4()
    member_id = uuid.uuid4()
    clan_orm = GeneratedClanORM(
        id=clan_id,
        family_id="wolf_pack",
        tier=1,
        zone_id="zone-a",
        context_hash="context",
        unique_hash="unique",
        raw_tags={},
        flavor_content={"name": "Wolf Pack T1"},
        name_ru="Wolf Pack T1",
        description="Old",
    )
    member_orm = GeneratedMonsterORM(
        id=member_id,
        clan_id=clan_id,
        variant_key="runner",
        role="minion",
        member_tier=0,
        threat_rating=20,
        name_ru="Runner T1",
        description="Old runner",
        text_content={"name_ru": "Runner T1"},
        scaled_attributes={"strength": 10},
        scaled_skills={},
        items={},
        vitals={},
        ai_profile={},
        generation_meta={},
    )
    clan_orm.members.append(member_orm)
    session.scalar = AsyncMock(return_value=clan_orm)
    repo = MonsterGenerationRepository(session)

    updated = GeneratedClan(
        id=clan_id,
        family_id="wolf_pack",
        tier=1,
        zone_id="zone-a",
        context_hash="context",
        unique_hash="unique",
        raw_tags={},
        flavor_content={"name_ru": "Ashen Wolves", "variants_flavor": {}},
        name_ru="Ashen Wolves",
        description="New",
        members=[
            GeneratedMonster(
                id=member_id,
                clan_id=clan_id,
                variant_key="runner",
                role="minion",
                member_tier=0,
                threat_rating=20,
                name_ru="Runner",
                description="New runner",
                text_content={"name_ru": "Runner"},
                scaled_attributes={"strength": 10},
                scaled_skills={},
                items={},
                vitals={},
                ai_profile={},
            )
        ],
    )

    result = await repo.update_clan_flavor(updated)

    assert result.name_ru == "Ashen Wolves"
    assert result.members[0].name_ru == "Runner"
    assert clan_orm.flavor_content == {"name_ru": "Ashen Wolves", "variants_flavor": {}}
    assert member_orm.description == "New runner"
    session.flush.assert_awaited_once()


@pytest.mark.unit
async def test_delete_generated_clans_outside_zone_contexts_deletes_stale_rift_slots() -> None:
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[MagicMock(rowcount=2), MagicMock(rowcount=1)])
    repo = MonsterGenerationRepository(session)

    deleted = await repo.delete_generated_clans_outside_zone_contexts(
        {
            "rift:starter_rift:primary": {("bandit_gang", "primary-hash")},
            "rift:starter_rift:secondary": {("rat_swarm", "secondary-hash")},
            "rift:starter_rift:empty": set(),
        }
    )

    assert deleted == 3
    assert session.execute.await_count == 2


@pytest.mark.unit
async def test_refresh_clan_gear_scores_updates_stale_member_balance_and_summary() -> None:
    session = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    clan_id = uuid.uuid4()
    member_orm = GeneratedMonsterORM(
        id=uuid.uuid4(),
        clan_id=clan_id,
        variant_key="runner",
        role="minion",
        member_tier=0,
        threat_rating=20,
        name_ru="Runner T1",
        description="Old runner",
        text_content={"name_ru": "Runner T1"},
        scaled_attributes={
            "strength": 6,
            "agility": 6,
            "endurance": 6,
            "intellect": 1,
            "memory": 1,
            "mental": 2,
            "perception": 3,
            "projection": 1,
            "prediction": 2,
        },
        scaled_skills={"skill_unarmed": 0.2},
        items={},
        vitals={"hp": {"current": 20, "max": 20}, "energy": {"current": 10, "max": 10}},
        ai_profile={},
        generation_meta={
            "balance": {
                "gear_score": 999,
                "gear_score_version": MonsterGearScoreService.VERSION - 1,
                "organization_type": "pack",
            },
            "meta": {"archetype": "beast", "tags": ["wolf"]},
        },
    )
    clan_orm = GeneratedClanORM(
        id=clan_id,
        family_id="wolf_pack",
        tier=1,
        zone_id="zone-a",
        context_hash="context",
        unique_hash="unique",
        raw_tags={},
        flavor_content={},
        name_ru="Wolf Pack T1",
        description="Old",
    )
    clan_orm.members.append(member_orm)
    session.scalar = AsyncMock(return_value=clan_orm)
    repo = MonsterGenerationRepository(session)

    members = await repo.refresh_clan_gear_scores(clan_id)

    assert members[0].generation_meta["balance"]["gear_score"] != 999
    assert members[0].generation_meta["balance"]["gear_score_version"] == MonsterGearScoreService.VERSION
    assert clan_orm.raw_tags["gear_score_summary"]["version"] == MonsterGearScoreService.VERSION
    session.flush.assert_awaited_once()
    assert session.refresh.await_count == 2
    session.refresh.assert_any_await(clan_orm, attribute_names=["raw_tags", "updated_at"])
    session.refresh.assert_any_await(member_orm, attribute_names=["generation_meta", "threat_rating", "updated_at"])

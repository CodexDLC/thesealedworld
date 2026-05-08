import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
from src.backend.features.monsters.repositories import MonsterGenerationRepository
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM


@pytest.mark.unit
async def test_create_clan_with_members_persists_clan_and_members() -> None:
    session = MagicMock()
    session.flush = AsyncMock()
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
        threat_rating=20,
        name_ru="Wolf",
        description="Wolf",
        scaled_base_stats={"strength": 10},
        loadout_ids={},
        skills_snapshot=[],
        combat_seed={"skills": {"skill_unarmed": 0.10}},
        current_state=None,
    )

    result = await repo.create_clan_with_members(clan, [member])

    persisted_clan = session.add.call_args.args[0]
    persisted_members = session.add_all.call_args.args[0]
    assert isinstance(result, GeneratedClan)
    assert result.id == clan.id
    assert result.members[0].id == member.id
    assert result.members[0].clan is result
    assert result.members[0].combat_seed == {"skills": {"skill_unarmed": 0.10}}
    assert isinstance(persisted_clan, GeneratedClanORM)
    assert isinstance(persisted_members[0], GeneratedMonsterORM)
    assert persisted_clan.id == clan.id
    assert persisted_members[0].id == member.id
    assert persisted_members[0].combat_seed == {"skills": {"skill_unarmed": 0.10}}
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
        threat_rating=20,
        name_ru="Runner T1",
        description="Old runner",
        scaled_base_stats={"strength": 10},
        loadout_ids={},
        skills_snapshot=[],
        combat_seed={},
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
                threat_rating=20,
                name_ru="Runner",
                description="New runner",
                scaled_base_stats={"strength": 10},
                loadout_ids={},
                skills_snapshot=[],
            )
        ],
    )

    result = await repo.update_clan_flavor(updated)

    assert result.name_ru == "Ashen Wolves"
    assert result.members[0].name_ru == "Runner"
    assert clan_orm.flavor_content == {"name_ru": "Ashen Wolves", "variants_flavor": {}}
    assert member_orm.description == "New runner"
    session.flush.assert_awaited_once()

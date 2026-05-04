import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.monsters.repositories import MonsterGenerationRepository
from src.backend.infrastructure.actor_state.models import GeneratedClanORM, GeneratedMonsterORM


@pytest.mark.unit
async def test_create_clan_with_members_persists_clan_and_members() -> None:
    session = MagicMock()
    session.flush = AsyncMock()
    repo = MonsterGenerationRepository(session)
    clan = GeneratedClanORM(
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
    member = GeneratedMonsterORM(
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
        current_state=None,
    )

    result = await repo.create_clan_with_members(clan, [member])

    assert result is clan
    assert clan.members == [member]
    session.add.assert_called_once_with(clan)
    session.add_all.assert_called_once_with([member])
    session.flush.assert_awaited_once()

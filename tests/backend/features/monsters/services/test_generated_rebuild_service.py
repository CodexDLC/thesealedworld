from __future__ import annotations

import uuid

import pytest

from src.backend.features.monsters.dto.generated_view import MonsterDataRebuildRequestDTO
from src.backend.features.monsters.services.generated_rebuild_service import MonsterGeneratedRebuildService
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM


class FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.deleted = []

    def add(self, item) -> None:
        self.added.append(item)

    async def delete(self, item) -> None:
        self.deleted.append(item)


@pytest.mark.unit
async def test_generated_rebuild_updates_mechanics_and_preserves_existing_visual() -> None:
    clan = GeneratedClanORM(
        id=uuid.uuid4(),
        family_id="bandit_gang",
        tier=1,
        zone_id="zone-a",
        biome_id="city_ruins",
        context_hash="a" * 32,
        unique_hash="b" * 32,
        raw_tags={"tags": ["bandit_gang"], "biome_id": "city_ruins", "difficulty": "mid"},
        flavor_content={
            "name_ru": "Bandits",
            "description": "Bandits",
            "variants_flavor": {},
            "visual": {"image_url": "/static/generated-assets/clan.webp"},
        },
        name_ru="Bandits",
        description="Bandits",
    )
    member_id = uuid.uuid4()
    member = GeneratedMonsterORM(
        id=member_id,
        clan_id=clan.id,
        variant_key="bandit_thug",
        role="minion",
        member_tier=1,
        threat_rating=1,
        name_ru="Existing thug",
        description="Existing text",
        text_content={"appearance_ru": "Existing appearance"},
        scaled_attributes={"strength": 1},
        scaled_skills={},
        items={"layout": {"equipment": {}}, "by_id": {}},
        vitals={},
        ai_profile={},
        generation_meta={
            "owner_key": str(member_id),
            "visual": {"image_url": "/static/generated-assets/member.webp", "asset_hash": "old"},
        },
        combat_actor_snapshot={},
    )
    clan.members.append(member)
    session = FakeSession()
    service = MonsterGeneratedRebuildService(session=session)

    outcome = await service._plan_clan(clan, MonsterDataRebuildRequestDTO(force=True))
    await service._apply_clan(clan, outcome, remove_obsolete_members=True)

    assert member.id == member_id
    assert member.scaled_skills
    assert member.generation_meta["visual"] == {
        "image_url": "/static/generated-assets/member.webp",
        "asset_hash": "old",
    }
    assert clan.flavor_content["visual"]["image_url"] == "/static/generated-assets/clan.webp"
    assert session.added

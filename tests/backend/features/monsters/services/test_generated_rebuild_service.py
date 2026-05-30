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


@pytest.mark.unit
async def test_generated_rebuild_uses_family_resource_version_instead_of_runtime_item_rolls() -> None:
    clan = _clan(family_id="bandit_gang", tier=1)
    service = MonsterGeneratedRebuildService(session=FakeSession())
    initial = await service._plan_clan(clan, MonsterDataRebuildRequestDTO())
    clan.members.extend(_member_orm(member) for member in initial.expected_by_variant.values())
    changed_member = clan.members[0]
    changed_member.items = {
        **changed_member.items,
        "by_id": {
            item_id: {
                **item,
                "generation": {
                    **item["generation"],
                    "affixes": [{"affix_id": "different_runtime_roll"}],
                },
            }
            for item_id, item in changed_member.items["by_id"].items()
        },
    }

    outcome = await service._plan_clan(clan, MonsterDataRebuildRequestDTO())

    assert outcome.changed == {}


@pytest.mark.unit
async def test_generated_rebuild_marks_missing_family_resource_version_as_stale() -> None:
    clan = _clan(family_id="bandit_gang", tier=1)
    service = MonsterGeneratedRebuildService(session=FakeSession())
    initial = await service._plan_clan(clan, MonsterDataRebuildRequestDTO())
    clan.members.extend(_member_orm(member) for member in initial.expected_by_variant.values())
    stale_member = clan.members[0]
    stale_member.generation_meta = {
        key: value for key, value in stale_member.generation_meta.items() if key != "family_resource_version"
    }

    outcome = await service._plan_clan(clan, MonsterDataRebuildRequestDTO())

    assert stale_member.variant_key in outcome.changed


def _clan(*, family_id: str, tier: int) -> GeneratedClanORM:
    return GeneratedClanORM(
        id=uuid.uuid4(),
        family_id=family_id,
        tier=tier,
        zone_id="zone-a",
        biome_id="city_ruins",
        context_hash="a" * 32,
        unique_hash="b" * 32,
        raw_tags={"tags": [family_id], "biome_id": "city_ruins", "difficulty": "mid"},
        flavor_content={
            "name_ru": "Generated clan",
            "description": "Generated clan",
            "variants_flavor": {},
            "visual": {"image_url": "/static/generated-assets/clan.webp"},
        },
        name_ru="Generated clan",
        description="Generated clan",
    )


def _member_orm(member) -> GeneratedMonsterORM:
    return GeneratedMonsterORM(
        id=member.id,
        clan_id=member.clan_id,
        variant_key=member.variant_key,
        role=member.role,
        member_tier=member.member_tier,
        threat_rating=member.threat_rating,
        name_ru=member.name_ru,
        description=member.description,
        text_content=dict(member.text_content),
        scaled_attributes=dict(member.scaled_attributes),
        scaled_skills=dict(member.scaled_skills),
        items=dict(member.items),
        vitals=dict(member.vitals),
        ai_profile=dict(member.ai_profile),
        generation_meta=dict(member.generation_meta),
        combat_actor_snapshot=dict(member.combat_actor_snapshot),
    )

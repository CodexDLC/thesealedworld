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


class FakeActorRepo:
    def __init__(self) -> None:
        self.documents = []

    async def upsert_actor_document(self, document):
        self.documents.append(dict(document))
        return str(document["mongo_actor_key"])


@pytest.mark.unit
async def test_generated_rebuild_updates_mechanics_and_preserves_existing_visual() -> None:
    clan_id = uuid.uuid4()
    clan = GeneratedClanORM(
        id=clan_id,
        family_id="bandit_gang",
        identity_hash="b" * 32,
        context_identity=_context_identity(tier=1),
        context_hash="a" * 32,
        selected_traits=[],
        metadata_={
            "visual": {"image_url": "/static/generated-assets/clan.webp"},
            "flavor_content": {"name_ru": "Bandits", "description": "Bandits", "variants_flavor": {}},
        },
        title="Bandits",
        description="Bandits",
        encounter_texts={},
    )
    member_id = uuid.uuid4()
    member = GeneratedMonsterORM(
        id=member_id,
        clan_id=clan.id,
        variant_id="bandit_thug",
        member_hash=str(member_id),
        role="minion",
        title="Existing thug",
        short_description="Existing text",
        min_tier=1,
        max_tier=7,
        mongo_actor_key=f"actor:{clan_id}:bandit_thug:{member_id}",
        metadata_={
            "owner_key": str(member_id),
            "visual": {"image_url": "/static/generated-assets/member.webp", "asset_hash": "old"},
        },
    )
    clan.members.append(member)
    session = FakeSession()
    service = MonsterGeneratedRebuildService(session=session)
    service.actor_repo = FakeActorRepo()

    outcome = await service._plan_clan(clan, MonsterDataRebuildRequestDTO(force=True))
    await service._apply_clan(clan, outcome, remove_obsolete_members=True)

    assert member.id == member_id
    assert member.metadata_["combat_math_version"]
    assert member.metadata_["visual"] == {
        "image_url": "/static/generated-assets/member.webp",
        "asset_hash": "old",
    }
    assert member.title == "Existing thug"
    assert clan.metadata_["visual"]["image_url"] == "/static/generated-assets/clan.webp"
    assert clan.context_identity["gear_score_summary"]["count"] > 0
    assert service.actor_repo.documents


@pytest.mark.unit
async def test_generated_rebuild_uses_family_resource_version_instead_of_runtime_item_rolls() -> None:
    clan = _clan(family_id="bandit_gang", tier=1)
    service = MonsterGeneratedRebuildService(session=FakeSession())
    initial = await service._plan_clan(clan, MonsterDataRebuildRequestDTO())
    clan.members.extend(_member_orm(member) for member in initial.expected_by_variant.values())
    changed_member = clan.members[0]
    changed_member.metadata_ = {**changed_member.metadata_, "runtime_noise": {"affix_id": "different_runtime_roll"}}

    outcome = await service._plan_clan(clan, MonsterDataRebuildRequestDTO())

    assert outcome.changed == {}


@pytest.mark.unit
async def test_generated_rebuild_marks_missing_family_resource_version_as_stale() -> None:
    clan = _clan(family_id="bandit_gang", tier=1)
    service = MonsterGeneratedRebuildService(session=FakeSession())
    initial = await service._plan_clan(clan, MonsterDataRebuildRequestDTO())
    clan.members.extend(_member_orm(member) for member in initial.expected_by_variant.values())
    stale_member = clan.members[0]
    stale_member.metadata_ = {
        key: value for key, value in stale_member.metadata_.items() if key != "family_resource_version"
    }

    outcome = await service._plan_clan(clan, MonsterDataRebuildRequestDTO())

    assert stale_member.variant_id in outcome.changed


@pytest.mark.unit
async def test_generated_rebuild_marks_missing_combat_math_version_as_stale() -> None:
    clan = _clan(family_id="bandit_gang", tier=1)
    service = MonsterGeneratedRebuildService(session=FakeSession())
    initial = await service._plan_clan(clan, MonsterDataRebuildRequestDTO())
    clan.members.extend(_member_orm(member) for member in initial.expected_by_variant.values())
    stale_member = clan.members[0]
    stale_member.metadata_ = {
        key: value for key, value in stale_member.metadata_.items() if key != "combat_math_version"
    }

    outcome = await service._plan_clan(clan, MonsterDataRebuildRequestDTO())

    assert stale_member.variant_id in outcome.changed


@pytest.mark.unit
async def test_generated_rebuild_marks_integer_family_resource_version_as_stale_after_minor_bump() -> None:
    clan = _clan(family_id="bandit_gang", tier=1)
    service = MonsterGeneratedRebuildService(session=FakeSession())
    initial = await service._plan_clan(clan, MonsterDataRebuildRequestDTO())
    clan.members.extend(_member_orm(member) for member in initial.expected_by_variant.values())
    stale_member = clan.members[0]
    stale_member.metadata_ = {
        **stale_member.metadata_,
        "family_resource_version": 1,
    }

    outcome = await service._plan_clan(clan, MonsterDataRebuildRequestDTO())

    assert stale_member.variant_id in outcome.changed


@pytest.mark.unit
async def test_generated_rebuild_marks_previous_minor_family_resource_version_as_stale() -> None:
    clan = _clan(family_id="bandit_gang", tier=1)
    service = MonsterGeneratedRebuildService(session=FakeSession())
    initial = await service._plan_clan(clan, MonsterDataRebuildRequestDTO())
    clan.members.extend(_member_orm(member) for member in initial.expected_by_variant.values())
    stale_member = clan.members[0]
    stale_member.metadata_ = {
        **stale_member.metadata_,
        "family_resource_version": 1.1,
    }

    outcome = await service._plan_clan(clan, MonsterDataRebuildRequestDTO())

    assert stale_member.variant_id in outcome.changed


def _clan(*, family_id: str, tier: int) -> GeneratedClanORM:
    return GeneratedClanORM(
        id=uuid.uuid4(),
        family_id=family_id,
        identity_hash="b" * 32,
        context_identity=_context_identity(tier=tier),
        context_hash="a" * 32,
        selected_traits=[],
        metadata_={
            "visual": {"image_url": "/static/generated-assets/clan.webp"},
            "flavor_content": {"name_ru": "Generated clan", "description": "Generated clan", "variants_flavor": {}},
        },
        title="Generated clan",
        description="Generated clan",
        encounter_texts={},
    )


def _member_orm(member) -> GeneratedMonsterORM:
    return GeneratedMonsterORM(
        id=member.id,
        clan_id=member.clan_id,
        variant_id=member.variant_id,
        member_hash=member.member_hash,
        role=member.role,
        title=member.title,
        short_description=member.short_description,
        min_tier=member.min_tier,
        max_tier=member.max_tier,
        mongo_actor_key=member.mongo_actor_key,
        metadata_=dict(member.metadata_),
    )


def _context_identity(*, tier: int) -> dict[str, object]:
    return {
        "schema_version": 2,
        "combat_math_version": "old",
        "family_resource_version": 1,
        "tags": ["bandit_gang"],
        "biome_id": "city_ruins",
        "difficulty": "mid",
        "habitat": {"biome": "city_ruins", "keys": ["bandit_gang"]},
        "context_meta": {},
        "tier": tier,
        "zone_id": "zone-a",
    }

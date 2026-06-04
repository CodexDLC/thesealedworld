import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
from src.backend.features.monsters.repositories import MonsterGenerationRepository
from src.backend.features.monsters.repositories.monster_generation_repository import _to_generated_monster
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM
from src.backend.infrastructure.monsters.actor_documents import (
    GENERATED_MONSTER_ACTOR_KIND,
    MissingGeneratedMonsterActorDocument,
    MissingGeneratedMonsterTierSnapshot,
)


class FakeActorRepository:
    def __init__(self) -> None:
        self.documents: dict[str, dict] = {}

    async def ensure_indexes(self) -> None:
        return None

    async def upsert_actor_document(self, document: dict) -> str:
        key = str(document["mongo_actor_key"])
        self.documents[key] = dict(document)
        return str(document.get("_id") or key)

    async def fetch_actor_documents_by_keys(self, actor_keys) -> dict[str, dict]:
        return {str(key): self.documents[str(key)] for key in actor_keys if str(key) in self.documents}

    async def require_tier_snapshot(self, mongo_actor_key: str, effective_tier: int) -> dict:
        document = self.documents.get(str(mongo_actor_key))
        if document is None:
            raise MissingGeneratedMonsterActorDocument(str(mongo_actor_key))
        snapshot = dict(document.get("tier_snapshots") or {}).get(str(effective_tier))
        if snapshot is None:
            raise MissingGeneratedMonsterTierSnapshot(str(effective_tier))
        return dict(snapshot)


@pytest.mark.unit
def test_generated_monster_pg_schema_is_replacement_only_light_contract() -> None:
    clan_columns = set(GeneratedClanORM.__table__.columns.keys())
    member_columns = set(GeneratedMonsterORM.__table__.columns.keys())

    assert {
        "tier",
        "unique_hash",
        "raw_tags",
        "flavor_content",
        "name_ru",
    }.isdisjoint(clan_columns)
    assert {
        "variant_key",
        "member_tier",
        "threat_rating",
        "text_content",
        "scaled_attributes",
        "scaled_skills",
        "items",
        "vitals",
        "ai_profile",
        "combat_actor_snapshot",
        "generation_meta",
    }.isdisjoint(member_columns)
    assert {
        "identity_hash",
        "context_identity",
        "selected_traits",
        "title",
        "encounter_texts",
    } <= clan_columns
    assert {"variant_id", "member_hash", "min_tier", "max_tier", "mongo_actor_key"} <= member_columns


@pytest.mark.unit
def test_generated_monster_conversion_requires_actor_document() -> None:
    member = GeneratedMonsterORM(
        id=uuid.uuid4(),
        clan_id=uuid.uuid4(),
        variant_id="runner",
        member_hash="hash",
        role="minion",
        title="Runner",
        short_description="Runner",
        min_tier=0,
        max_tier=2,
        mongo_actor_key="actor:runner",
    )

    with pytest.raises(TypeError):
        _to_generated_monster(member)  # type: ignore[call-arg]


@pytest.mark.unit
async def test_create_clan_with_members_persists_light_rows_and_actor_document() -> None:
    session = MagicMock()
    session.flush = AsyncMock()
    repo = MonsterGenerationRepository(session)
    repo.actor_repo = FakeActorRepository()
    clan_id = uuid.uuid4()
    member_id = uuid.uuid4()
    actor_key = f"actor:{clan_id}:wolf:member-hash"
    actor_document = {
        "_id": actor_key,
        "document_kind": GENERATED_MONSTER_ACTOR_KIND,
        "schema_version": 1,
        "clan_id": str(clan_id),
        "family_id": "wolf_pack",
        "variant_id": "wolf",
        "member_id": str(member_id),
        "member_hash": "member-hash",
        "mongo_actor_key": actor_key,
        "base_projection": {"role": "minion"},
        "tier_snapshots": {
            "1": {
                "effective_tier": 1,
                "attributes": {"strength": 10},
                "skills": {"skill_unarmed": 0.1},
                "loadout": {},
                "items": {},
                "affixes": [],
                "gear_score": 10,
                "combat_snapshot_input": {"skills": {"skill_unarmed": 0.1}},
            }
        },
    }
    clan = GeneratedClan(
        id=clan_id,
        family_id="wolf_pack",
        identity_hash="identity",
        context_identity={"zone_id": "zone-a", "tier": 1},
        context_hash="context",
        selected_traits=[],
        title="Wolves",
        description="Existing wolves",
        encounter_texts={"detected": "Wolves circle."},
        generation_version=1,
        resource_version="1",
    )
    member = GeneratedMonster(
        id=member_id,
        clan_id=clan.id,
        variant_id="wolf",
        member_hash="member-hash",
        role="minion",
        title="Wolf",
        short_description="Wolf",
        min_tier=0,
        max_tier=2,
        mongo_actor_key=actor_key,
        actor_document=actor_document,
    )

    result = await repo.create_clan_with_members(clan, [member])

    persisted_clan = session.add.call_args.args[0]
    persisted_members = session.add_all.call_args.args[0]
    assert isinstance(result, GeneratedClan)
    assert result.identity_hash == "identity"
    assert result.members[0].variant_id == "wolf"
    assert result.members[0].actor_document["tier_snapshots"]["1"]["gear_score"] == 10
    assert isinstance(persisted_clan, GeneratedClanORM)
    assert isinstance(persisted_members[0], GeneratedMonsterORM)
    assert persisted_clan.identity_hash == "identity"
    assert persisted_members[0].mongo_actor_key == actor_key
    assert repo.actor_repo.documents[actor_key]["tier_snapshots"]["1"]["gear_score"] == 10
    session.flush.assert_awaited_once()


@pytest.mark.unit
async def test_require_member_actor_snapshot_fails_without_snapshot() -> None:
    session = MagicMock()
    member = GeneratedMonsterORM(
        id=uuid.uuid4(),
        clan_id=uuid.uuid4(),
        variant_id="runner",
        member_hash="hash",
        role="minion",
        title="Runner",
        short_description="Runner",
        min_tier=0,
        max_tier=2,
        mongo_actor_key="actor:runner",
    )
    session.scalar = AsyncMock(return_value=member)
    repo = MonsterGenerationRepository(session)
    repo.actor_repo = FakeActorRepository()
    repo.actor_repo.documents["actor:runner"] = {
        "document_kind": GENERATED_MONSTER_ACTOR_KIND,
        "schema_version": 1,
        "clan_id": str(member.clan_id),
        "family_id": "wolf_pack",
        "variant_id": "runner",
        "member_id": str(member.id),
        "member_hash": "hash",
        "mongo_actor_key": "actor:runner",
        "base_projection": {},
        "tier_snapshots": {},
    }

    with pytest.raises(MissingGeneratedMonsterTierSnapshot):
        await repo.require_member_actor_snapshot(member.id, 1)


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

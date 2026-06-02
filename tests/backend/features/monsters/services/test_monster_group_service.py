from __future__ import annotations

import uuid
from typing import Any

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster, MonsterLocationContext
from src.backend.features.monsters.services.monster_group_service import MonsterGroupService


class FakeStorage:
    def __init__(self) -> None:
        self.clans_by_context: dict[str, list[GeneratedClan]] = {}
        self.clans_by_unique: dict[str, GeneratedClan] = {}
        self.members_by_clan: dict[uuid.UUID, list[GeneratedMonster]] = {}
        self.created = False

    async def get_clan_by_unique_hash(self, unique_hash: str) -> GeneratedClan | None:
        return self.clans_by_unique.get(unique_hash)

    async def get_generated_clan(self, clan_id: uuid.UUID | str) -> GeneratedClan | None:
        clan_uuid = uuid.UUID(str(clan_id))
        for clan in self.clans_by_unique.values():
            if clan.id == clan_uuid:
                return clan
        for clans in self.clans_by_context.values():
            for clan in clans:
                if clan.id == clan_uuid:
                    return clan
        return None

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClan]:
        return self.clans_by_context.get(context_hash, [])

    async def get_clan_members(self, clan_id: uuid.UUID | str) -> list[GeneratedMonster]:
        return self.members_by_clan.get(uuid.UUID(str(clan_id)), [])

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

    async def update_clan_flavor(self, clan: GeneratedClan) -> GeneratedClan:
        self.clans_by_unique[clan.unique_hash] = clan
        return clan


class FakeClanFactory:
    def __init__(self, storage: FakeStorage) -> None:
        self.storage = storage

    def select_family_id(self, context, context_hash: str) -> str:
        del context, context_hash
        return "rat_swarm"

    def get_available_family_ids(self, context) -> list[str]:
        del context
        return ["rat_swarm"]

    async def build_clan_template(
        self,
        *,
        context,
        family_id: str,
        context_hash: str,
        unique_hash: str,
        normalized_tags: list[str],
        reuse_existing: bool = False,
    ) -> GeneratedClan:
        del normalized_tags, reuse_existing
        clan = GeneratedClan(
            id=uuid.uuid4(),
            family_id=family_id,
            tier=context.tier,
            zone_id=context.zone_id,
            context_hash=context_hash,
            unique_hash=unique_hash,
            raw_tags={},
            flavor_content={},
            name_ru="Rat Swarm",
            description="Rat Swarm",
        )
        monster = _generated_monster(
            clan_id=clan.id,
            variant_key="sewer_rat",
            role="minion",
            gear_score=40,
            organization_type="swarm",
        )
        monster.clan = clan
        clan.members.append(monster)
        return await self.storage.create_clan_with_members(clan, [monster])


def _generated_monster(
    *,
    clan_id: uuid.UUID,
    variant_key: str,
    role: str,
    gear_score: int,
    organization_type: str,
) -> GeneratedMonster:
    return GeneratedMonster(
            id=uuid.uuid4(),
            clan_id=clan_id,
            variant_key=variant_key,
            role=role,
            member_tier=0,
            threat_rating=gear_score,
            name_ru=variant_key,
            description=variant_key,
            text_content={"name_ru": variant_key},
            scaled_attributes={
                "strength": 4,
                "agility": 10,
                "endurance": 5,
                "intellect": 1,
                "memory": 1,
                "mental": 2,
                "perception": 6,
                "projection": 1,
                "prediction": 2,
            },
            scaled_skills={"skill_fencing": 0.2, "skill_scouting": 0.9},
            items={},
            vitals={"hp": {"current": 20, "max": 20}, "energy": {"current": 10, "max": 10}},
            ai_profile={},
            generation_meta={
                "schema_version": 2,
                "meta": {"archetype": "beast", "tags": ["rat"]},
                "balance": {"gear_score": gear_score, "organization_type": organization_type},
                "visual": {
                    "status": "generated",
                    "image_url": "/static/generated-assets/monsters/generated/members/rat.webp",
                    "asset_hash": "rat-image-bytes",
                },
            },
        )


class FakeLocationContext:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def get_location_context(self, loc_id: str) -> MonsterLocationContext:
        self.calls.append(loc_id)
        return MonsterLocationContext(
            loc_id=loc_id,
            zone_id="D4_0_0",
            biome_id="city_ruins",
            tier=1,
            danger=0.0,
            tags=["city_ruins", "mana_leak"],
        )


class FakeActorCommitments:
    def __init__(self) -> None:
        self.saved: dict[str, dict] = {}

    async def save_monster_sources(
        self,
        *,
        sources: list[dict[str, Any]],
        ttl: int,
        scope_id: str | None = None,
    ) -> dict[str, str]:
        del ttl
        prefix = f"actor:{scope_id}" if scope_id else "actor:snapshot"

        # In real code we use actor_uuid, but here we just mock the result
        self.saved = {}
        results = {}
        for source in sources:
            monster_id = source['source']['monster_id']
            actor_id = f"{prefix}:monster:{monster_id}"
            self.saved[actor_id] = source
            results[f"monster:{monster_id}"] = actor_id

        return results


class FakeGroupCache:
    def __init__(self) -> None:
        self.payload: dict | None = None

    async def save_group(self, group_id: str, payload: dict, *, ttl: int) -> str:
        del ttl
        self.payload = payload
        return f"game:monster:group:{group_id}"


async def test_prepare_monster_group_creates_clan_and_actor_commitments() -> None:
    storage = FakeStorage()
    commitments = FakeActorCommitments()
    cache = FakeGroupCache()
    service = MonsterGroupService(
        repository=storage,
        location_context=FakeLocationContext(),  # type: ignore[arg-type]
        actor_commitments=commitments,  # type: ignore[arg-type]
        group_cache=cache,  # type: ignore[arg-type]
        factory=FakeClanFactory(storage),  # type: ignore[arg-type]
    )

    # scope_id passed here becomes group_id and is used in save_monster_sources as scope_id
    result = await service.prepare_monster_group(
        "45_45",
        budget=40,
        composition_policy={
            "allowed_roles": ["minion"],
            "min_units": 1,
            "max_units": 1,
            "role_caps": {"minion": 1, "veteran": 0, "elite": 0, "boss": 0},
            "allow_repeated_members": False,
        },
        scope_id="encounter:test",
        ttl=120,
    )

    assert storage.created is True
    assert result.group_id == "encounter:test"
    assert result.group_key == "game:monster:group:encounter:test"
    assert result.clan_id
    assert result.monster_ids
    assert result.total_power > 0
    assert set(result.actor_commitments.values()) == set(commitments.saved)
    assert all(source_ref.startswith("monster:") for source_ref in result.actor_commitments)
    assert cache.payload is not None
    first_source = next(iter(commitments.saved.values()))
    assert set(first_source) == {"meta", "source", "status", "combat"}
    assert first_source["meta"]["actor_type"] == "monster"
    assert first_source["meta"]["avatar_url"] == (
        "/static/generated-assets/monsters/generated/members/rat.webp?v=rat-image-bytes"
    )
    assert first_source["combat"]["skills"] == {"skill_fencing": 0.2}
    assert first_source["combat"]["math_model"]
    assert result.previews[0].image == "/static/generated-assets/monsters/generated/members/rat.webp?v=rat-image-bytes"
    assert result.previews[0].visual["image_url"] == (
        "/static/generated-assets/monsters/generated/members/rat.webp?v=rat-image-bytes"
    )


async def test_prepare_monster_group_allows_repeated_monster_templates() -> None:
    storage = FakeStorage()
    service = MonsterGroupService(
        repository=storage,
        location_context=FakeLocationContext(),  # type: ignore[arg-type]
        actor_commitments=FakeActorCommitments(),  # type: ignore[arg-type]
        factory=FakeClanFactory(storage),  # type: ignore[arg-type]
    )

    result = await service.prepare_monster_group(
        "45_45",
        budget=150,
        composition_policy={
            "encounter_kind": "guard",
            "encounter_difficulty": "normal",
            "budget_multiplier": 1.0,
            "allowed_roles": ["minion"],
            "min_units": 1,
            "max_units": 8,
            "role_caps": {"minion": 8, "veteran": 0, "elite": 0, "boss": 0},
            "allow_repeated_members": True,
        },
        scope_id="encounter:test",
        ttl=120,
    )

    assert len(result.monster_ids) == 8
    assert len(set(result.monster_ids)) == 1
    assert len(result.previews) == 8
    clan_members = next(iter(storage.members_by_clan.values()))
    expected_score = clan_members[0].generation_meta["balance"]["gear_score"]
    assert result.previews[0].gear_score == expected_score
    assert result.previews[0].threat_rating == expected_score
    assert set(result.actor_commitments) == {f"monster:{result.monster_ids[0]}"}


async def test_prepare_monster_group_from_clan_skips_world_location_and_hash_selection() -> None:
    storage = FakeStorage()
    commitments = FakeActorCommitments()
    cache = FakeGroupCache()
    location_context = FakeLocationContext()
    factory = FakeClanFactory(storage)
    world_context = type(
        "WorldContext",
        (),
        {"tier": 1, "zone_id": "D4_0_0"},
    )()
    clan = await factory.build_clan_template(
        context=world_context,
        family_id="rat_swarm",
        context_hash="rift-slot-context-hash",
        unique_hash="rift-slot-unique-hash",
        normalized_tags=["starter_rift", "primary"],
    )
    service = MonsterGroupService(
        repository=storage,
        location_context=location_context,  # type: ignore[arg-type]
        actor_commitments=commitments,  # type: ignore[arg-type]
        group_cache=cache,  # type: ignore[arg-type]
        factory=factory,  # type: ignore[arg-type]
    )

    result = await service.prepare_monster_group_from_clan(
        clan.id,
        budget=40,
        tier=1,
        danger=0.35,
        biome_id="broken_road",
        loc_id="rift:starter_rift:primary",
        zone_id="rift:starter_rift",
        tags=["starter_rift", "primary"],
        composition_policy={
            "allowed_roles": ["minion"],
            "min_units": 1,
            "max_units": 1,
            "role_caps": {"minion": 1, "veteran": 0, "elite": 0, "boss": 0},
            "allow_repeated_members": False,
        },
        scope_id="rift:encounter:test",
        ttl=120,
    )

    assert location_context.calls == []
    assert storage.created is True
    assert result.group_id == "rift:encounter:test"
    assert result.group_key == "game:monster:group:rift:encounter:test"
    assert result.clan_id == str(clan.id)
    assert result.family_id == "rat_swarm"
    assert result.loc_id == "rift:starter_rift:primary"
    assert result.zone_id == "rift:starter_rift"
    assert result.biome_id == "broken_road"
    assert result.context_hash == "rift-slot-context-hash"
    assert result.unique_hash == "rift-slot-unique-hash"
    assert result.tags == ["starter_rift", "primary"]
    assert result.reused_existing_clan is True
    assert result.monster_ids
    assert set(result.actor_commitments.values()) == set(commitments.saved)


async def test_prepare_monster_group_from_clan_applies_rift_composition_policy() -> None:
    storage = FakeStorage()
    commitments = FakeActorCommitments()
    clan = GeneratedClan(
        id=uuid.uuid4(),
        family_id="rat_swarm",
        tier=1,
        zone_id="rift:starter_rift",
        context_hash="rift-boss-context-hash",
        unique_hash="rift-boss-unique-hash",
        raw_tags={},
        flavor_content={},
        name_ru="Rift Rats",
        description="Rift Rats",
    )
    minion = _generated_monster(
        clan_id=clan.id,
        variant_key="minion",
        role="minion",
        gear_score=20,
        organization_type="swarm",
    )
    boss = _generated_monster(
        clan_id=clan.id,
        variant_key="heart_boss",
        role="boss",
        gear_score=160,
        organization_type="swarm",
    )
    for member in (minion, boss):
        member.clan = clan
        clan.members.append(member)
    storage.clans_by_unique[clan.unique_hash] = clan
    storage.members_by_clan[clan.id] = [minion, boss]
    service = MonsterGroupService(
        repository=storage,
        location_context=FakeLocationContext(),  # type: ignore[arg-type]
        actor_commitments=commitments,  # type: ignore[arg-type]
        factory=FakeClanFactory(storage),  # type: ignore[arg-type]
    )

    result = await service.prepare_monster_group_from_clan(
        clan.id,
        budget=60,
        tier=1,
        danger=0.0,
        biome_id="broken_road",
        loc_id="rift:starter_rift:heart",
        zone_id="rift:starter_rift",
        tags=["starter_rift", "heart_guard"],
        composition_policy={
            "allowed_roles": ["boss"],
            "required_roles": ["boss"],
            "max_units": 1,
            "allow_repeated_members": False,
        },
        scope_id="rift:boss:test",
        ttl=120,
    )

    assert result.monster_ids == [str(boss.id)]
    assert result.previews[0].role == "boss"


async def test_prepare_monster_group_from_clan_applies_family_encounter_profile() -> None:
    storage = FakeStorage()
    commitments = FakeActorCommitments()
    clan = GeneratedClan(
        id=uuid.uuid4(),
        family_id="rat_swarm",
        tier=1,
        zone_id="rift:starter_rift",
        context_hash="rift-guard-context-hash",
        unique_hash="rift-guard-unique-hash",
        raw_tags={},
        flavor_content={},
        name_ru="Rift Rats",
        description="Rift Rats",
    )
    members = [
        _generated_monster(
            clan_id=clan.id,
            variant_key="minion",
            role="minion",
            gear_score=20,
            organization_type="swarm",
        ),
        _generated_monster(
            clan_id=clan.id,
            variant_key="veteran",
            role="veteran",
            gear_score=30,
            organization_type="swarm",
        ),
        _generated_monster(
            clan_id=clan.id,
            variant_key="elite",
            role="elite",
            gear_score=50,
            organization_type="swarm",
        ),
    ]
    for member in members:
        member.clan = clan
        clan.members.append(member)
    storage.clans_by_unique[clan.unique_hash] = clan
    storage.members_by_clan[clan.id] = members
    service = MonsterGroupService(
        repository=storage,
        location_context=FakeLocationContext(),  # type: ignore[arg-type]
        actor_commitments=commitments,  # type: ignore[arg-type]
        factory=FakeClanFactory(storage),  # type: ignore[arg-type]
    )

    result = await service.prepare_monster_group_from_clan(
        clan.id,
        budget=200,
        tier=1,
        danger=0.0,
        biome_id="broken_road",
        loc_id="rift:starter_rift:guard",
        zone_id="rift:starter_rift",
        tags=["starter_rift"],
        composition_policy={"encounter_kind": "guard", "encounter_difficulty": "hard"},
        scope_id="rift:guard:test",
        ttl=120,
    )

    assert result.target_budget == 260
    assert 3 <= len(result.previews) <= 6
    assert {preview.role for preview in result.previews} <= {"veteran", "elite"}
    assert [preview.role for preview in result.previews].count("elite") >= 1
    assert [preview.role for preview in result.previews].count("elite") <= 3

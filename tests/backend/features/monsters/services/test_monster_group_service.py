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
        monster = GeneratedMonster(
            id=uuid.uuid4(),
            clan_id=clan.id,
            variant_key="sewer_rat",
            role="minion",
            member_tier=0,
            threat_rating=20,
            name_ru="Rat",
            description="Rat",
            text_content={"name_ru": "Rat"},
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
                "visual": {
                    "status": "generated",
                    "image_url": "/static/generated-assets/monsters/generated/members/rat.webp",
                },
            },
        )
        monster.clan = clan
        clan.members.append(monster)
        return await self.storage.create_clan_with_members(clan, [monster])


class FakeLocationContext:
    async def get_location_context(self, loc_id: str) -> MonsterLocationContext:
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
    result = await service.prepare_monster_group("45_45", budget=40, scope_id="encounter:test", ttl=120)

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
    assert first_source["meta"]["avatar_url"] == "/static/generated-assets/monsters/generated/members/rat.webp"
    assert first_source["combat"]["skills"] == {"skill_fencing": 0.2}
    assert first_source["combat"]["math_model"]
    assert result.previews[0].image == "/static/generated-assets/monsters/generated/members/rat.webp"

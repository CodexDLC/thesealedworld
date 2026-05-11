from __future__ import annotations

import uuid

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

    async def save_monster_sources(self, *, scope_id: str, sources: list[dict], ttl: int) -> dict[str, str]:
        del ttl
        self.saved = {f"actor:{scope_id}:monster:{source['source']['monster_id']}": source for source in sources}
        return {
            f"monster:{source['source']['monster_id']}": actor_id
            for actor_id, source in self.saved.items()
        }


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
    )

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
    assert first_source["combat"]["math_model"]

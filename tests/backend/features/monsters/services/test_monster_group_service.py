from __future__ import annotations

import uuid
from typing import Any

from src.backend.features.monsters.dto.generation import (
    GeneratedClan,
    GeneratedMonster,
    HabitatClanPoolEntryDTO,
    MonsterGenerationContext,
    MonsterHabitatDTO,
    MonsterLocationContext,
)
from src.backend.features.monsters.runtime.hashing import (
    compute_clan_identity_hash,
    compute_habitat_hash,
)
from src.backend.features.monsters.services.monster_group_service import MonsterGroupService


class FakeStorage:
    def __init__(self) -> None:
        self.clans_by_context: dict[str, list[GeneratedClan]] = {}
        self.clans_by_identity: dict[str, GeneratedClan] = {}
        self.members_by_clan: dict[uuid.UUID, list[GeneratedMonster]] = {}
        self.pool_entries: dict[tuple[str, str], list[HabitatClanPoolEntryDTO]] = {}
        self.created = False

    async def get_clan_by_identity_hash(self, identity_hash: str) -> GeneratedClan | None:
        return self.clans_by_identity.get(identity_hash)

    async def get_generated_clan(self, clan_id: uuid.UUID | str) -> GeneratedClan | None:
        clan_uuid = uuid.UUID(str(clan_id))
        for clan in self.clans_by_identity.values():
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

    async def list_habitat_clan_pool_entries(
        self,
        *,
        scope_type: str,
        scope_id: str,
        enabled_only: bool = True,
    ) -> list[HabitatClanPoolEntryDTO]:
        entries = self.pool_entries.get((scope_type, scope_id), [])
        return [entry for entry in entries if entry.enabled or not enabled_only]

    async def upsert_habitat_clan_pool_entry(self, entry: HabitatClanPoolEntryDTO) -> HabitatClanPoolEntryDTO:
        entries = self.pool_entries.setdefault((entry.scope_type, entry.scope_id), [])
        entries[:] = [item for item in entries if item.clan_identity_hash != entry.clan_identity_hash]
        entries.append(entry)
        return entry

    async def create_clan_with_members(
        self,
        clan: GeneratedClan,
        members: list[GeneratedMonster],
    ) -> GeneratedClan:
        self.created = True
        self.clans_by_identity[clan.identity_hash] = clan
        self.clans_by_context.setdefault(clan.context_hash, []).append(clan)
        self.members_by_clan[clan.id] = members
        return clan

    async def update_clan_narrative(self, clan: GeneratedClan) -> GeneratedClan:
        self.clans_by_identity[clan.identity_hash] = clan
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
        identity_hash: str,
        normalized_tags: list[str],
        reuse_existing: bool = False,
    ) -> GeneratedClan:
        del normalized_tags, reuse_existing
        clan = GeneratedClan(
            id=uuid.uuid4(),
            family_id=family_id,
            identity_hash=identity_hash,
            context_identity={"tier": context.tier, "zone_id": context.zone_id},
            context_hash=context_hash,
            selected_traits=[],
            title="Rat Swarm",
            description="Rat Swarm",
            encounter_texts={
                "patrol": "Крысы идут по следу.",
                "ambush": "Крысы вылетают из щелей.",
                "lair": "Крысы держат гнездо.",
                "random_meeting": "Крысы показываются у дороги.",
            },
            generation_version=2,
            resource_version="1",
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
    member_id = uuid.uuid4()
    snapshot = {
        "effective_tier": 1,
        "attributes": {
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
        "skills": {"skill_fencing": 0.2, "skill_scouting": 0.9},
        "items": {},
        "vitals": {"hp": {"current": 20, "max": 20}, "energy": {"current": 10, "max": 10}},
        "combat_snapshot_input": {
            "meta": {"actor_type": "monster", "variant_id": variant_key, "effective_tier": 1},
            "source": {"monster_id": str(member_id), "variant_id": variant_key},
            "status": {"hp": {"current": 20, "max": 20}},
            "raw": {"attributes": {"strength": 4}},
            "skills": {"skill_fencing": 0.2},
            "loadout": {},
        },
        "gear_score": gear_score,
    }
    return GeneratedMonster(
            id=member_id,
            clan_id=clan_id,
            variant_id=variant_key,
            member_hash=variant_key,
            role=role,
            title=variant_key,
            short_description=variant_key,
            min_tier=0,
            max_tier=7,
            mongo_actor_key=f"actor:{clan_id}:{variant_key}",
            actor_document={
                "base_projection": {
                    "visual": {
                        "status": "generated",
                        "image_url": "/static/generated-assets/monsters/generated/members/rat.webp",
                        "asset_hash": "rat-image-bytes",
                    }
                },
                "tier_snapshots": {f"tier_{tier}": {**snapshot, "effective_tier": tier} for tier in range(0, 8)},
            },
            active_snapshot=dict(snapshot),
            metadata_={
                "schema_version": 2,
                "meta": {"archetype": "beast", "tags": ["rat"]},
                "visual": {
                    "status": "generated",
                    "image_url": "/static/generated-assets/monsters/generated/members/rat.webp",
                    "asset_hash": "rat-image-bytes",
                },
            },
        )


class FakeLocationContext:
    def __init__(self, *, danger: float = 0.0) -> None:
        self.calls: list[str] = []
        self.danger = danger

    async def get_location_context(self, loc_id: str) -> MonsterLocationContext:
        self.calls.append(loc_id)
        return MonsterLocationContext(
            loc_id=loc_id,
            zone_id="D4_0_0",
            biome_id="city_ruins",
            tier=1,
            danger=self.danger,
            tags=["city_ruins", "mana_leak"],
            raw_location={"world_zone": {"region_id": "D4", "id": "D4_0_0"}},
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


async def _materialize_fake_pool_clan(
    storage: FakeStorage,
    factory: FakeClanFactory,
    *,
    scope_type: str = "region",
    scope_id: str = "D4",
    family_id: str = "rat_swarm",
    biome: str = "city_ruins",
    keys: list[str] | None = None,
    pool_tier: str = "primary",
    weight: int = 100,
) -> GeneratedClan:
    habitat = MonsterHabitatDTO(biome=biome, keys=keys or ["ancient", "ruined_old_city"])
    context_hash = compute_habitat_hash(biome=habitat.biome, keys=habitat.keys)
    identity_hash = compute_clan_identity_hash(
        family_id=family_id,
        biome=habitat.biome,
        keys=habitat.keys,
        selected_trait_keys=[],
        resource_version=1.4,
    )
    context = MonsterGenerationContext(
        zone_id=f"{scope_type}:{scope_id}",
        biome_id=habitat.biome,
        habitat=habitat,
        tier=1,
        tags=list(habitat.keys),
    )
    clan = await factory.build_clan_template(
        context=context,
        family_id=family_id,
        context_hash=context_hash,
        identity_hash=identity_hash,
        normalized_tags=list(habitat.keys),
    )
    await storage.upsert_habitat_clan_pool_entry(
        HabitatClanPoolEntryDTO(
            scope_type=scope_type,
            scope_id=scope_id,
            clan_identity_hash=identity_hash,
            family_id=family_id,
            pool_tier=pool_tier,  # type: ignore[arg-type]
            weight=weight,
            enabled=True,
            habitat=habitat,
            policy_version=1,
        )
    )
    return clan


async def test_prepare_monster_group_creates_clan_and_actor_commitments() -> None:
    storage = FakeStorage()
    commitments = FakeActorCommitments()
    cache = FakeGroupCache()
    factory = FakeClanFactory(storage)
    await _materialize_fake_pool_clan(storage, factory)
    service = MonsterGroupService(
        repository=storage,
        location_context=FakeLocationContext(),  # type: ignore[arg-type]
        actor_commitments=commitments,  # type: ignore[arg-type]
        group_cache=cache,  # type: ignore[arg-type]
        factory=factory,  # type: ignore[arg-type]
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
    assert first_source["meta"]["effective_tier"] == 1
    assert first_source["combat"]["skills"] == {"skill_fencing": 0.2}
    assert "math_model" in first_source["combat"]
    assert result.previews[0].image == "/static/generated-assets/monsters/generated/members/rat.webp?v=rat-image-bytes"
    assert result.previews[0].visual["image_url"] == (
        "/static/generated-assets/monsters/generated/members/rat.webp?v=rat-image-bytes"
    )


async def test_prepare_monster_group_allows_repeated_monster_templates() -> None:
    storage = FakeStorage()
    factory = FakeClanFactory(storage)
    await _materialize_fake_pool_clan(storage, factory)
    service = MonsterGroupService(
        repository=storage,
        location_context=FakeLocationContext(),  # type: ignore[arg-type]
        actor_commitments=FakeActorCommitments(),  # type: ignore[arg-type]
        factory=factory,  # type: ignore[arg-type]
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

    assert len(result.monster_ids) == 3
    assert len(set(result.monster_ids)) == 1
    assert len(result.previews) == 3
    clan_members = next(iter(storage.members_by_clan.values()))
    expected_score = clan_members[0].active_snapshot["gear_score"]
    assert result.previews[0].gear_score == expected_score
    assert result.previews[0].threat_rating == expected_score
    assert set(result.actor_commitments) == {f"monster:{result.monster_ids[0]}"}


async def test_prepare_monster_group_does_not_apply_location_danger_budget_bonus() -> None:
    storage = FakeStorage()
    factory = FakeClanFactory(storage)
    await _materialize_fake_pool_clan(storage, factory)
    service = MonsterGroupService(
        repository=storage,
        location_context=FakeLocationContext(danger=1.0),  # type: ignore[arg-type]
        actor_commitments=FakeActorCommitments(),  # type: ignore[arg-type]
        factory=factory,  # type: ignore[arg-type]
    )

    result = await service.prepare_monster_group(
        "45_45",
        budget=100,
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

    assert result.target_budget == 100
    assert result.adjusted_budget == 100


async def test_prepare_monster_group_for_scope_skips_world_location_and_uses_pool_contract() -> None:
    storage = FakeStorage()
    commitments = FakeActorCommitments()
    cache = FakeGroupCache()
    location_context = FakeLocationContext()
    factory = FakeClanFactory(storage)
    clan = await _materialize_fake_pool_clan(
        storage,
        factory,
        scope_type="rift",
        scope_id="starter_rift",
        biome="broken_road",
        keys=["road_tract", "scavenger_camp"],
    )
    service = MonsterGroupService(
        repository=storage,
        location_context=location_context,  # type: ignore[arg-type]
        actor_commitments=commitments,  # type: ignore[arg-type]
        group_cache=cache,  # type: ignore[arg-type]
        factory=factory,  # type: ignore[arg-type]
    )

    result = await service.prepare_monster_group_for_scope(
        scope_type="rift",
        scope_id="starter_rift",
        budget=40,
        tier=1,
        danger=0.35,
        biome_id="broken_road",
        loc_id="rift:starter_rift:primary",
        zone_id="rift:starter_rift",
        composition_policy={
            "allowed_roles": ["minion"],
            "min_units": 1,
            "max_units": 1,
            "role_caps": {"minion": 1, "veteran": 0, "elite": 0, "boss": 0},
            "allow_repeated_members": False,
        },
        group_scope_id="rift:encounter:test",
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
    assert result.context_hash == clan.context_hash
    assert result.unique_hash == clan.identity_hash
    assert result.tags == ["broken_road", "road_tract", "scavenger_camp"]
    assert result.reused_existing_clan is True
    assert result.monster_ids
    assert set(result.actor_commitments.values()) == set(commitments.saved)


async def test_prepare_monster_group_for_scope_applies_rift_composition_policy() -> None:
    storage = FakeStorage()
    commitments = FakeActorCommitments()
    habitat = MonsterHabitatDTO(biome="broken_road", keys=["road_tract", "scavenger_camp"])
    context_hash = compute_habitat_hash(biome=habitat.biome, keys=habitat.keys)
    identity_hash = compute_clan_identity_hash(
        family_id="rat_swarm",
        biome=habitat.biome,
        keys=habitat.keys,
        selected_trait_keys=[],
        resource_version=1.4,
    )
    clan = GeneratedClan(
        id=uuid.uuid4(),
        family_id="rat_swarm",
        identity_hash=identity_hash,
        context_identity={"tier": 1, "zone_id": "rift:starter_rift"},
        context_hash=context_hash,
        selected_traits=[],
        title="Rift Rats",
        description="Rift Rats",
        encounter_texts={
            "patrol": "Крысы идут вдоль рифта.",
            "ambush": "Крысы бросаются из разлома.",
            "lair": "Крысы держат рифтовое гнездо.",
            "random_meeting": "Крысы выходят к дороге.",
        },
        generation_version=2,
        resource_version="1.4",
    )
    minion = _generated_monster(
        clan_id=clan.id,
        variant_key="sewer_rat",
        role="minion",
        gear_score=20,
        organization_type="swarm",
    )
    boss = _generated_monster(
        clan_id=clan.id,
        variant_key="rat_king",
        role="boss",
        gear_score=160,
        organization_type="swarm",
    )
    for member in (minion, boss):
        member.clan = clan
        clan.members.append(member)
    storage.clans_by_identity[clan.identity_hash] = clan
    storage.clans_by_context[clan.context_hash] = [clan]
    storage.members_by_clan[clan.id] = [minion, boss]
    await storage.upsert_habitat_clan_pool_entry(
        HabitatClanPoolEntryDTO(
            scope_type="rift",
            scope_id="starter_rift",
            clan_identity_hash=identity_hash,
            family_id="rat_swarm",
            pool_tier="primary",
            weight=100,
            habitat=habitat,
        )
    )
    service = MonsterGroupService(
        repository=storage,
        location_context=FakeLocationContext(),  # type: ignore[arg-type]
        actor_commitments=commitments,  # type: ignore[arg-type]
        factory=FakeClanFactory(storage),  # type: ignore[arg-type]
    )

    result = await service.prepare_monster_group_for_scope(
        scope_type="rift",
        scope_id="starter_rift",
        budget=60,
        tier=4,
        danger=0.0,
        biome_id="broken_road",
        loc_id="rift:starter_rift:heart",
        zone_id="rift:starter_rift",
        composition_policy={
            "allowed_roles": ["boss"],
            "required_roles": ["boss"],
            "max_units": 1,
            "allow_repeated_members": False,
        },
        group_scope_id="rift:boss:test",
        ttl=120,
    )

    assert result.monster_ids == [str(boss.id)]
    assert result.previews[0].role == "boss"


async def test_prepare_monster_group_for_scope_applies_family_encounter_profile() -> None:
    storage = FakeStorage()
    commitments = FakeActorCommitments()
    habitat = MonsterHabitatDTO(biome="broken_road", keys=["road_tract", "scavenger_camp"])
    context_hash = compute_habitat_hash(biome=habitat.biome, keys=habitat.keys)
    identity_hash = compute_clan_identity_hash(
        family_id="rat_swarm",
        biome=habitat.biome,
        keys=habitat.keys,
        selected_trait_keys=[],
        resource_version=1.4,
    )
    clan = GeneratedClan(
        id=uuid.uuid4(),
        family_id="rat_swarm",
        identity_hash=identity_hash,
        context_identity={"tier": 1, "zone_id": "rift:starter_rift"},
        context_hash=context_hash,
        selected_traits=[],
        title="Rift Rats",
        description="Rift Rats",
        encounter_texts={
            "patrol": "Крысы идут вдоль рифта.",
            "ambush": "Крысы бросаются из разлома.",
            "lair": "Крысы держат рифтовое гнездо.",
            "random_meeting": "Крысы выходят к дороге.",
        },
        generation_version=2,
        resource_version="1.4",
    )
    members = [
        _generated_monster(
            clan_id=clan.id,
            variant_key="sewer_rat",
            role="minion",
            gear_score=20,
            organization_type="swarm",
        ),
        _generated_monster(
            clan_id=clan.id,
            variant_key="tunnel_rat",
            role="veteran",
            gear_score=30,
            organization_type="swarm",
        ),
        _generated_monster(
            clan_id=clan.id,
            variant_key="plague_rat",
            role="elite",
            gear_score=50,
            organization_type="swarm",
        ),
    ]
    for member in members:
        member.clan = clan
        clan.members.append(member)
    storage.clans_by_identity[clan.identity_hash] = clan
    storage.clans_by_context[clan.context_hash] = [clan]
    storage.members_by_clan[clan.id] = members
    await storage.upsert_habitat_clan_pool_entry(
        HabitatClanPoolEntryDTO(
            scope_type="rift",
            scope_id="starter_rift",
            clan_identity_hash=identity_hash,
            family_id="rat_swarm",
            pool_tier="primary",
            weight=100,
            habitat=habitat,
        )
    )
    service = MonsterGroupService(
        repository=storage,
        location_context=FakeLocationContext(),  # type: ignore[arg-type]
        actor_commitments=commitments,  # type: ignore[arg-type]
        factory=FakeClanFactory(storage),  # type: ignore[arg-type]
    )

    result = await service.prepare_monster_group_for_scope(
        scope_type="rift",
        scope_id="starter_rift",
        budget=200,
        tier=1,
        danger=0.0,
        biome_id="broken_road",
        loc_id="rift:starter_rift:guard",
        zone_id="rift:starter_rift",
        composition_policy={"encounter_kind": "guard", "encounter_difficulty": "hard"},
        group_scope_id="rift:guard:test",
        ttl=120,
    )

    assert result.target_budget == 260
    assert result.encounter_texts["lair"] == "Крысы держат рифтовое гнездо."
    assert 3 <= len(result.previews) <= 6
    assert {preview.role for preview in result.previews} <= {"veteran", "elite"}
    assert [preview.role for preview in result.previews].count("elite") >= 1
    assert [preview.role for preview in result.previews].count("elite") <= 3
    for preview in result.previews:
        assert preview.detected_ru == ""
        assert preview.ambush_ru == ""
        assert preview.idle_ru == ""

from __future__ import annotations

import uuid

import pytest

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService
from src.backend.features.monsters.services.generated_view_service import GeneratedMonsterViewService


class FakeGeneratedMonsterRepository:
    def __init__(self, clans: list[GeneratedClan]) -> None:
        self.clans = clans
        self.refresh_calls: list[uuid.UUID] = []
        self.light_calls: list[dict] = []
        self.visual_task_calls = 0

    async def count_generated_clans(self, **kwargs) -> int:
        return len(self.clans)

    async def list_generated_clans_page(self, **kwargs) -> list[GeneratedClan]:
        return self.clans

    async def list_generated_clans_page_light(self, **kwargs) -> list[GeneratedClan]:
        self.light_calls.append(dict(kwargs))
        return self.clans

    async def refresh_clan_gear_scores(
        self,
        clan_id,
        *,
        gear_score_service,
        persist: bool = False,
    ) -> list[GeneratedMonster]:
        assert persist is True
        self.refresh_calls.append(clan_id)
        clan = next(clan for clan in self.clans if clan.id == clan_id)
        gear_score_service.refresh_stale_monster_scores(clan.members)
        gear_score_service.apply_clan_summary(clan)
        return clan.members

    async def list_latest_visual_generation_tasks(self, *, entity_ids: set[str], asset_hashes: set[str]):
        del entity_ids, asset_hashes
        self.visual_task_calls += 1
        return {}

    async def generated_monsters_summary(self, *, family_id: str | None = None) -> dict[str, int]:
        assert family_id in {None, "rat_swarm"}
        return {"clans": len(self.clans), "members": sum(len(clan.members) for clan in self.clans), "missing_images": 0}


@pytest.mark.unit
async def test_generated_view_projects_visual_storage_and_equipment_summary() -> None:
    clan_id = uuid.uuid4()
    member_id = uuid.uuid4()
    member = GeneratedMonster(
        id=member_id,
        clan_id=clan_id,
        variant_id="bandit_cutthroat",
        member_hash="member-hash",
        role="minion",
        title="Cutthroat",
        short_description="A quick knife fighter.",
        min_tier=1,
        max_tier=3,
        mongo_actor_key="actor:bandit",
        metadata_={
            "visual": {
                "status": "generated",
                "image_url": "/static/generated-assets/monsters/member.webp",
                "storage_key": "monsters/member.webp",
                "storage_backend": "local",
            },
        },
        active_snapshot={
            "member_tier": 2,
            "text_content": {
                "name_ru": "Old snapshot name",
                "short_name_ru": "Old snapshot name",
                "appearance_ru": "В плаще с ржавым ножом.",
                "behavior_ru": "Держится сбоку.",
            },
            "scaled_attributes": {"strength": 12},
            "scaled_skills": {"skill_swords": 0.3},
            "items": {
                "layout": {"equipment": {"main_hand": "knife-1", "body": "coat-1"}},
                "by_id": {
                    "knife-1": {"name_ru": "Rust knife", "kind": "weapon", "affixes": ["sharp"]},
                    "coat-1": {"name_ru": "Patched coat", "kind": "armor", "affixes": ["worn"]},
                },
            },
            "vitals": {"hp": {"current": 50, "max": 50}},
            "ai_profile": {"profile": "aggressive"},
            "balance": {"organization_type": "gang"},
            "gear_score": 11,
            "combat_snapshot_input": {"meta": {"source": "generated_monsters"}},
        },
        actor_document={"tier_snapshots": {}},
    )
    clan = GeneratedClan(
        id=clan_id,
        family_id="bandit_gang",
        identity_hash="unique",
        context_identity={"zone_id": "zone-a", "tier": 2},
        context_hash="ctx",
        selected_traits=[],
        title="Bandits",
        description="A gang",
        encounter_texts={},
        generation_version=1,
        resource_version="1",
        metadata_={
            "seed": "test",
            "flavor_content": {
                "variants_flavor": {
                    "bandit_cutthroat": {
                        "display_name": {"ru": "Ножевой Дозорный", "en": "Knife Lookout"},
                        "name": "Ножевой Дозорный",
                        "short_description": {
                            "ru": "Быстрый боец с ножом.",
                            "en": "A quick knife fighter.",
                        },
                        "appearance": {
                            "ru": "плащ и ржавый нож",
                            "en": "cloak and rusty knife",
                        },
                        "visual_hint": {
                            "ru": "плащ и ржавый нож",
                            "en": "patched cloak, rusty knife",
                        },
                    }
                }
            },
            "visual": {
                "status": "generated",
                "image_url": "/static/generated-assets/monsters/clan.webp",
                "storage_key": "monsters/clan.webp",
                "storage_backend": "local",
            }
        },
        context={"biome": "ruins"},
        source_context={"source": "test"},
        members=[member],
    )
    member.clan = clan

    result = await GeneratedMonsterViewService(FakeGeneratedMonsterRepository([clan])).list_generated()

    item = result.items[0]
    assert item.visual.image_url == "/static/generated-assets/monsters/clan.webp"
    assert item.visual.storage_key == "monsters/clan.webp"
    assert item.members[0].visual.image_url == "/static/generated-assets/monsters/member.webp"
    assert item.members[0].description == "A quick knife fighter."
    assert item.members[0].monster_id == str(member_id)
    assert item.members[0].variant_key == "bandit_cutthroat"
    assert item.members[0].member_tier == 2
    assert item.members[0].name_ru == "Cutthroat"
    assert item.members[0].localized["display_name"]["en"] == "Knife Lookout"
    assert item.members[0].gear_score == 11
    assert item.members[0].text_content == {
        "appearance_ru": "плащ и ржавый нож",
        "behavior_ru": "Держится сбоку.",
        "description_ru": "A quick knife fighter.",
        "localized": {
            "appearance": {
                "en": "cloak and rusty knife",
                "ru": "плащ и ржавый нож",
            },
            "display_name": {
                "en": "Knife Lookout",
                "ru": "Ножевой Дозорный",
            },
            "short_description": {
                "en": "A quick knife fighter.",
                "ru": "Быстрый боец с ножом.",
            },
            "visual_hint": {
                "en": "patched cloak, rusty knife",
                "ru": "плащ и ржавый нож",
            },
        },
        "name_ru": "Cutthroat",
        "short_name_ru": "Cutthroat",
        "visual_hint": "плащ и ржавый нож",
    }
    assert item.metadata_["seed"] == "test"
    assert item.metadata_["visual"]["storage_key"] == "monsters/clan.webp"
    assert item.context == {"biome": "ruins"}
    assert item.source_context == {"source": "test"}
    assert item.members[0].scaled_attributes == {"strength": 12}
    assert item.members[0].scaled_skills == {"skill_swords": 0.3}
    assert item.members[0].items["layout"]["equipment"]["main_hand"] == "knife-1"
    assert item.members[0].vitals == {"hp": {"current": 50, "max": 50}}
    assert item.members[0].ai_profile == {"profile": "aggressive"}
    assert item.members[0].combat_actor_snapshot == {"meta": {"source": "generated_monsters"}}
    assert "base_cost" not in item.members[0].model_dump()
    assert "effective_cost" not in item.members[0].model_dump()
    assert item.members[0].equipment_summary.equipment == ["body: Patched coat", "main_hand: Rust knife"]
    assert item.members[0].equipment_summary.weapons == ["main_hand: Rust knife"]
    assert item.members[0].equipment_summary.armor == ["body: Patched coat"]
    assert item.members[0].equipment_summary.affixes == ["sharp", "worn"]


@pytest.mark.unit
async def test_generated_view_projects_snapshot_gear_scores_without_legacy_refresh() -> None:
    clan_id = uuid.uuid4()
    member = GeneratedMonster(
        id=uuid.uuid4(),
        clan_id=clan_id,
        variant_id="bandit_thug",
        member_hash="member-hash",
        role="minion",
        title="Thug",
        short_description="",
        min_tier=0,
        max_tier=1,
        mongo_actor_key="actor:thug",
        active_snapshot={
            "member_tier": 0,
            "text_content": {},
            "scaled_attributes": {
                "strength": 8,
                "agility": 6,
                "endurance": 8,
                "intellect": 1,
                "memory": 1,
                "mental": 2,
                "perception": 4,
                "projection": 1,
                "prediction": 2,
            },
            "scaled_skills": {"skill_tactics": 0.1},
            "items": {},
            "vitals": {},
            "ai_profile": {},
            "balance": {"gear_score_version": 1},
            "gear_score": 999,
        },
    )
    clan = GeneratedClan(
        id=clan_id,
        family_id="bandit_gang",
        identity_hash="unique",
        context_identity={"zone_id": "zone-a", "tier": 1},
        context_hash="ctx",
        selected_traits=[],
        title="Bandits",
        description="A gang",
        encounter_texts={},
        generation_version=1,
        resource_version="1",
        members=[member],
    )
    member.clan = clan
    repository = FakeGeneratedMonsterRepository([clan])

    result = await GeneratedMonsterViewService(repository).list_generated()

    assert repository.refresh_calls == []
    assert result.items[0].members[0].gear_score == 999
    assert result.items[0].members[0].generation_meta["balance"]["gear_score_version"] == 1


@pytest.mark.unit
async def test_generated_view_light_mode_skips_visual_task_lookup_and_uses_light_repository() -> None:
    clan_id = uuid.uuid4()
    member = GeneratedMonster(
        id=uuid.uuid4(),
        clan_id=clan_id,
        variant_id="rat_scout",
        member_hash="member-hash",
        role="minion",
        title="Rat Scout",
        short_description="",
        min_tier=1,
        max_tier=1,
        mongo_actor_key="actor:rat",
        metadata_={"visual": {"image_url": "/static/generated-assets/member.webp", "storage_backend": "local"}},
    )
    clan = GeneratedClan(
        id=clan_id,
        family_id="rat_swarm",
        identity_hash="unique",
        context_identity={
            "zone_id": "zone-a",
            "tier": 1,
            "gear_score_summary": {"count": 1, "min": 3, "avg": 3.0, "max": 3, "total": 3},
        },
        context_hash="ctx",
        selected_traits=[],
        title="Rats",
        description="A swarm",
        encounter_texts={},
        generation_version=1,
        resource_version="1",
        metadata_={"visual": {"image_url": "/static/generated-assets/clan.webp", "storage_backend": "local"}},
        members=[member],
    )
    member.clan = clan
    repository = FakeGeneratedMonsterRepository([clan])

    result = await GeneratedMonsterViewService(repository).list_generated(light=True)

    assert repository.light_calls == [
        {"family_id": None, "clan_id": None, "limit": 25, "offset": 0, "include_members": True}
    ]
    assert repository.visual_task_calls == 0
    assert result.items[0].gear_score_summary.count == 1
    assert result.items[0].members[0].visual.image_url == "/static/generated-assets/member.webp"


@pytest.mark.unit
async def test_generated_view_summary_uses_repository_aggregate() -> None:
    repository = FakeGeneratedMonsterRepository([])

    result = await GeneratedMonsterViewService(repository).summary(family_id="rat_swarm")

    assert result.clans == 0
    assert result.members == 0
    assert result.missing_images == 0


@pytest.mark.unit
async def test_generated_view_projects_failed_visual_task_reason() -> None:
    clan_id = uuid.uuid4()
    member_id = uuid.uuid4()
    member = GeneratedMonster(
        id=member_id,
        clan_id=clan_id,
        variant_id="scavenger_rat",
        member_hash="member-hash",
        role="minion",
        title="Rat",
        short_description="",
        min_tier=1,
        max_tier=1,
        mongo_actor_key="actor:rat",
        metadata_={
            "visual": {
                "status": "pending",
                "image_url": "/static/images/monsters/families/rat_swarm.svg",
                "storage_key": "monsters/generated/members/hash.webp",
                "storage_backend": "s3",
                "asset_hash": "hash",
            },
        },
    )
    clan = GeneratedClan(
        id=clan_id,
        family_id="rat_swarm",
        identity_hash="unique",
        context_identity={"zone_id": "zone-a", "tier": 1},
        context_hash="ctx",
        selected_traits=[],
        title="Rats",
        description="A swarm",
        encounter_texts={},
        generation_version=1,
        resource_version="1",
        members=[member],
    )
    member.clan = clan
    repository = FakeGeneratedMonsterRepository([clan])

    async def failed_tasks(*, entity_ids: set[str], asset_hashes: set[str]):
        assert str(member_id) in entity_ids
        assert "hash" in asset_hashes
        return {
            f"entity:{member_id}": {
                "task_id": "task-failed",
                "status": "failed",
                "attempts": 3,
                "max_attempts": 5,
                "error_type": "JSONDecodeError",
                "error_message": "Expecting value",
            }
        }

    repository.list_latest_visual_generation_tasks = failed_tasks  # type: ignore[method-assign]

    result = await GeneratedMonsterViewService(repository).list_generated()

    visual = result.items[0].members[0].visual
    assert visual.status == "failed"
    assert visual.image_url == "/static/images/monsters/families/rat_swarm.svg"
    assert visual.task_id == "task-failed"
    assert visual.task_status == "failed"
    assert visual.task_attempts == 3
    assert visual.task_max_attempts == 5
    assert visual.task_error_type == "JSONDecodeError"
    assert visual.task_error_message == "Expecting value"
    assert result.items[0].gear_score_summary.version == MonsterGearScoreService.VERSION

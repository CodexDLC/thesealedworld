from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.studio.features.cabinet.modules.content_ops.cabinet as content_ops
from fastapi_cabinet import include_cabinet
from src.frontend.cabinet import CABINET_MODULES
from src.studio.features.cabinet.modules.content_ops.cabinet import (
    ContentOpsAdmin,
    _filter_monster_clans,
    _find_member,
    _load_monster_browser_context,
    _monster_browser_redirect_url,
)
from src.studio.integrations.backend_api.admin_monsters import (
    AdminAIGenerationTask,
    AdminGeneratedMonsterClan,
    AdminGeneratedMonsterMember,
    AdminMonsterVisual,
)


def test_content_ops_admin_declares_operational_sections() -> None:
    assert ContentOpsAdmin.key == "content_ops"
    assert ContentOpsAdmin.path == "/admin/content-ops"
    assert ContentOpsAdmin.label == "Монстры"
    assert ContentOpsAdmin.group_label == "Контент"
    assert [item.key for item in ContentOpsAdmin.sidebar] == ["overview", "monsters", "monster_maintenance"]
    assert [item.label for item in ContentOpsAdmin.sidebar] == [
        "Обзор",
        "Сгенерированные монстры",
        "Обслуживание монстров",
    ]
    assert [item.path for item in ContentOpsAdmin.sidebar] == [
        "/admin/content-ops",
        "/admin/content-ops/monster-browser",
        "/admin/content-ops/monster-maintenance",
    ]
    assert "monster-browser" in ContentOpsAdmin.action_routes
    assert "monster-detail" in ContentOpsAdmin.action_routes
    assert "monster-member-detail" in ContentOpsAdmin.action_routes
    assert "monster-maintenance" in ContentOpsAdmin.action_routes
    assert "monster-rebuild-plan" in ContentOpsAdmin.action_routes
    assert "monster-rebuild-apply" in ContentOpsAdmin.action_routes
    assert "regenerate-clan-flavor" in ContentOpsAdmin.action_routes
    assert "regenerate-clan-member-images" in ContentOpsAdmin.action_routes
    assert "regenerate-visible-member-images" in ContentOpsAdmin.action_routes


def test_content_ops_filters_monsters_by_domain_safe_fields() -> None:
    rat = _clan("rat-clan", family="rats", tier=1, storage="s3", roles=("scout", "brute"), missing_member=False)
    spider = _clan("spider-clan", family="spiders", tier=2, storage="local", roles=("caster",), missing_member=True)

    filtered = _filter_monster_clans(
        [rat, spider],
        {"family_id": "spiders", "tier": "", "storage_backend": "", "missing_image": ""},
    )
    assert [clan.clan_id for clan in filtered] == ["spider-clan"]

    filtered = _filter_monster_clans(
        [rat, spider],
        {"family_id": "", "tier": "1", "storage_backend": "s3", "missing_image": ""},
    )
    assert [clan.clan_id for clan in filtered] == ["rat-clan"]

    filtered = _filter_monster_clans(
        [rat, spider],
        {"family_id": "", "tier": "", "storage_backend": "", "missing_image": "1"},
    )
    assert [clan.clan_id for clan in filtered] == ["spider-clan"]


def test_content_ops_custom_pages_render_operational_surfaces() -> None:
    app = FastAPI()
    include_cabinet(app, modules=CABINET_MODULES, mount_path="/admin")
    client = TestClient(app)

    monsters = client.get("/admin/content-ops/monster-browser")
    assert monsters.status_code == 200
    assert "Сгенерированные монстры" in monsters.text
    assert "Тир семьи" in monsters.text
    assert "Без изображения" in monsters.text
    assert "Перегенерировать картинки участников" in monsters.text

    maintenance = client.get("/admin/content-ops/monster-maintenance")
    assert maintenance.status_code == 200
    assert "Обслуживание монстров" in maintenance.text
    assert "Проверить расхождения" in maintenance.text
    assert "Пересобрать" in maintenance.text


def test_content_ops_rebuild_plan_renders_result_items(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAdminMonstersApi:
        async def list_generated(self, *, limit: int, **kwargs):
            assert limit == 100
            assert kwargs["light"] is True
            return [_clan("rat-clan", family="rats", storage="local", roles=("scout",), missing_member=False)]

        async def plan_generated_rebuild(self, **kwargs):
            assert kwargs["family_id"] == "rats"
            return {
                "dry_run": True,
                "status": "ok",
                "scanned": 1,
                "stale": 1,
                "rebuilt": 0,
                "skipped": 0,
                "errors": [],
                "items": [
                    {
                        "clan_id": "rat-clan",
                        "family_id": "rats",
                        "status": "stale",
                        "members_expected": 12,
                        "members_changed": 2,
                        "members_created": 0,
                        "members_removed": 0,
                        "reason": "changed=2",
                    }
                ],
            }

    monkeypatch.setattr(content_ops, "_api", lambda request: FakeAdminMonstersApi())
    app = FastAPI()
    include_cabinet(app, modules=CABINET_MODULES, mount_path="/admin")
    client = TestClient(app)

    response = client.post(
        "/admin/content-ops/monster-rebuild-plan",
        data={"family_id": "rats", "limit": "100", "remove_obsolete_members": "1"},
    )

    assert response.status_code == 200
    assert "План пересборки" in response.text
    assert "rat-clan" in response.text
    assert "changed=2" in response.text


def test_content_ops_detail_pages_render_domain_summary_instead_of_raw_json(monkeypatch: pytest.MonkeyPatch) -> None:
    clan = _clan("rat-clan", family="rats", storage="local", roles=("scout",), missing_member=False)

    class FakeAdminMonstersApi:
        async def get_generated_clan(self, clan_id: str):
            assert clan_id == "rat-clan"
            return clan

    monkeypatch.setattr(content_ops, "_api", lambda request: FakeAdminMonstersApi())
    app = FastAPI()
    include_cabinet(app, modules=CABINET_MODULES, mount_path="/admin")
    client = TestClient(app)

    clan_response = client.get("/admin/content-ops/monster-detail?id=rat-clan")
    assert clan_response.status_code == 200
    assert "Профиль сгенерированной семьи" in clan_response.text
    assert "Перезаказать описания" in clan_response.text
    assert "Перезаказать картинки участников" in clan_response.text
    assert "Перегенерировать изображение семьи" not in clan_response.text
    assert "city_ruins" in clan_response.text
    assert "mid" in clan_response.text
    assert "combat-v2" in clan_response.text
    assert "Тексты встреч" in clan_response.text
    assert "Патруль" in clan_response.text
    assert "Крысы идут по следу." in clan_response.text
    assert "Засада" in clan_response.text
    assert "Крысы бросаются из щелей." in clan_response.text
    assert "переделка городского лома" in clan_response.text
    assert "Состав шаблона" in clan_response.text
    assert "0..7" in clan_response.text
    assert "scout" in clan_response.text
    assert "Persisted JSON" not in clan_response.text
    assert "raw_tags" not in clan_response.text

    member_response = client.get("/admin/content-ops/monster-member-detail?clan_id=rat-clan&member_id=rat-clan-scout")
    assert member_response.status_code == 200
    assert "Боевой профиль" in member_response.text
    assert "Атрибуты" in member_response.text
    assert "Мечи" in member_response.text
    assert "Физическая защита" in member_response.text
    assert "+4.0%" in member_response.text
    assert "Предметы и аффиксы" in member_response.text
    assert "Правая рука" in member_response.text
    assert "Ржавый топор" in member_response.text
    assert "Power 2.4" in member_response.text
    assert "Кровоточащий край" in member_response.text
    assert "Урон кровотечения +6.0%" in member_response.text
    assert "skill_swords" not in member_response.text
    assert "physical_resistance" not in member_response.text
    assert "base " not in member_response.text
    assert "per tier" not in member_response.text
    assert "Persisted JSON" not in member_response.text
    assert "generation_meta" not in member_response.text


def test_content_ops_regeneration_redirects_to_visible_task_status(monkeypatch: pytest.MonkeyPatch) -> None:
    clan = _clan("rat-clan", family="rats", storage="local", roles=("scout",), missing_member=False)

    class FakeAdminMonstersApi:
        async def regenerate_clan_flavor(self, clan_id: str):
            assert clan_id == "rat-clan"
            return {"task_id": "task-flavor", "status": "pending", "requested": 1}

        async def get_generated_clan(self, clan_id: str):
            assert clan_id == "rat-clan"
            return clan

        async def get_generation_task(self, task_id: str):
            assert task_id == "task-flavor"
            return AdminAIGenerationTask(
                task_id="task-flavor",
                task_type="monster.clan_flavor",
                entity_type="monster_clan",
                entity_id="rat-clan",
                output_kind="json",
                status="pending",
            )

    monkeypatch.setattr(content_ops, "_api", lambda request: FakeAdminMonstersApi())
    app = FastAPI()
    include_cabinet(app, modules=CABINET_MODULES, mount_path="/admin")
    client = TestClient(app)

    response = client.post(
        "/admin/content-ops/regenerate-clan-flavor",
        data={"clan_id": "rat-clan"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    location = response.headers["location"]
    assert "ai_kind=clan_flavor" in location
    assert "ai_task_ids=task-flavor" in location

    detail = client.get(location)

    assert detail.status_code == 200
    assert "Описания семьи" in detail.text
    assert "Задача поставлена в очередь." in detail.text
    assert "task-flavor" in detail.text
    assert "очередь" in detail.text or "pending" in detail.text
    assert 'http-equiv="refresh"' in detail.text


def test_content_ops_task_notice_renders_done_and_failed_states(monkeypatch: pytest.MonkeyPatch) -> None:
    clan = _clan("rat-clan", family="rats", storage="local", roles=("scout",), missing_member=False)
    task_statuses = {"task-done": "done", "task-failed": "failed"}

    class FakeAdminMonstersApi:
        async def get_generated_clan(self, clan_id: str):
            assert clan_id == "rat-clan"
            return clan

        async def get_generation_task(self, task_id: str):
            return AdminAIGenerationTask(
                task_id=task_id,
                task_type="monster.member_visual",
                entity_type="monster_member",
                entity_id="rat-clan-scout",
                output_kind="image",
                status=task_statuses[task_id],
                error={"message": "provider rejected prompt"} if task_id == "task-failed" else {},
            )

    monkeypatch.setattr(content_ops, "_api", lambda request: FakeAdminMonstersApi())
    app = FastAPI()
    include_cabinet(app, modules=CABINET_MODULES, mount_path="/admin")
    client = TestClient(app)

    done = client.get("/admin/content-ops/monster-detail?id=rat-clan&ai_kind=member_image&ai_task_ids=task-done")
    failed = client.get("/admin/content-ops/monster-detail?id=rat-clan&ai_kind=member_image&ai_task_ids=task-failed")

    assert "Задача закончилась успешно." in done.text
    assert "готово" in done.text
    assert 'http-equiv="refresh"' not in done.text
    assert "Одна или несколько задач завершились ошибкой." in failed.text
    assert "provider rejected prompt" in failed.text
    assert "ошибка" in failed.text


def test_monster_browser_redirect_preserves_bulk_filters() -> None:
    form = {
        "family_id": "rat_swarm",
        "tier": "1",
        "storage_backend": "s3",
        "missing_image": "1",
    }

    assert (
        _monster_browser_redirect_url(form)
        == "/admin/content-ops/monster-browser?family_id=rat_swarm&tier=1&storage_backend=s3&missing_image=1"
    )


def test_content_ops_finds_member_for_detail_page() -> None:
    clan = _clan("rat-clan", family="rats", storage="local", roles=("scout",), missing_member=False)

    member = _find_member(clan, "rat-clan-scout")

    assert member is not None
    assert member.description == "scout description"
    assert member.text_content == {"appearance_ru": "scout appearance"}
    assert member.items["layout"] == {"equipment": {"main_hand": "hatchet"}}
    assert member.scaled_attributes == {"strength": 10}


@pytest.mark.asyncio
async def test_monster_count_provider_uses_summary_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAdminMonstersApi:
        async def get_generated_summary(self):
            return SimpleNamespace(clans=6, members=72, missing_images=1)

        async def list_generated(self, **kwargs):
            raise AssertionError(f"overview metric must not load generated list: {kwargs}")

    monkeypatch.setattr(content_ops, "_api", lambda request: FakeAdminMonstersApi())

    metric = await content_ops._monster_count_provider(SimpleNamespace())

    assert metric.value == "6"
    assert metric.subtitle == "участников 72 / без изображения 1"


@pytest.mark.asyncio
async def test_monster_browser_uses_backend_contract_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAdminMonstersApi:
        async def list_generated(self, *, limit: int, **kwargs):
            assert limit == 100
            assert kwargs["light"] is True
            return [_clan("rat-clan", family="rats", storage="local", roles=("scout",), missing_member=False)]

    monkeypatch.setattr(content_ops, "_api", lambda request: FakeAdminMonstersApi())

    browser = await _load_monster_browser_context(SimpleNamespace(query_params={}))

    assert browser.error == ""
    assert browser.total_clans == 1
    assert browser.total_members == 1
    assert browser.tier_options == [1]


def _clan(
    clan_id: str,
    *,
    family: str,
    tier: int = 1,
    storage: str,
    roles: tuple[str, ...],
    missing_member: bool,
) -> AdminGeneratedMonsterClan:
    return AdminGeneratedMonsterClan(
        clan_id=clan_id,
        family_id=family,
        tier=tier,
        zone_id="zone",
        context_hash="context",
        unique_hash="unique",
        raw_tags={
            "biome_id": "city_ruins",
            "difficulty": "mid",
            "family_resource_version": "family-v1",
            "combat_math_version": "combat-v2",
            "tags": ["rift", "roadside"],
            "context_meta": {"source": "test"},
            "gear_score_summary": {"count": len(roles), "avg": 12, "min": 9, "max": 15},
            "variant_window": {"min_tier": 0, "max_tier": 7},
            "composition": list(roles),
        },
        flavor_content={
            "visual": {},
            "loot_culture": {
                "craft_style": "переделка городского лома",
                "tone_hints": ["ржавчина", "ремни"],
            },
        },
        encounter_texts={
            "patrol": "Крысы идут по следу.",
            "ambush": "Крысы бросаются из щелей.",
            "lair": "Крысы держат гнездо.",
            "random_meeting": "Крысы выходят на дорогу.",
        },
        name_ru=clan_id,
        localized={},
        description="",
        metadata_={},
        context={},
        source_context={},
        lifecycle_status="active",
        archived_at="",
        expires_at="",
        schema_version=1,
        created_at="",
        updated_at="",
        visual=AdminMonsterVisual(image_url="/static/generated-assets/clan.webp", storage_backend=storage),
        selected_traits=[
            {
                "key": "scarred_hide",
                "label": "Scarred Hide",
                "flavor": "Clan hides carry old wounds.",
                "modifiers": [
                    {
                        "target": "physical_resistance",
                        "base": 0.03,
                        "per_tier": 0.01,
                    }
                ],
            }
        ],
        members=[
            AdminGeneratedMonsterMember(
                monster_id=f"{clan_id}-{role}",
                variant_key=role,
                role=role,
                member_tier=1,
                name_ru=role,
                localized={},
                description=f"{role} description",
                text_content={"appearance_ru": f"{role} appearance"},
                scaled_attributes={"strength": 10},
                scaled_skills={"skill_swords": 0.2},
                items={
                    "layout": {"equipment": {"main_hand": "hatchet"}},
                    "by_id": {
                        "hatchet": {
                            "name_ru": "Ржавый топор",
                            "base_id": "hatchet",
                            "item_type": "weapon",
                            "combat": {
                                "power": 2.4,
                                "related_skill": "skill_swords",
                                "tags": ["axe", "rusty"],
                                "bonuses": {"physical_damage_bonus": "+0.0300"},
                            },
                            "generation": {
                                "affixes": [
                                    {
                                        "name_ru": "Кровоточащий край",
                                        "bonuses": {"bleed_damage_bonus": 0.06},
                                    }
                                ]
                            },
                        }
                    },
                },
                vitals={"hp": {"max": 50}},
                ai_profile={"profile": "aggressive"},
                generation_meta={"balance": {"gear_score": 1}},
                combat_actor_snapshot={"meta": {}},
                metadata_={},
                context={},
                source_context={},
                lifecycle_status="active",
                archived_at="",
                expires_at="",
                schema_version=1,
                created_at="",
                updated_at="",
                threat_rating=1,
                gear_score=1,
                visual=AdminMonsterVisual(
                    image_url="" if missing_member and index == 0 else "/static/generated-assets/member.webp",
                    storage_backend=storage,
                ),
            )
            for index, role in enumerate(roles)
        ],
    )

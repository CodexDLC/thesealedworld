from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.frontend.features.cabinet.modules.content_ops.cabinet as content_ops
from fastapi_cabinet import include_cabinet
from src.frontend.cabinet import CABINET_MODULES
from src.frontend.features.cabinet.modules.content_ops.cabinet import (
    ContentOpsAdmin,
    _filter_monster_clans,
    _find_member,
    _load_monster_browser_context,
    _monster_browser_redirect_url,
)
from src.frontend.integrations.backend_api.admin_monsters import (
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
    assert "regenerate-clan-family-images" in ContentOpsAdmin.action_routes
    assert "regenerate-visible-clan-images" in ContentOpsAdmin.action_routes


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
    assert "Перегенерировать видимые" in monsters.text

    maintenance = client.get("/admin/content-ops/monster-maintenance")
    assert maintenance.status_code == 200
    assert "Обслуживание монстров" in maintenance.text
    assert "Проверить расхождения" in maintenance.text
    assert "Пересобрать" in maintenance.text


def test_content_ops_rebuild_plan_renders_result_items(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAdminMonstersApi:
        async def list_generated(self, *, limit: int, **kwargs):
            assert limit == 100
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
    assert member.items == {"layout": {"equipment": {"main_hand": "hatchet"}}}
    assert member.scaled_attributes == {"strength": 10}


@pytest.mark.asyncio
async def test_monster_browser_uses_backend_contract_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAdminMonstersApi:
        async def list_generated(self, *, limit: int, **kwargs):
            assert limit == 100
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
        raw_tags={"tag": "value"},
        flavor_content={"visual": {}},
        name_ru=clan_id,
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
        members=[
            AdminGeneratedMonsterMember(
                monster_id=f"{clan_id}-{role}",
                variant_key=role,
                role=role,
                member_tier=1,
                name_ru=role,
                description=f"{role} description",
                text_content={"appearance_ru": f"{role} appearance"},
                scaled_attributes={"strength": 10},
                scaled_skills={"skill_swords": 0.2},
                items={"layout": {"equipment": {"main_hand": "hatchet"}}},
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

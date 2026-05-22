from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_cabinet import include_cabinet
from fastapi_cabinet.contracts.widgets import ListWidgetMap
from src.frontend.cabinet import CABINET_MODULES
from src.frontend.features.cabinet.modules.content_ops import cabinet as content_ops
from src.frontend.features.cabinet.modules.content_ops.cabinet import (
    ContentOpsAdmin,
    _asset_status_rows,
    _assets_provider,
    _filter_monster_clans,
)
from src.frontend.integrations.backend_api.admin_monsters import (
    AdminGeneratedMonsterClan,
    AdminGeneratedMonsterMember,
    AdminMonsterVisual,
)


def test_content_ops_admin_declares_operational_sections() -> None:
    assert ContentOpsAdmin.key == "content_ops"
    assert ContentOpsAdmin.path == "/admin/content-ops"
    assert [item.key for item in ContentOpsAdmin.sidebar] == ["overview", "monsters", "news_covers", "assets"]
    assert [item.path for item in ContentOpsAdmin.sidebar] == [
        "/admin/content-ops",
        "/admin/content-ops/monster-browser",
        "/admin/content-ops/news-covers",
        "/admin/content-ops/generated-assets",
    ]
    assert "monster-browser" in ContentOpsAdmin.action_routes
    assert "generated-assets" in ContentOpsAdmin.action_routes
    assert "news-covers" in ContentOpsAdmin.action_routes
    assert "monster-detail" in ContentOpsAdmin.action_routes


async def test_content_ops_assets_provider_documents_storage_contract() -> None:
    widget = await _assets_provider(None)  # type: ignore[arg-type]

    assert isinstance(widget, ListWidgetMap)
    assert any("ASSET_STORAGE_BACKEND" in item for item in widget.items)
    assert any("storage_key" in item for item in widget.items)


def test_content_ops_asset_rows_show_s3_operational_status(monkeypatch) -> None:
    monkeypatch.setattr(content_ops.settings, "asset_storage_backend", "s3")
    monkeypatch.setattr(content_ops.settings, "asset_public_base_url", "/static/generated-assets")
    monkeypatch.setattr(content_ops.settings, "asset_s3_bucket", "thesealedworld-generated-assets")
    monkeypatch.setattr(content_ops.settings, "asset_s3_region", "nbg1")
    monkeypatch.setattr(content_ops.settings, "asset_s3_endpoint_url", "https://nbg1.your-objectstorage.com")
    monkeypatch.setattr(content_ops.settings, "asset_s3_access_key_id", "configured")
    monkeypatch.setattr(content_ops.settings, "asset_s3_secret_access_key", "configured")  # pragma: allowlist secret

    rows = _asset_status_rows()

    assert {"label": "Storage backend", "value": "s3", "status": "active"} in rows
    assert any(row["label"] == "S3 credentials" and row["status"] == "ready" for row in rows)
    assert any(
        row["label"] == "Public URL" and "/static/generated-assets/<storage_key>" in row["value"] for row in rows
    )


def test_content_ops_filters_monsters_by_domain_safe_fields() -> None:
    rat = _clan("rat-clan", family="rats", storage="s3", roles=("scout", "brute"), missing_member=False)
    spider = _clan("spider-clan", family="spiders", storage="local", roles=("caster",), missing_member=True)

    filtered = _filter_monster_clans(
        [rat, spider],
        {"family_id": "spiders", "role": "", "storage_backend": "", "missing_image": ""},
    )
    assert [clan.clan_id for clan in filtered] == ["spider-clan"]

    filtered = _filter_monster_clans(
        [rat, spider],
        {"family_id": "", "role": "scout", "storage_backend": "s3", "missing_image": ""},
    )
    assert [clan.clan_id for clan in filtered] == ["rat-clan"]

    filtered = _filter_monster_clans(
        [rat, spider],
        {"family_id": "", "role": "", "storage_backend": "", "missing_image": "1"},
    )
    assert [clan.clan_id for clan in filtered] == ["spider-clan"]


def test_content_ops_custom_pages_render_operational_surfaces() -> None:
    app = FastAPI()
    include_cabinet(app, modules=CABINET_MODULES, mount_path="/admin")
    client = TestClient(app)

    assets = client.get("/admin/content-ops/generated-assets")
    assert assets.status_code == 200
    assert "Storage contract" in assets.text
    assert "Backfill dry-run" in assets.text

    news_covers = client.get("/admin/content-ops/news-covers")
    assert news_covers.status_code == 200
    assert "News cover workflow" in news_covers.text
    assert "News Management" in news_covers.text

    monsters = client.get("/admin/content-ops/monster-browser")
    assert monsters.status_code == 200
    assert "Generated monsters" in monsters.text
    assert "Missing image" in monsters.text


def _clan(
    clan_id: str,
    *,
    family: str,
    storage: str,
    roles: tuple[str, ...],
    missing_member: bool,
) -> AdminGeneratedMonsterClan:
    return AdminGeneratedMonsterClan(
        clan_id=clan_id,
        family_id=family,
        tier=1,
        zone_id="zone",
        name_ru=clan_id,
        description="",
        visual=AdminMonsterVisual(image_url="/static/generated-assets/clan.webp", storage_backend=storage),
        members=[
            AdminGeneratedMonsterMember(
                monster_id=f"{clan_id}-{role}",
                variant_key=role,
                role=role,
                member_tier=1,
                name_ru=role,
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

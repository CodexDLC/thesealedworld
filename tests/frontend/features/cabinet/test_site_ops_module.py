from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_cabinet import include_cabinet
from src.frontend.cabinet import CABINET_MODULES
from src.frontend.features.cabinet.modules.site_ops import cabinet as site_ops
from src.frontend.features.cabinet.modules.site_ops.cabinet import SiteOpsAdmin, _asset_status_rows


def test_site_ops_admin_lives_under_site_group() -> None:
    assert SiteOpsAdmin.key == "site_ops"
    assert SiteOpsAdmin.label == "OPS"
    assert SiteOpsAdmin.group == "site"
    assert SiteOpsAdmin.path == "/admin/site-ops"
    assert [item.key for item in SiteOpsAdmin.sidebar] == ["storage"]


def test_site_ops_asset_rows_show_s3_operational_status(monkeypatch) -> None:
    monkeypatch.setattr(site_ops.settings, "asset_storage_backend", "s3")
    monkeypatch.setattr(site_ops.settings, "asset_public_base_url", "/static/generated-assets")
    monkeypatch.setattr(site_ops.settings, "asset_s3_bucket", "thesealedworld-generated-assets")
    monkeypatch.setattr(site_ops.settings, "asset_s3_region", "nbg1")
    monkeypatch.setattr(site_ops.settings, "asset_s3_endpoint_url", "https://nbg1.your-objectstorage.com")
    monkeypatch.setattr(site_ops.settings, "asset_s3_access_key_id", "configured")
    monkeypatch.setattr(site_ops.settings, "asset_s3_secret_access_key", "configured")  # pragma: allowlist secret

    rows = _asset_status_rows()

    assert {"label": "Storage backend", "value": "s3", "status": "active"} in rows
    assert any(row["label"] == "S3 credentials" and row["status"] == "ready" for row in rows)
    assert any(
        row["label"] == "Public URL" and "/static/generated-assets/<storage_key>" in row["value"] for row in rows
    )


def test_site_ops_storage_page_renders_s3_monitoring() -> None:
    app = FastAPI()
    include_cabinet(app, modules=CABINET_MODULES, mount_path="/admin")

    response = TestClient(app).get("/admin/site-ops/storage")

    assert response.status_code == 200
    assert "S3 storage OPS" in response.text
    assert "Storage state" in response.text
    assert "Backfill dry-run" in response.text

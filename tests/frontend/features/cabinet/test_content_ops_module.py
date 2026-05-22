from __future__ import annotations

from fastapi_cabinet.contracts.widgets import ListWidgetMap
from src.frontend.features.cabinet.modules.content_ops.cabinet import ContentOpsAdmin, _assets_provider


def test_content_ops_admin_declares_operational_sections() -> None:
    assert ContentOpsAdmin.key == "content_ops"
    assert ContentOpsAdmin.path == "/admin/content-ops"
    assert [item.key for item in ContentOpsAdmin.sidebar] == ["overview", "monsters", "news_covers", "assets"]
    assert "monster-detail" in ContentOpsAdmin.action_routes


async def test_content_ops_assets_provider_documents_storage_contract() -> None:
    widget = await _assets_provider(None)  # type: ignore[arg-type]

    assert isinstance(widget, ListWidgetMap)
    assert any("ASSET_STORAGE_BACKEND" in item for item in widget.items)
    assert any("storage_key" in item for item in widget.items)

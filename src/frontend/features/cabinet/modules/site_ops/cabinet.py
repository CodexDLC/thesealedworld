from __future__ import annotations

from typing import Any, ClassVar

from fastapi import Request
from starlette.responses import Response

from fastapi_cabinet import CabinetAdmin, MetricWidget, SidebarItem, TableWidget, cabinet_site
from fastapi_cabinet.contracts.widgets import MetricWidgetMap, TableColumnMap, TableWidgetMap
from fastapi_cabinet.rendering.layout_mapper import build_layout_map
from fastapi_cabinet.runtime import resolve_active_admin
from src.frontend.config.settings import settings

_MOUNT_PATH = "/admin"
_BASE = "/admin/site-ops"


async def _storage_backend_provider(request: Request) -> MetricWidgetMap:
    s3_ready = _s3_configured()
    subtitle = "S3 configured" if s3_ready else "S3 config incomplete"
    if settings.asset_storage_backend == "local":
        subtitle = "local generated assets"
    return MetricWidgetMap(
        key="site_ops_storage_backend",
        title="Generated Asset Storage",
        value=settings.asset_storage_backend,
        subtitle=subtitle,
    )


async def _storage_status_provider(request: Request) -> TableWidgetMap:
    return TableWidgetMap(
        key="site_ops_storage_status",
        title="S3 / generated assets state",
        columns=[
            TableColumnMap(key="label", label="Check"),
            TableColumnMap(key="value", label="Value"),
            TableColumnMap(key="status", label="Status"),
        ],
        rows=_asset_status_rows(),
    )


class SiteOpsAdmin(CabinetAdmin):
    key = "site_ops"
    label = "OPS"
    group = "site"
    group_label = "Сайт"
    path = _BASE
    order = 30
    sidebar: ClassVar = (SidebarItem(key="storage", label="S3 storage", path=_BASE, order=10),)
    dashboard_widgets: ClassVar = (
        MetricWidget(
            key="site_ops_storage_backend",
            title="Generated Asset Storage",
            provider="site_ops.storage_backend",
            order=10,
        ),
        TableWidget(
            key="site_ops_storage_status",
            title="S3 / generated assets state",
            provider="site_ops.storage_status",
            order=20,
        ),
    )
    sub_pages: ClassVar = {}
    action_routes: ClassVar = {
        "storage": ("GET", "handle_storage"),
    }
    providers: ClassVar = {
        "site_ops.storage_backend": _storage_backend_provider,
        "site_ops.storage_status": _storage_status_provider,
    }

    async def handle_storage(self, request: Request) -> Response:
        return _render_custom(
            self,
            request,
            "cabinet/site_ops_storage.html",
            {
                "asset_rows": _asset_status_rows(),
                "operator_commands": _operator_commands(),
                "public_base_url": settings.asset_public_base_url,
            },
        )


def _asset_status_rows() -> list[dict[str, str]]:
    s3_configured = _s3_configured()
    return [
        {
            "label": "Storage backend",
            "value": settings.asset_storage_backend,
            "status": "active" if settings.asset_storage_backend == "s3" else "local",
        },
        {
            "label": "Public URL",
            "value": f"{settings.asset_public_base_url}/<storage_key>",
            "status": "canonical",
        },
        {
            "label": "S3 bucket",
            "value": settings.asset_s3_bucket or "not configured",
            "status": "ready" if settings.asset_s3_bucket else "missing",
        },
        {
            "label": "S3 endpoint",
            "value": settings.asset_s3_endpoint_url or "not configured",
            "status": "ready" if settings.asset_s3_endpoint_url else "missing",
        },
        {
            "label": "S3 credentials",
            "value": "configured" if s3_configured else "missing",
            "status": "ready" if s3_configured else "missing",
        },
        {
            "label": "Local fallback root",
            "value": settings.asset_local_root,
            "status": "fallback",
        },
    ]


def _operator_commands() -> list[dict[str, str]]:
    return [
        {
            "label": "Backfill dry-run",
            "command": "uv run python scripts/backfill_generated_assets_to_s3.py --local-root var/generated-assets --dry-run",
        },
        {
            "label": "Backfill upload",
            "command": "uv run python scripts/backfill_generated_assets_to_s3.py --local-root var/generated-assets --skip-existing",
        },
    ]


def _s3_configured() -> bool:
    return all(
        [
            settings.asset_s3_bucket,
            settings.asset_s3_region,
            settings.asset_s3_endpoint_url,
            settings.asset_s3_access_key_id,
            settings.asset_s3_secret_access_key,
        ]
    )


def _render_custom(admin: Any, request: Request, template: str, context: dict[str, Any]) -> Response:
    active_path = str(request.url.path)
    active_admin = resolve_active_admin(active_path, cabinet_site.registry, _MOUNT_PATH)
    layout = build_layout_map(
        cabinet_site.registry,
        mount_path=_MOUNT_PATH,
        active_admin=active_admin,
        active_path=active_path,
        title=admin.label,
    )
    return cabinet_site.templates.TemplateResponse(
        request,
        template,
        {"layout": layout, "module": admin, "module_context": {}, "widgets": [], **context},
    )


cabinet_site.register(SiteOpsAdmin)

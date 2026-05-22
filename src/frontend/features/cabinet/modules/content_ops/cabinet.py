from __future__ import annotations

from typing import Any, ClassVar

import httpx
from fastapi import Request
from starlette.responses import RedirectResponse, Response

from fastapi_cabinet import CabinetAdmin, ListWidget, MetricWidget, SidebarItem, TableWidget, cabinet_site
from fastapi_cabinet.contracts.widgets import ListWidgetMap, MetricWidgetMap, TableColumnMap, TableWidgetMap
from fastapi_cabinet.rendering.layout_mapper import build_layout_map
from fastapi_cabinet.runtime import resolve_active_admin
from src.frontend.config.settings import settings
from src.frontend.integrations.backend_api.admin_monsters import AdminGeneratedMonsterClan, AdminMonstersApi

_MOUNT_PATH = "/admin"
_BASE = "/admin/content-ops"


def _api(request: Request) -> AdminMonstersApi:
    client: httpx.AsyncClient = request.app.state.backend_http_client
    return AdminMonstersApi(client=client, base_url=settings.backend_base_url)


async def _overview_provider(request: Request) -> ListWidgetMap:
    return ListWidgetMap(
        key="content_ops_overview",
        title="Операционные зоны",
        items=[
            "Monsters: просмотр сгенерированных кланов, участников и image metadata.",
            "News covers: генерация обложек остаётся в модуле новостей с approve/reject.",
            "Generated assets: S3/backfill инструменты готовы как backend/operator contracts.",
            "Future: items, locations, users and moderation queues.",
        ],
    )


async def _monster_count_provider(request: Request) -> MetricWidgetMap:
    try:
        clans = await _api(request).list_generated(limit=100)
    except (httpx.HTTPStatusError, httpx.RequestError):
        return MetricWidgetMap(
            key="content_ops_monsters",
            title="Generated Monsters",
            value="—",
            subtitle="backend unavailable",
        )
    member_count = sum(len(clan.members) for clan in clans)
    missing = sum(1 for clan in clans if _has_missing_image(clan))
    return MetricWidgetMap(
        key="content_ops_monsters",
        title="Generated Monsters",
        value=str(len(clans)),
        subtitle=f"members {member_count} / missing image {missing}",
    )


async def _monster_table_provider(request: Request) -> TableWidgetMap:
    params = request.query_params
    try:
        clans = await _api(request).list_generated(
            family_id=params.get("family_id") or None,
            role=params.get("role") or None,
            missing_image=params.get("missing_image") == "1",
            limit=100,
        )
    except (httpx.HTTPStatusError, httpx.RequestError):
        clans = []
    return TableWidgetMap(
        key="content_ops_monster_families",
        title="Generated monster families",
        columns=[
            TableColumnMap(key="name", label="Clan"),
            TableColumnMap(key="family", label="Family"),
            TableColumnMap(key="tier", label="Tier"),
            TableColumnMap(key="members", label="Members"),
            TableColumnMap(key="storage", label="Storage"),
            TableColumnMap(key="image", label="Image"),
        ],
        rows=[
            {
                "name": clan.name_ru or clan.clan_id,
                "family": clan.family_id,
                "tier": clan.tier,
                "members": len(clan.members),
                "storage": clan.visual.storage_backend or "—",
                "image": "missing" if _has_missing_image(clan) else "ok",
                "href": f"{_BASE}/monster-detail?id={clan.clan_id}",
            }
            for clan in clans
        ],
        row_href_key="href",
    )


async def _assets_provider(request: Request) -> ListWidgetMap:
    return ListWidgetMap(
        key="content_ops_assets",
        title="Generated assets",
        items=[
            "S3 storage backend is controlled by ASSET_STORAGE_BACKEND.",
            "Backfill is an operator script with dry-run and skip-existing modes.",
            "Canonical data remains storage_key plus /static/generated-assets public URL.",
        ],
    )


class ContentOpsAdmin(CabinetAdmin):
    key = "content_ops"
    label = "Content Ops"
    group = "content_ops"
    group_label = "Content Ops"
    path = "/admin/content-ops"
    order = 10
    sidebar: ClassVar = (
        SidebarItem(key="overview", label="Overview", path="/admin/content-ops", order=10),
        SidebarItem(key="monsters", label="Monsters", path="/admin/content-ops/monsters", order=20),
        SidebarItem(key="news_covers", label="News covers", path="/admin/news", order=30),
        SidebarItem(key="assets", label="Generated assets", path="/admin/content-ops/assets", order=40),
    )
    dashboard_widgets: ClassVar = (
        MetricWidget(key="content_ops_monsters", title="Generated Monsters", provider="content_ops.monster_count"),
        ListWidget(key="content_ops_overview", title="Операционные зоны", provider="content_ops.overview", order=20),
    )
    sub_pages: ClassVar = {
        "monsters": (
            TableWidget(
                key="content_ops_monster_families",
                title="Generated monster families",
                provider="content_ops.monster_table",
                order=10,
            ),
        ),
        "assets": (
            ListWidget(
                key="content_ops_assets",
                title="Generated assets",
                provider="content_ops.assets",
                order=10,
            ),
        ),
    }
    action_routes: ClassVar = {
        "monster-detail": ("GET", "handle_monster_detail"),
        "regenerate-clan-image": ("POST", "handle_regenerate_clan_image"),
        "regenerate-member-image": ("POST", "handle_regenerate_member_image"),
    }
    providers: ClassVar = {
        "content_ops.overview": _overview_provider,
        "content_ops.monster_count": _monster_count_provider,
        "content_ops.monster_table": _monster_table_provider,
        "content_ops.assets": _assets_provider,
    }

    async def handle_monster_detail(self, request: Request) -> Response:
        clan_id = request.query_params.get("id", "")
        clan = await _api(request).get_generated_clan(clan_id) if clan_id else None
        return _render_custom(self, request, "cabinet/content_ops_monster_detail.html", {"clan": clan})

    async def handle_regenerate_clan_image(self, request: Request) -> Response:
        form = await request.form()
        clan_id = str(form.get("clan_id") or "")
        if clan_id:
            await _api(request).regenerate_clan_image(clan_id)
        return RedirectResponse(url=f"{_BASE}/monster-detail?id={clan_id}", status_code=303)

    async def handle_regenerate_member_image(self, request: Request) -> Response:
        form = await request.form()
        clan_id = str(form.get("clan_id") or "")
        member_id = str(form.get("member_id") or "")
        if member_id:
            await _api(request).regenerate_member_image(member_id)
        return RedirectResponse(url=f"{_BASE}/monster-detail?id={clan_id}", status_code=303)


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


def _has_missing_image(clan: AdminGeneratedMonsterClan) -> bool:
    return not clan.visual.image_url or any(not member.visual.image_url for member in clan.members)


cabinet_site.register(ContentOpsAdmin)

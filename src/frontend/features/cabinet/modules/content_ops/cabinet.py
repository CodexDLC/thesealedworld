from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

import httpx
from fastapi import Request
from starlette.responses import RedirectResponse, Response

from fastapi_cabinet import CabinetAdmin, ListWidget, MetricWidget, SidebarItem, cabinet_site
from fastapi_cabinet.contracts.widgets import ListWidgetMap, MetricWidgetMap, TableColumnMap, TableWidgetMap
from fastapi_cabinet.rendering.layout_mapper import build_layout_map
from fastapi_cabinet.runtime import resolve_active_admin
from src.frontend.config.settings import settings
from src.frontend.integrations.backend_api.admin_monsters import AdminGeneratedMonsterClan, AdminMonstersApi

_MOUNT_PATH = "/admin"
_BASE = "/admin/content-ops"


@dataclass(frozen=True)
class MonsterBrowserContext:
    clans: list[AdminGeneratedMonsterClan]
    family_options: list[str]
    role_options: list[str]
    storage_options: list[str]
    filters: dict[str, str]
    total_clans: int
    total_members: int
    missing_images: int
    error: str = ""


def _api(request: Request) -> AdminMonstersApi:
    client: httpx.AsyncClient = request.app.state.backend_http_client
    return AdminMonstersApi(client=client, base_url=settings.backend_base_url)


async def _overview_provider(request: Request) -> ListWidgetMap:
    return ListWidgetMap(
        key="content_ops_overview",
        title="Операционные зоны",
        items=[
            "Generated monsters: семьи, индивиды, визуалы, metadata и safe regeneration actions.",
            "Generated world: будущая секция для сгенерированных локаций, текстов и фоновых изображений.",
            "Item templates: будущая секция для статических шаблонов и AI-generated descriptions/images.",
            "Static resources: будущий read-only browser словарей, которые сейчас живут в кодовых resource-модулях.",
        ],
    )


async def _monster_count_provider(request: Request) -> MetricWidgetMap:
    try:
        clans = await _api(request).list_generated(limit=100)
    except (AttributeError, httpx.HTTPStatusError, httpx.RequestError):
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
    except (AttributeError, httpx.HTTPStatusError, httpx.RequestError):
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


async def _load_monster_browser_context(request: Request) -> MonsterBrowserContext:
    params = request.query_params
    filters = {
        "family_id": (params.get("family_id") or "").strip(),
        "role": (params.get("role") or "").strip(),
        "storage_backend": (params.get("storage_backend") or "").strip(),
        "missing_image": "1" if params.get("missing_image") == "1" else "",
    }
    try:
        source = await _api(request).list_generated(limit=200)
    except (AttributeError, httpx.HTTPStatusError, httpx.RequestError) as exc:
        return MonsterBrowserContext(
            clans=[],
            family_options=[],
            role_options=[],
            storage_options=[],
            filters=filters,
            total_clans=0,
            total_members=0,
            missing_images=0,
            error=f"backend unavailable: {exc.__class__.__name__}",
        )

    clans = _filter_monster_clans(source, filters)
    return MonsterBrowserContext(
        clans=clans,
        family_options=sorted({clan.family_id for clan in source if clan.family_id}),
        role_options=sorted({member.role for clan in source for member in clan.members if member.role}),
        storage_options=sorted(
            {
                backend
                for clan in source
                for backend in [
                    clan.visual.storage_backend,
                    *(member.visual.storage_backend for member in clan.members),
                ]
                if backend
            }
        ),
        filters=filters,
        total_clans=len(clans),
        total_members=sum(len(clan.members) for clan in clans),
        missing_images=sum(1 for clan in clans if _has_missing_image(clan)),
    )


def _filter_monster_clans(
    clans: list[AdminGeneratedMonsterClan],
    filters: dict[str, str],
) -> list[AdminGeneratedMonsterClan]:
    result = clans
    if filters.get("family_id"):
        result = [clan for clan in result if clan.family_id == filters["family_id"]]
    if filters.get("role"):
        result = [clan for clan in result if any(member.role == filters["role"] for member in clan.members)]
    if filters.get("storage_backend"):
        result = [clan for clan in result if _clan_uses_storage_backend(clan, filters["storage_backend"])]
    if filters.get("missing_image"):
        result = [clan for clan in result if _has_missing_image(clan)]
    return result


class ContentOpsAdmin(CabinetAdmin):
    key = "content_ops"
    label = "Content"
    group = "content_ops"
    group_label = "Content"
    path = "/admin/content-ops"
    order = 10
    sidebar: ClassVar = (
        SidebarItem(key="overview", label="Overview", path="/admin/content-ops", order=10),
        SidebarItem(key="monsters", label="Generated monsters", path="/admin/content-ops/monster-browser", order=20),
    )
    dashboard_widgets: ClassVar = (
        MetricWidget(key="content_ops_monsters", title="Generated Monsters", provider="content_ops.monster_count"),
        ListWidget(key="content_ops_overview", title="Операционные зоны", provider="content_ops.overview", order=20),
    )
    sub_pages: ClassVar = {}
    action_routes: ClassVar = {
        "monster-browser": ("GET", "handle_monster_browser"),
        "monster-detail": ("GET", "handle_monster_detail"),
        "regenerate-clan-image": ("POST", "handle_regenerate_clan_image"),
        "regenerate-member-image": ("POST", "handle_regenerate_member_image"),
    }
    providers: ClassVar = {
        "content_ops.overview": _overview_provider,
        "content_ops.monster_count": _monster_count_provider,
        "content_ops.monster_table": _monster_table_provider,
    }

    async def get_dashboard_context(self, request: Request) -> dict[str, Any]:
        browser = await _load_monster_browser_context(request)
        return {
            "sections": [
                {
                    "label": "Monsters",
                    "href": f"{_BASE}/monster-browser",
                    "status": "ready" if not browser.error else "unavailable",
                    "detail": f"{browser.total_clans} clans / {browser.total_members} members",
                },
                {
                    "label": "Static resources",
                    "href": _BASE,
                    "status": "planned",
                    "detail": "read-only dictionaries/resources browser",
                },
            ]
        }

    async def handle_monster_browser(self, request: Request) -> Response:
        browser = await _load_monster_browser_context(request)
        return _render_custom(
            self,
            request,
            "cabinet/content_ops_monsters.html",
            {"browser": browser, "base_url": _BASE},
        )

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


def _clan_uses_storage_backend(clan: AdminGeneratedMonsterClan, storage_backend: str) -> bool:
    if clan.visual.storage_backend == storage_backend:
        return True
    return any(member.visual.storage_backend == storage_backend for member in clan.members)


cabinet_site.register(ContentOpsAdmin)

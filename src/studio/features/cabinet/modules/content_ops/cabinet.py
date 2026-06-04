from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar
from urllib.parse import parse_qsl, urlencode

import httpx
from fastapi import Request
from starlette.responses import RedirectResponse, Response

from fastapi_cabinet import CabinetAdmin, ListWidget, MetricWidget, SidebarItem, cabinet_site
from fastapi_cabinet.contracts.widgets import ListWidgetMap, MetricWidgetMap, TableColumnMap, TableWidgetMap
from fastapi_cabinet.rendering.layout_mapper import build_layout_map
from fastapi_cabinet.runtime import resolve_active_admin
from src.studio.integrations.backend_api.admin_monsters import (
    AdminAIGenerationTask,
    AdminGeneratedMonsterClan,
    AdminGeneratedMonsterMember,
    AdminMonstersApi,
)

_MOUNT_PATH = "/admin"
_BASE = "/admin/content-ops"
_GENERATED_MONSTER_PAGE_LIMIT = 100


@dataclass(frozen=True)
class MonsterBrowserContext:
    clans: list[AdminGeneratedMonsterClan]
    family_options: list[str]
    tier_options: list[int]
    storage_options: list[str]
    filters: dict[str, str]
    total_clans: int
    total_members: int
    missing_images: int
    error: str = ""


@dataclass(frozen=True)
class AITaskNotice:
    kind: str
    title: str
    message: str
    task_ids: list[str]
    tasks: list[AdminAIGenerationTask]
    requested: int = 0
    error: str = ""

    @property
    def active(self) -> bool:
        return any(task.status in {"pending", "running", "cooldown"} for task in self.tasks)

    @property
    def failed(self) -> bool:
        return bool(self.error) or any(task.status == "failed" for task in self.tasks)

    @property
    def done(self) -> bool:
        return bool(self.tasks) and all(task.status == "done" for task in self.tasks)

    @property
    def css_class(self) -> str:
        if self.failed:
            return "fc-task-notice--error"
        if self.done:
            return "fc-task-notice--done"
        return "fc-task-notice--active"


def _api(request: Request) -> AdminMonstersApi:
    client: httpx.AsyncClient = request.app.state.backend_http_client
    return AdminMonstersApi(client=client, base_url=request.state.source.api_base)


async def _overview_provider(request: Request) -> ListWidgetMap:
    return ListWidgetMap(
        key="content_ops_overview",
        title="Операционные зоны",
        items=[
            "Сгенерированные монстры: семьи, индивиды, визуалы, метаданные и безопасная перегенерация.",
            "Сгенерированный мир: будущая секция для локаций, текстов и фоновых изображений.",
            "Шаблоны предметов: будущая секция для статических шаблонов и AI-сгенерированных описаний/изображений.",
            "Статические ресурсы: будущий просмотр словарей и ресурсных модулей в режиме только чтения.",
        ],
    )


async def _monster_count_provider(request: Request) -> MetricWidgetMap:
    try:
        clans = await _api(request).list_generated(limit=100)
    except (AttributeError, httpx.HTTPStatusError, httpx.RequestError):
        return MetricWidgetMap(
            key="content_ops_monsters",
            title="Сгенерированные монстры",
            value="—",
            subtitle="backend недоступен",
        )
    member_count = sum(len(clan.members) for clan in clans)
    missing = sum(1 for clan in clans if _has_missing_image(clan))
    return MetricWidgetMap(
        key="content_ops_monsters",
        title="Сгенерированные монстры",
        value=str(len(clans)),
        subtitle=f"участников {member_count} / без изображения {missing}",
    )


async def _monster_table_provider(request: Request) -> TableWidgetMap:
    params = request.query_params
    try:
        clans = await _api(request).list_generated(
            family_id=params.get("family_id") or None,
            missing_image=params.get("missing_image") == "1",
            limit=100,
        )
        clans = _filter_monster_clans(
            clans,
            {
                "family_id": "",
                "tier": (params.get("tier") or "").strip(),
                "storage_backend": (params.get("storage_backend") or "").strip(),
                "missing_image": "",
            },
        )
    except (AttributeError, httpx.HTTPStatusError, httpx.RequestError):
        clans = []
    return TableWidgetMap(
        key="content_ops_monster_families",
        title="Семьи сгенерированных монстров",
        columns=[
            TableColumnMap(key="name", label="Семья"),
            TableColumnMap(key="family", label="Тип"),
            TableColumnMap(key="tier", label="Тир семьи"),
            TableColumnMap(key="members", label="Участники"),
            TableColumnMap(key="storage", label="Хранилище"),
            TableColumnMap(key="image", label="Изображение"),
        ],
        rows=[
            {
                "name": clan.name_ru or clan.clan_id,
                "family": clan.family_id,
                "tier": clan.tier,
                "members": len(clan.members),
                "storage": clan.visual.storage_backend or "—",
                "image": "нет" if _has_missing_image(clan) else "есть",
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
        "tier": (params.get("tier") or "").strip(),
        "storage_backend": (params.get("storage_backend") or "").strip(),
        "missing_image": "1" if params.get("missing_image") == "1" else "",
    }
    try:
        source = await _api(request).list_generated(limit=_GENERATED_MONSTER_PAGE_LIMIT)
    except (AttributeError, httpx.HTTPStatusError, httpx.RequestError) as exc:
        return MonsterBrowserContext(
            clans=[],
            family_options=[],
            tier_options=[],
            storage_options=[],
            filters=filters,
            total_clans=0,
            total_members=0,
            missing_images=0,
            error=f"backend недоступен: {exc.__class__.__name__}",
        )

    clans = _filter_monster_clans(source, filters)
    return MonsterBrowserContext(
        clans=clans,
        family_options=sorted({clan.family_id for clan in source if clan.family_id}),
        tier_options=sorted({clan.tier for clan in source}),
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
    if filters.get("tier"):
        result = [clan for clan in result if str(clan.tier) == filters["tier"]]
    if filters.get("storage_backend"):
        result = [clan for clan in result if _clan_uses_storage_backend(clan, filters["storage_backend"])]
    if filters.get("missing_image"):
        result = [clan for clan in result if _has_missing_image(clan)]
    return result


class ContentOpsAdmin(CabinetAdmin):
    key = "content_ops"
    label = "Монстры"
    group = "content_ops"
    group_label = "Контент"
    path = "/admin/content-ops"
    order = 10
    sidebar: ClassVar = (
        SidebarItem(key="overview", label="Обзор", path="/admin/content-ops", order=10),
        SidebarItem(
            key="monsters",
            label="Сгенерированные монстры",
            path="/admin/content-ops/monster-browser",
            order=20,
        ),
        SidebarItem(
            key="monster_maintenance",
            label="Обслуживание монстров",
            path="/admin/content-ops/monster-maintenance",
            order=30,
        ),
    )
    dashboard_widgets: ClassVar = (
        MetricWidget(
            key="content_ops_monsters",
            title="Сгенерированные монстры",
            provider="content_ops.monster_count",
        ),
        ListWidget(key="content_ops_overview", title="Операционные зоны", provider="content_ops.overview", order=20),
    )
    sub_pages: ClassVar[dict[str, Any]] = {}
    action_routes: ClassVar = {
        "monster-browser": ("GET", "handle_monster_browser"),
        "monster-detail": ("GET", "handle_monster_detail"),
        "monster-member-detail": ("GET", "handle_monster_member_detail"),
        "monster-maintenance": ("GET", "handle_monster_maintenance"),
        "monster-rebuild-plan": ("POST", "handle_monster_rebuild_plan"),
        "monster-rebuild-apply": ("POST", "handle_monster_rebuild_apply"),
        "regenerate-clan-flavor": ("POST", "handle_regenerate_clan_flavor"),
        "regenerate-clan-member-images": ("POST", "handle_regenerate_clan_member_images"),
        "regenerate-visible-member-images": ("POST", "handle_regenerate_visible_member_images"),
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
                    "label": "Монстры",
                    "href": f"{_BASE}/monster-browser",
                    "status": "готово" if not browser.error else "недоступно",
                    "detail": f"{browser.total_clans} семей / {browser.total_members} участников",
                },
                {
                    "label": "Статические ресурсы",
                    "href": _BASE,
                    "status": "планируется",
                    "detail": "просмотр словарей и ресурсных модулей в режиме только чтения",
                },
            ]
        }

    async def handle_monster_browser(self, request: Request) -> Response:
        browser = await _load_monster_browser_context(request)
        task_notice = await _task_notice_from_query(request)
        return _render_custom(
            self,
            request,
            "cabinet/content_ops_monsters.html",
            {"browser": browser, "base_url": _BASE, "task_notice": task_notice},
        )

    async def handle_monster_detail(self, request: Request) -> Response:
        clan_id = request.query_params.get("id", "")
        clan = await _api(request).get_generated_clan(clan_id) if clan_id else None
        task_notice = await _task_notice_from_query(request)
        return _render_custom(
            self,
            request,
            "cabinet/content_ops_monster_detail.html",
            {"clan": clan, "task_notice": task_notice},
        )

    async def handle_monster_member_detail(self, request: Request) -> Response:
        clan_id = request.query_params.get("clan_id", "")
        member_id = request.query_params.get("member_id", "")
        clan = await _api(request).get_generated_clan(clan_id) if clan_id else None
        member = _find_member(clan, member_id) if clan and member_id else None
        task_notice = await _task_notice_from_query(request)
        return _render_custom(
            self,
            request,
            "cabinet/content_ops_monster_member_detail.html",
            {"clan": clan, "member": member, "task_notice": task_notice},
        )

    async def handle_monster_maintenance(self, request: Request) -> Response:
        return await _render_monster_maintenance(self, request)

    async def handle_monster_rebuild_plan(self, request: Request) -> Response:
        form = await request.form()
        result = await _api(request).plan_generated_rebuild(**_rebuild_options_from_form(form))
        return await _render_monster_maintenance(self, request, result=result, form=form)

    async def handle_monster_rebuild_apply(self, request: Request) -> Response:
        form = await request.form()
        result = await _api(request).apply_generated_rebuild(**_rebuild_options_from_form(form))
        return await _render_monster_maintenance(self, request, result=result, form=form)

    async def handle_regenerate_clan_flavor(self, request: Request) -> Response:
        form = await request.form()
        clan_id = str(form.get("clan_id") or "")
        result: dict[str, Any] = {}
        if clan_id:
            try:
                result = await _api(request).regenerate_clan_flavor(clan_id)
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                return RedirectResponse(
                    url=_task_redirect_url(
                        f"{_BASE}/monster-detail",
                        {"id": clan_id},
                        kind="clan_flavor",
                        error=f"{exc.__class__.__name__}: {exc}",
                    ),
                    status_code=303,
                )
        return RedirectResponse(
            url=_task_redirect_url(
                f"{_BASE}/monster-detail",
                {"id": clan_id},
                kind="clan_flavor",
                task_ids=_task_ids_from_result(result),
                requested=int(result.get("requested") or 1) if result else 0,
            ),
            status_code=303,
        )

    async def handle_regenerate_clan_member_images(self, request: Request) -> Response:
        form = await request.form()
        clan_id = str(form.get("clan_id") or "")
        result: dict[str, Any] = {}
        if clan_id:
            try:
                result = await _api(request).regenerate_clan_member_images(clan_id)
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                return RedirectResponse(
                    url=_task_redirect_url(
                        f"{_BASE}/monster-detail",
                        {"id": clan_id},
                        kind="member_images",
                        error=f"{exc.__class__.__name__}: {exc}",
                    ),
                    status_code=303,
                )
        return RedirectResponse(
            url=_task_redirect_url(
                f"{_BASE}/monster-detail",
                {"id": clan_id},
                kind="member_images",
                task_ids=_task_ids_from_result(result),
                requested=int(result.get("requested") or len(_task_ids_from_result(result))),
            ),
            status_code=303,
        )

    async def handle_regenerate_visible_member_images(self, request: Request) -> Response:
        form = await request.form()
        clan_ids = [str(value) for value in form.getlist("clan_ids") if str(value)]
        result: dict[str, Any] = {}
        redirect_base, redirect_params = _split_url_query(_monster_browser_redirect_url(form))
        if clan_ids:
            try:
                result = await _api(request).regenerate_clan_member_images_batch(clan_ids)
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                return RedirectResponse(
                    url=_task_redirect_url(
                        redirect_base,
                        redirect_params,
                        kind="member_images_batch",
                        error=f"{exc.__class__.__name__}: {exc}",
                    ),
                    status_code=303,
                )
        return RedirectResponse(
            url=_task_redirect_url(
                redirect_base,
                redirect_params,
                kind="member_images_batch",
                task_ids=_task_ids_from_result(result)[:30],
                requested=int(result.get("requested") or len(_task_ids_from_result(result))),
            ),
            status_code=303,
        )

    async def handle_regenerate_member_image(self, request: Request) -> Response:
        form = await request.form()
        clan_id = str(form.get("clan_id") or "")
        member_id = str(form.get("member_id") or "")
        result: dict[str, Any] = {}
        if member_id:
            try:
                result = await _api(request).regenerate_member_image(member_id)
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                return_to_member = form.get("return_member_detail") == "1"
                target = f"{_BASE}/monster-member-detail" if return_to_member else f"{_BASE}/monster-detail"
                params = {"clan_id": clan_id, "member_id": member_id} if return_to_member else {"id": clan_id}
                return RedirectResponse(
                    url=_task_redirect_url(
                        target,
                        params,
                        kind="member_image",
                        error=f"{exc.__class__.__name__}: {exc}",
                    ),
                    status_code=303,
                )
        if form.get("return_member_detail") == "1":
            return RedirectResponse(
                url=_task_redirect_url(
                    f"{_BASE}/monster-member-detail",
                    {"clan_id": clan_id, "member_id": member_id},
                    kind="member_image",
                    task_ids=_task_ids_from_result(result),
                    requested=int(result.get("requested") or 1) if result else 0,
                ),
                status_code=303,
            )
        return RedirectResponse(
            url=_task_redirect_url(
                f"{_BASE}/monster-detail",
                {"id": clan_id},
                kind="member_image",
                task_ids=_task_ids_from_result(result),
                requested=int(result.get("requested") or 1) if result else 0,
            ),
            status_code=303,
        )


def _render_custom(admin: Any, request: Request, template: str, context: dict[str, Any]) -> Response:
    active_path = str(request.url.path)
    active_admin = resolve_active_admin(active_path, cabinet_site.registry, _MOUNT_PATH)
    layout = build_layout_map(
        cabinet_site.registry,
        mount_path=_MOUNT_PATH,
        active_admin=active_admin,
        static_mount_path=cabinet_site.static_mount_path,
        active_path=active_path,
        title=admin.label,
    )
    return cabinet_site.templates.TemplateResponse(
        request,
        template,
        {"layout": layout, "module": admin, "module_context": {}, "widgets": [], **context},
    )


async def _render_monster_maintenance(
    admin: Any,
    request: Request,
    *,
    result: dict[str, Any] | None = None,
    form: Any | None = None,
) -> Response:
    try:
        clans = await _api(request).list_generated(limit=_GENERATED_MONSTER_PAGE_LIMIT)
        error = ""
    except (AttributeError, httpx.HTTPStatusError, httpx.RequestError) as exc:
        clans = []
        error = f"backend недоступен: {exc.__class__.__name__}"

    selected = {
        "family_id": str(form.get("family_id") or "") if form is not None else "",
        "clan_id": str(form.get("clan_id") or "") if form is not None else "",
        "limit": str(form.get("limit") or _GENERATED_MONSTER_PAGE_LIMIT)
        if form is not None
        else str(_GENERATED_MONSTER_PAGE_LIMIT),
        "force": form.get("force") == "1" if form is not None else False,
        "remove_obsolete_members": form.get("remove_obsolete_members") == "1" if form is not None else True,
    }
    return _render_custom(
        admin,
        request,
        "cabinet/content_ops_monster_maintenance.html",
        {
            "base_url": _BASE,
            "families": sorted({clan.family_id for clan in clans if clan.family_id}),
            "clans": clans,
            "selected": selected,
            "result": result or {},
            "error": error,
        },
    )


def _has_missing_image(clan: AdminGeneratedMonsterClan) -> bool:
    return not clan.visual.image_url or any(not member.visual.image_url for member in clan.members)


def _clan_uses_storage_backend(clan: AdminGeneratedMonsterClan, storage_backend: str) -> bool:
    if clan.visual.storage_backend == storage_backend:
        return True
    return any(member.visual.storage_backend == storage_backend for member in clan.members)


def _find_member(
    clan: AdminGeneratedMonsterClan | None,
    member_id: str,
) -> AdminGeneratedMonsterMember | None:
    if clan is None:
        return None
    return next((member for member in clan.members if member.monster_id == member_id), None)


async def _task_notice_from_query(request: Request) -> AITaskNotice | None:
    kind = str(request.query_params.get("ai_kind") or "").strip()
    raw_error = str(request.query_params.get("ai_error") or "").strip()
    task_ids = [
        task_id.strip() for task_id in str(request.query_params.get("ai_task_ids") or "").split(",") if task_id.strip()
    ]
    try:
        requested = int(str(request.query_params.get("ai_requested") or "0"))
    except ValueError:
        requested = 0
    if not kind and not raw_error and not task_ids:
        return None
    tasks: list[AdminAIGenerationTask] = []
    status_error = raw_error
    for task_id in task_ids:
        try:
            tasks.append(await _api(request).get_generation_task(task_id))
        except (AttributeError, httpx.HTTPStatusError, httpx.RequestError) as exc:
            status_error = status_error or f"не удалось получить статус задачи {task_id}: {exc.__class__.__name__}"
    return AITaskNotice(
        kind=kind,
        title=_task_notice_title(kind),
        message=_task_notice_message(kind, tasks=tasks, requested=requested, error=status_error),
        task_ids=task_ids,
        tasks=tasks,
        requested=requested,
        error=status_error,
    )


def _task_notice_title(kind: str) -> str:
    return {
        "clan_flavor": "Описания семьи",
        "member_images": "Картинки участников",
        "member_images_batch": "Картинки участников",
        "member_image": "Картинка участника",
    }.get(kind, "AI-задача")


def _task_notice_message(
    kind: str,
    *,
    tasks: list[AdminAIGenerationTask],
    requested: int,
    error: str,
) -> str:
    if error:
        return "Ошибка постановки или чтения статуса задачи."
    if not tasks:
        return "Задача отправлена, но backend не вернул id для отслеживания."
    if any(task.status == "failed" for task in tasks):
        return "Одна или несколько задач завершились ошибкой."
    if all(task.status == "done" for task in tasks):
        return "Задача закончилась успешно." if len(tasks) == 1 else "Все отслеживаемые задачи закончились успешно."
    if any(task.status == "running" for task in tasks):
        return "Задача выполняется."
    if any(task.status == "cooldown" for task in tasks):
        return "Задача временно отложена после ошибки, будет повтор."
    if kind == "member_images_batch" and requested > len(tasks):
        return f"Задачи поставлены: {requested}. Отслеживаются первые {len(tasks)}."
    return "Задача поставлена в очередь."


def _task_ids_from_result(result: dict[str, Any]) -> list[str]:
    if result.get("task_id"):
        return [str(result["task_id"])]
    return [str(task_id) for task_id in result.get("task_ids") or [] if str(task_id)]


def _task_redirect_url(
    path: str,
    params: dict[str, str],
    *,
    kind: str,
    task_ids: list[str] | None = None,
    requested: int = 0,
    error: str = "",
) -> str:
    query = dict(params)
    if kind:
        query["ai_kind"] = kind
    if task_ids:
        query["ai_task_ids"] = ",".join(task_ids)
    if requested:
        query["ai_requested"] = str(requested)
    if error:
        query["ai_error"] = error[:500]
    return f"{path}?{urlencode(query)}"


def _split_url_query(url: str) -> tuple[str, dict[str, str]]:
    path, _, raw_query = url.partition("?")
    return path, dict(parse_qsl(raw_query, keep_blank_values=False))


def _monster_browser_redirect_url(form: Any) -> str:
    params: dict[str, str] = {}
    for key in ("family_id", "tier", "storage_backend"):
        value = str(form.get(key) or "").strip()
        if value:
            params[key] = value
    if form.get("missing_image") == "1":
        params["missing_image"] = "1"
    query = urlencode(params)
    return f"{_BASE}/monster-browser?{query}" if query else f"{_BASE}/monster-browser"


def _rebuild_options_from_form(form: Any) -> dict[str, Any]:
    raw_limit = str(form.get("limit") or _GENERATED_MONSTER_PAGE_LIMIT)
    try:
        limit = int(raw_limit)
    except ValueError:
        limit = _GENERATED_MONSTER_PAGE_LIMIT
    return {
        "family_id": str(form.get("family_id") or "").strip() or None,
        "clan_id": str(form.get("clan_id") or "").strip() or None,
        "limit": max(1, min(500, limit)),
        "force": form.get("force") == "1",
        "remove_obsolete_members": form.get("remove_obsolete_members") == "1",
    }


cabinet_site.register(ContentOpsAdmin)

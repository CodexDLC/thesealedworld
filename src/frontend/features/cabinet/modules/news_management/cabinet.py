from __future__ import annotations

from typing import Any, ClassVar

from fastapi import Request
from starlette.responses import RedirectResponse, Response

from fastapi_cabinet import CabinetAdmin, MetricWidget, SidebarItem, TableWidget, cabinet_site
from fastapi_cabinet.contracts.widgets import MetricWidgetMap, TableColumnMap, TableWidgetMap
from fastapi_cabinet.rendering.layout_mapper import build_layout_map
from fastapi_cabinet.runtime import resolve_active_admin
from src.frontend.core.database.session import async_session_factory
from src.frontend.features.cabinet.modules.news_management.cover_library import get_news_cover_presets
from src.frontend.features.news.repositories.article_repository import ArticleRepository

_MOUNT_PATH = "/admin"
_BASE = "/admin/news"


async def _get_repo() -> tuple[Any, ArticleRepository]:
    session = async_session_factory()
    return session, ArticleRepository(session)


# ── Dashboard providers ──────────────────────────────────────────────────────


async def _total_provider(request: Request) -> MetricWidgetMap:
    session, repo = await _get_repo()
    async with session:
        total = await repo.count_all()
        published = await repo.count_published()
        drafts = await repo.count_drafts()
    return MetricWidgetMap(
        key="news_total",
        title="Всего статей",
        value=str(total),
        subtitle=f"опубл. {published} / черн. {drafts}",
    )


async def _articles_table_provider(request: Request) -> TableWidgetMap:
    session, repo = await _get_repo()
    async with session:
        articles = await repo.get_all(limit=50)
    rows = [
        {
            "id": a.id,
            "title": a.title,
            "slug": a.slug,
            "status": "Опубликована" if a.is_published else "Черновик",
            "published_at": a.published_at.strftime("%d.%m.%Y %H:%M") if a.published_at else "—",
            "created_at": a.created_at.strftime("%d.%m.%Y %H:%M") if a.created_at else "—",
            "href": f"{_BASE}/edit?id={a.id}",
        }
        for a in articles
    ]
    return TableWidgetMap(
        key="articles_list",
        title="Все статьи",
        columns=[
            TableColumnMap(key="title", label="Заголовок"),
            TableColumnMap(key="slug", label="Slug"),
            TableColumnMap(key="status", label="Статус"),
            TableColumnMap(key="published_at", label="Опубликована"),
            TableColumnMap(key="created_at", label="Создана"),
        ],
        rows=rows,
        row_href_key="href",
    )


async def _drafts_table_provider(request: Request) -> TableWidgetMap:
    session, repo = await _get_repo()
    async with session:
        articles = await repo.get_drafts(limit=50)
    rows = [
        {
            "id": a.id,
            "title": a.title,
            "slug": a.slug,
            "created_at": a.created_at.strftime("%d.%m.%Y %H:%M") if a.created_at else "—",
            "href": f"{_BASE}/edit?id={a.id}",
        }
        for a in articles
    ]
    return TableWidgetMap(
        key="drafts_list",
        title="Черновики",
        columns=[
            TableColumnMap(key="title", label="Заголовок"),
            TableColumnMap(key="slug", label="Slug"),
            TableColumnMap(key="created_at", label="Создана"),
        ],
        rows=rows,
        row_href_key="href",
    )


# ── Layout helper ────────────────────────────────────────────────────────────


def _render_news_page(admin: Any, request: Request, title: str, widgets: list) -> Any:
    active_path = str(request.url.path)
    active_admin = resolve_active_admin(active_path, cabinet_site.registry, _MOUNT_PATH)
    layout = build_layout_map(
        cabinet_site.registry,
        mount_path=_MOUNT_PATH,
        active_admin=active_admin,
        static_mount_path=cabinet_site.static_mount_path,
        active_path=active_path,
        title=title,
    )
    return cabinet_site.templates.TemplateResponse(
        request,
        "cabinet/module.html",
        {"layout": layout, "module": admin, "module_context": {}, "widgets": widgets},
    )


# ── Form-page widget maps ───────────────────────────────────────────────────


class ArticleFormWidgetMap:
    kind = "article_form"

    def __init__(
        self,
        *,
        key: str,
        title: str,
        action_url: str,
        article_id: int | None = None,
        slug: str = "",
        article_title: str = "",
        preview: str = "",
        body: str = "",
        cover_image: str = "",
        is_published: bool = False,
        cancel_url: str = "/admin/news",
    ) -> None:
        self.key = key
        self.title = title
        self.action_url = action_url
        self.article_id = article_id
        self.slug = slug
        self.article_title = article_title
        self.preview = preview
        self.body = body
        self.cover_image = cover_image
        self.is_published = is_published
        self.cancel_url = cancel_url
        self.cover_presets = get_news_cover_presets()


# ── Admin class ──────────────────────────────────────────────────────────────

_FORM_WIDGETS = (MetricWidget(key="news_total", title="Статей", provider="news.total", order=10),)


class NewsManagementAdmin(CabinetAdmin):
    key = "news_management"
    label = "Новости"
    group = "site"
    group_label = "Сайт"
    path = "/admin/news"
    order = 5
    sidebar: ClassVar = (
        SidebarItem(key="articles", label="Все статьи", path="/admin/news", order=10),
        SidebarItem(key="create", label="Создать", path="/admin/news/create", order=20),
        SidebarItem(key="drafts", label="Черновики", path="/admin/news/drafts", badge_key="drafts", order=30),
    )
    dashboard_widgets: ClassVar = (
        MetricWidget(key="news_total", title="Статей", provider="news.total", order=10),
        TableWidget(key="articles_list", title="Все статьи", provider="news.articles", order=20),
    )
    sub_pages: ClassVar = {
        "drafts": (TableWidget(key="drafts_list", title="Черновики", provider="news.drafts", order=10),),
    }
    action_routes: ClassVar = {
        "create": ("GET", "handle_create_form"),
        "save": ("POST", "handle_save"),
        "edit": ("GET", "handle_edit_form"),
        "update": ("POST", "handle_update"),
        "toggle-publish": ("POST", "handle_toggle_publish"),
        "delete": ("POST", "handle_delete"),
    }
    providers: ClassVar = {
        "news.total": _total_provider,
        "news.articles": _articles_table_provider,
        "news.drafts": _drafts_table_provider,
    }

    async def get_sidebar_badges(self, request: Request) -> dict[str, int | str]:
        session, repo = await _get_repo()
        async with session:
            drafts = await repo.count_drafts()
        if drafts == 0:
            return {}
        return {"drafts": drafts}

    # ── Create form ──────────────────────────────────────────────────────────

    async def handle_create_form(self, request: Request) -> Response:
        form_widget = ArticleFormWidgetMap(
            key="article_form",
            title="Новая статья",
            action_url=f"{_BASE}/save",
        )
        active_admin = resolve_active_admin(request.url.path, cabinet_site.registry, _MOUNT_PATH)
        layout = build_layout_map(
            cabinet_site.registry,
            mount_path=_MOUNT_PATH,
            active_admin=active_admin,
            static_mount_path=cabinet_site.static_mount_path,
            active_path=str(request.url.path),
            title="Создать статью",
        )
        return cabinet_site.templates.TemplateResponse(
            request,
            "cabinet/article_form.html",
            {"layout": layout, "module": self, "module_context": {}, "form": form_widget, "widgets": []},
        )

    async def handle_save(self, request: Request) -> Response:
        form = await request.form()
        slug = str(form.get("slug", "")).strip()
        title = str(form.get("title", "")).strip()
        preview = str(form.get("preview", "")).strip()
        body = str(form.get("body", "")).strip()
        cover_image = str(form.get("cover_image", "")).strip() or None

        session, repo = await _get_repo()
        async with session:
            await repo.create(slug=slug, title=title, preview=preview, body=body, cover_image=cover_image)
        return RedirectResponse(url=_BASE, status_code=303)

    # ── Edit form ────────────────────────────────────────────────────────────

    async def handle_edit_form(self, request: Request) -> Response:
        article_id = int(request.query_params.get("id", 0))
        session, repo = await _get_repo()
        async with session:
            article = await repo.get_by_id(article_id)
        if article is None:
            return RedirectResponse(url=_BASE, status_code=303)

        form_widget = ArticleFormWidgetMap(
            key="article_form",
            title="Редактировать статью",
            action_url=f"{_BASE}/update",
            article_id=article.id,
            slug=article.slug,
            article_title=article.title,
            preview=article.preview,
            body=article.body,
            cover_image=article.cover_image or "",
            is_published=article.is_published,
        )
        active_admin = resolve_active_admin(request.url.path, cabinet_site.registry, _MOUNT_PATH)
        layout = build_layout_map(
            cabinet_site.registry,
            mount_path=_MOUNT_PATH,
            active_admin=active_admin,
            static_mount_path=cabinet_site.static_mount_path,
            active_path=str(request.url.path),
            title=f"Редактировать: {article.title}",
        )
        return cabinet_site.templates.TemplateResponse(
            request,
            "cabinet/article_form.html",
            {"layout": layout, "module": self, "module_context": {}, "form": form_widget, "widgets": []},
        )

    async def handle_update(self, request: Request) -> Response:
        form = await request.form()
        article_id = int(form.get("article_id", 0))  # type: ignore[arg-type]
        slug = str(form.get("slug", "")).strip()
        title = str(form.get("title", "")).strip()
        preview = str(form.get("preview", "")).strip()
        body = str(form.get("body", "")).strip()
        cover_image = str(form.get("cover_image", "")).strip() or None

        session, repo = await _get_repo()
        async with session:
            article = await repo.get_by_id(article_id)
            if article is None:
                return RedirectResponse(url=_BASE, status_code=303)
            await repo.update(article, slug=slug, title=title, preview=preview, body=body, cover_image=cover_image)
        return RedirectResponse(url=f"{_BASE}/edit?id={article_id}", status_code=303)

    # ── Publish / Unpublish ──────────────────────────────────────────────────

    async def handle_toggle_publish(self, request: Request) -> Response:
        form = await request.form()
        article_id = int(form.get("article_id", 0))  # type: ignore[arg-type]
        session, repo = await _get_repo()
        async with session:
            article = await repo.get_by_id(article_id)
            if article is not None:
                await repo.toggle_publish(article)
        return RedirectResponse(url=f"{_BASE}/edit?id={article_id}", status_code=303)

    # ── Delete ───────────────────────────────────────────────────────────────

    async def handle_delete(self, request: Request) -> Response:
        form = await request.form()
        article_id = int(form.get("article_id", 0))  # type: ignore[arg-type]
        session, repo = await _get_repo()
        async with session:
            article = await repo.get_by_id(article_id)
            if article is not None:
                await repo.delete(article)
        return RedirectResponse(url=_BASE, status_code=303)


cabinet_site.register(NewsManagementAdmin)

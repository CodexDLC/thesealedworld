from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import Request
from starlette.responses import RedirectResponse, Response

from fastapi_cabinet import CabinetAdmin, MetricWidget, SidebarItem, TableWidget, cabinet_site
from fastapi_cabinet.contracts.widgets import MetricWidgetMap, TableColumnMap, TableWidgetMap
from fastapi_cabinet.rendering.layout_mapper import build_layout_map
from fastapi_cabinet.runtime import resolve_active_admin
from src.frontend.config.settings import settings
from src.frontend.core.database.session import get_session_context
from src.frontend.features.auth.repositories.user_repository import UserRepository
from src.frontend.integrations.backend_api.admin_players import (
    AdminPlayerCharacterDetail,
    AdminPlayerCharacterListResponse,
    AdminPlayerCharacterSummary,
    AdminPlayerGenerateCharacterRequest,
    AdminPlayerGenerationClanOption,
    AdminPlayersApi,
)

if TYPE_CHECKING:
    from src.frontend.features.auth.models import User

_MOUNT_PATH = "/admin"
_BASE = "/admin/accounts"
_ACCOUNT_LIMIT = 25
_CHARACTER_LIMIT = 25
_INVENTORY_LIMIT = 50
_MAX_CHARACTER_SLOTS = 4


@dataclass(frozen=True)
class AccountRow:
    user_id: str
    email: str
    is_active: bool
    is_superuser: bool
    tester_status: str
    created_at: str


@dataclass(frozen=True)
class AccountBrowserContext:
    accounts: list[AccountRow]
    total: int
    limit: int
    offset: int
    query: str
    prev_url: str
    next_url: str
    error: str = ""


@dataclass(frozen=True)
class AccountDetailContext:
    account: AccountRow | None
    characters: AdminPlayerCharacterListResponse | None
    slots: list[AccountCharacterSlot]
    generation_options: list[AdminPlayerGenerationClanOption]
    prev_url: str
    next_url: str
    error: str = ""


@dataclass(frozen=True)
class AccountCharacterSlot:
    index: int
    character: AdminPlayerCharacterSummary | None
    state: str
    action_label: str
    action_enabled: bool = False


@dataclass(frozen=True)
class CharacterDetailContext:
    detail: AdminPlayerCharacterDetail | None
    account_id: str
    prev_url: str
    next_url: str
    error: str = ""


def _api(request: Request) -> AdminPlayersApi:
    client: httpx.AsyncClient = request.app.state.backend_http_client
    return AdminPlayersApi(client=client, base_url=settings.backend_base_url)


async def _registered_accounts_provider(request: Request) -> MetricWidgetMap:
    try:
        async with get_session_context() as session:
            value = str(await UserRepository(session).count_all())
            subtitle = "site.auth_users"
    except Exception:
        value = "—"
        subtitle = "site DB недоступна"
    return MetricWidgetMap(key="accounts_total", title="Аккаунтов", value=value, subtitle=subtitle)


async def _accounts_table_provider(request: Request) -> TableWidgetMap:
    browser = await _load_account_browser_context(request)
    return TableWidgetMap(
        key="accounts_table",
        title="Последние аккаунты",
        columns=[
            TableColumnMap(key="email", label="Email"),
            TableColumnMap(key="tester_status", label="Тестер"),
            TableColumnMap(key="flags", label="Флаги"),
            TableColumnMap(key="created_at", label="Создан"),
        ],
        rows=[
            {
                "email": row.email,
                "tester_status": row.tester_status,
                "flags": _account_flags(row),
                "created_at": row.created_at or "—",
                "href": f"{_BASE}/account-detail?user_id={row.user_id}",
            }
            for row in browser.accounts
        ],
        row_href_key="href",
    )


async def _load_account_browser_context(request: Request) -> AccountBrowserContext:
    params = request.query_params
    query = (params.get("q") or "").strip()
    limit = _bounded_int(params.get("limit"), default=_ACCOUNT_LIMIT, low=1, high=100)
    offset = _bounded_int(params.get("offset"), default=0, low=0, high=1_000_000)
    try:
        async with get_session_context() as session:
            repo = UserRepository(session)
            total = await repo.count_matching(query)
            users = await repo.list_page(limit=limit, offset=offset, query=query)
    except Exception as exc:
        return AccountBrowserContext(
            accounts=[],
            total=0,
            limit=limit,
            offset=offset,
            query=query,
            prev_url="",
            next_url="",
            error=f"site DB недоступна: {exc.__class__.__name__}",
        )

    return AccountBrowserContext(
        accounts=[_account_row(user) for user in users],
        total=total,
        limit=limit,
        offset=offset,
        query=query,
        prev_url=_accounts_url(query=query, limit=limit, offset=max(0, offset - limit)) if offset > 0 else "",
        next_url=_accounts_url(query=query, limit=limit, offset=offset + limit) if offset + limit < total else "",
    )


async def _load_account_detail_context(request: Request) -> AccountDetailContext:
    raw_user_id = (request.query_params.get("user_id") or "").strip()
    char_limit = _bounded_int(request.query_params.get("limit"), default=_CHARACTER_LIMIT, low=1, high=100)
    char_offset = _bounded_int(request.query_params.get("offset"), default=0, low=0, high=1_000_000)
    try:
        user_id = UUID(raw_user_id)
    except ValueError:
        return AccountDetailContext(
            account=None,
            characters=None,
            slots=[],
            generation_options=[],
            prev_url="",
            next_url="",
            error="Некорректный user_id",
        )

    try:
        async with get_session_context() as session:
            user = await UserRepository(session).get_by_id(user_id)
    except Exception as exc:
        return AccountDetailContext(
            account=None,
            characters=None,
            slots=[],
            generation_options=[],
            prev_url="",
            next_url="",
            error=f"site DB недоступна: {exc.__class__.__name__}",
        )
    if user is None:
        return AccountDetailContext(
            account=None,
            characters=None,
            slots=[],
            generation_options=[],
            prev_url="",
            next_url="",
            error="Аккаунт не найден",
        )

    try:
        api = _api(request)
        characters = await api.list_user_characters(user_id, limit=char_limit, offset=char_offset)
        generation_options = (await api.list_character_generation_options()).clans
        error = ""
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        characters = None
        generation_options = []
        error = f"game backend недоступен: {exc.__class__.__name__}"
    generation_error = (request.query_params.get("generation_error") or "").strip()
    if generation_error:
        error = f"генерация не выполнена: {generation_error}"

    total = characters.total if characters else 0
    return AccountDetailContext(
        account=_account_row(user),
        characters=characters,
        slots=_account_character_slots(
            characters.items if characters else [], backend_available=characters is not None
        ),
        generation_options=generation_options,
        prev_url=_account_url(user_id, limit=char_limit, offset=max(0, char_offset - char_limit))
        if char_offset > 0
        else "",
        next_url=_account_url(user_id, limit=char_limit, offset=char_offset + char_limit)
        if char_offset + char_limit < total
        else "",
        error=error,
    )


async def _load_character_detail_context(request: Request) -> CharacterDetailContext:
    account_id = (request.query_params.get("user_id") or "").strip()
    character_id = _bounded_int(request.query_params.get("character_id"), default=0, low=0, high=1_000_000_000)
    limit = _bounded_int(request.query_params.get("limit"), default=_INVENTORY_LIMIT, low=1, high=100)
    offset = _bounded_int(request.query_params.get("offset"), default=0, low=0, high=1_000_000)
    if character_id <= 0:
        return CharacterDetailContext(
            detail=None, account_id=account_id, prev_url="", next_url="", error="Некорректный character_id"
        )
    try:
        detail = await _api(request).get_character_detail(character_id, inventory_limit=limit, inventory_offset=offset)
        error = ""
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        detail = None
        error = f"game backend недоступен: {exc.__class__.__name__}"

    total = detail.carried_total if detail else 0
    return CharacterDetailContext(
        detail=detail,
        account_id=account_id,
        prev_url=_character_url(account_id, character_id, limit=limit, offset=max(0, offset - limit))
        if offset > 0
        else "",
        next_url=_character_url(account_id, character_id, limit=limit, offset=offset + limit)
        if offset + limit < total
        else "",
        error=error,
    )


class AccountsAdmin(CabinetAdmin):
    key = "accounts"
    label = "Аккаунты"
    group = "site"
    group_label = "Сайт"
    path = _BASE
    order = 3
    sidebar: ClassVar = (
        SidebarItem(key="overview", label="Обзор", path=_BASE, order=10),
        SidebarItem(key="accounts", label="Аккаунты", path=f"{_BASE}/browser", order=20),
    )
    dashboard_widgets: ClassVar = (
        MetricWidget(key="accounts_total", title="Аккаунтов", provider="accounts.total", order=10),
        TableWidget(key="accounts_table", title="Последние аккаунты", provider="accounts.table", order=20),
    )
    action_routes: ClassVar = {
        "browser": ("GET", "handle_browser"),
        "account-detail": ("GET", "handle_account_detail"),
        "character-detail": ("GET", "handle_character_detail"),
        "generate-character": ("POST", "handle_generate_character"),
    }
    providers: ClassVar = {
        "accounts.total": _registered_accounts_provider,
        "accounts.table": _accounts_table_provider,
    }

    async def handle_browser(self, request: Request) -> Response:
        browser = await _load_account_browser_context(request)
        return _render_custom(self, request, "cabinet/accounts_browser.html", {"browser": browser, "base_url": _BASE})

    async def handle_account_detail(self, request: Request) -> Response:
        account = await _load_account_detail_context(request)
        return _render_custom(
            self,
            request,
            "cabinet/account_detail.html",
            {"account_view": account, "base_url": _BASE},
        )

    async def handle_character_detail(self, request: Request) -> Response:
        character = await _load_character_detail_context(request)
        return _render_custom(
            self,
            request,
            "cabinet/account_character_detail.html",
            {"character_view": character, "base_url": _BASE},
        )

    async def handle_generate_character(self, request: Request) -> Response:
        form = await request.form()
        raw_user_id = str(form.get("user_id") or "")
        try:
            user_id = UUID(raw_user_id)
        except ValueError:
            return RedirectResponse(f"{_BASE}/browser", status_code=303)
        payload = AdminPlayerGenerateCharacterRequest(
            slot_index=_bounded_int(str(form.get("slot_index") or ""), default=1, low=1, high=4),
            name=str(form.get("name") or "").strip(),
            gender=str(form.get("gender") or "random"),
            skill_progress_percent=_bounded_int(
                str(form.get("skill_progress_percent") or ""),
                default=75,
                low=0,
                high=100,
            ),
            item_tier=_bounded_int(str(form.get("item_tier") or ""), default=1, low=0, high=7),
            source_clan_id=str(form.get("source_clan_id") or ""),
            request_ai_text=str(form.get("request_ai_text") or "") == "1",
        )
        try:
            await _api(request).generate_test_character(user_id, payload)
            suffix = ""
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            suffix = f"&generation_error={exc.__class__.__name__}"
        return RedirectResponse(f"{_BASE}/account-detail?user_id={user_id}{suffix}", status_code=303)


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


def _account_row(user: User) -> AccountRow:
    return AccountRow(
        user_id=str(user.id),
        email=str(user.email),
        is_active=bool(user.is_active),
        is_superuser=bool(user.is_superuser),
        tester_status=str(user.tester_status or "none"),
        created_at=user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "",
    )


def _account_flags(row: AccountRow) -> str:
    flags = []
    if row.is_superuser:
        flags.append("superuser")
    if not row.is_active:
        flags.append("inactive")
    return ", ".join(flags) if flags else "—"


def _account_character_slots(
    characters: list[AdminPlayerCharacterSummary],
    *,
    backend_available: bool,
) -> list[AccountCharacterSlot]:
    slots: list[AccountCharacterSlot] = []
    visible_characters = characters[:_MAX_CHARACTER_SLOTS]
    for index, character in enumerate(visible_characters, start=1):
        slots.append(
            AccountCharacterSlot(
                index=index,
                character=character,
                state="занят",
                action_label="Открыть",
                action_enabled=True,
            )
        )
    for index in range(len(visible_characters) + 1, _MAX_CHARACTER_SLOTS + 1):
        slots.append(
            AccountCharacterSlot(
                index=index,
                character=None,
                state="пустой" if backend_available else "не загружен",
                action_label="Создать персонажа" if backend_available else "backend недоступен",
            )
        )
    return slots


def _bounded_int(raw: str | None, *, default: int, low: int, high: int) -> int:
    try:
        value = int(raw) if raw is not None else default
    except (TypeError, ValueError):
        return default
    return max(low, min(high, value))


def _accounts_url(*, query: str, limit: int, offset: int) -> str:
    params = {"limit": str(limit), "offset": str(offset)}
    if query:
        params["q"] = query
    return f"{_BASE}/browser?{urlencode(params)}"


def _account_url(user_id: UUID, *, limit: int, offset: int) -> str:
    return f"{_BASE}/account-detail?{urlencode({'user_id': str(user_id), 'limit': str(limit), 'offset': str(offset)})}"


def _character_url(user_id: str, character_id: int, *, limit: int, offset: int) -> str:
    return (
        f"{_BASE}/character-detail?"
        f"{urlencode({'user_id': user_id, 'character_id': str(character_id), 'limit': str(limit), 'offset': str(offset)})}"
    )


cabinet_site.register(AccountsAdmin)

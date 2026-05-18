from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, ClassVar

import httpx
from starlette.responses import RedirectResponse, Response

from fastapi_cabinet import CabinetAdmin, EditableConfigWidget, ListWidget, SidebarItem, cabinet_site
from fastapi_cabinet.contracts.widgets import ConfigEntryRow, EditableConfigWidgetMap, ListWidgetMap
from src.frontend.config.settings import settings
from src.frontend.integrations.backend_api.game_config import GameConfigApi

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request

_UPDATE_URL = "/admin/game-settings/update-config"
_RESET_URL = "/admin/game-settings/reset-config"


def _config_provider(widget_key: str, title: str, namespace: str, redirect_to: str) -> Callable:
    async def provider(request: Request) -> EditableConfigWidgetMap:
        client: httpx.AsyncClient = request.app.state.backend_http_client
        api = GameConfigApi(client=client, base_url=settings.backend_base_url)
        try:
            entries = await api.list_namespace(namespace)
        except (httpx.HTTPStatusError, httpx.RequestError):
            entries = []
        return EditableConfigWidgetMap(
            key=widget_key,
            title=title,
            namespace=namespace,
            redirect_to=redirect_to,
            update_url=_UPDATE_URL,
            reset_url=_RESET_URL,
            entries=[
                ConfigEntryRow(
                    key=e.key,
                    current=e.current,
                    default=e.default,
                    value_type=e.value_type,
                    is_modified=e.is_modified,
                )
                for e in entries
            ],
        )

    return provider


async def _overview_provider(request: Request) -> ListWidgetMap:
    return ListWidgetMap(
        key="settings_overview",
        title="Разделы настроек",
        items=[
            "Бой — параметры боевой системы (Redis, live)",
            "Сценарии — параметры генерации сценариев (Redis, live)",
            "Исследование — параметры путешествий и событий (Redis, live)",
            "Redis Streams — состояние event bus (не подключено)",
            "Воркеры — состояние фоновых задач (не подключено)",
        ],
    )


async def _streams_provider(request: Request) -> ListWidgetMap:
    return ListWidgetMap(
        key="streams_status",
        title="Redis Streams",
        items=["Redis Streams система спроектирована, но ещё не подключена к игре"],
    )


async def _workers_provider(request: Request) -> ListWidgetMap:
    return ListWidgetMap(
        key="workers_status",
        title="Воркеры",
        items=["Мониторинг воркеров будет добавлен после интеграции Redis Streams"],
    )


class GameSettingsAdmin(CabinetAdmin):
    key = "game_settings"
    label = "Настройки"
    group = "game_server"
    group_label = "Гейм Сервер"
    path = "/admin/game-settings"
    order = 90
    sidebar: ClassVar = (
        SidebarItem(key="combat", label="Бой", path="/admin/game-settings/combat", order=10),
        SidebarItem(key="scenario", label="Сценарии", path="/admin/game-settings/scenario", order=20),
        SidebarItem(key="exploration", label="Исследование", path="/admin/game-settings/exploration", order=30),
        SidebarItem(key="streams", label="Redis Streams", path="/admin/game-settings/streams", order=40),
        SidebarItem(key="workers", label="Воркеры", path="/admin/game-settings/workers", order=50),
    )
    dashboard_widgets: ClassVar = (
        ListWidget(key="settings_overview", title="Разделы настроек", provider="game_settings.overview", order=10),
    )
    sub_pages: ClassVar = {
        "combat": (
            EditableConfigWidget(key="combat_cfg", title="Настройки боя", provider="game_settings.combat", order=10),
        ),
        "scenario": (
            EditableConfigWidget(
                key="scenario_cfg", title="Настройки сценариев", provider="game_settings.scenario", order=10
            ),
        ),
        "exploration": (
            EditableConfigWidget(
                key="exploration_cfg",
                title="Настройки исследования",
                provider="game_settings.exploration",
                order=10,
            ),
        ),
        "streams": (
            ListWidget(
                key="streams_status", title="Redis Streams (статус)", provider="game_settings.streams", order=10
            ),
        ),
        "workers": (
            ListWidget(key="workers_status", title="Воркеры (статус)", provider="game_settings.workers", order=10),
        ),
    }
    action_routes: ClassVar = {
        "update-config": ("POST", "handle_update_config"),
        "reset-config": ("POST", "handle_reset_config"),
    }
    providers: ClassVar = {
        "game_settings.overview": _overview_provider,
        "game_settings.combat": _config_provider(
            "combat_cfg", "Настройки боя", "combat", "/admin/game-settings/combat"
        ),
        "game_settings.scenario": _config_provider(
            "scenario_cfg", "Настройки сценариев", "scenario", "/admin/game-settings/scenario"
        ),
        "game_settings.exploration": _config_provider(
            "exploration_cfg", "Настройки исследования", "exploration", "/admin/game-settings/exploration"
        ),
        "game_settings.streams": _streams_provider,
        "game_settings.workers": _workers_provider,
    }

    async def handle_update_config(self, request: Request) -> Response:
        form = await request.form()
        namespace = str(form.get("namespace", ""))
        redirect_to = str(form.get("redirect_to", "/admin/game-settings"))
        client: httpx.AsyncClient = request.app.state.backend_http_client
        api = GameConfigApi(client=client, base_url=settings.backend_base_url)
        for raw_key, value in form.multi_items():
            if raw_key.startswith("values[") and raw_key.endswith("]"):
                key = raw_key[7:-1]
                with contextlib.suppress(httpx.HTTPStatusError, httpx.RequestError):
                    await api.set_value(namespace, key, str(value))
        return RedirectResponse(url=redirect_to, status_code=303)

    async def handle_reset_config(self, request: Request) -> Response:
        form = await request.form()
        namespace = str(form.get("namespace", ""))
        key = str(form.get("key", ""))
        redirect_to = str(form.get("redirect_to", "/admin/game-settings"))
        client: httpx.AsyncClient = request.app.state.backend_http_client
        api = GameConfigApi(client=client, base_url=settings.backend_base_url)
        with contextlib.suppress(httpx.HTTPStatusError, httpx.RequestError):
            await api.reset_key(namespace, key)
        return RedirectResponse(url=redirect_to, status_code=303)


cabinet_site.register(GameSettingsAdmin)

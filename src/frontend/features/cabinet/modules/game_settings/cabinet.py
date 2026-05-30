from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import ClassVar

import httpx
from fastapi import Request
from starlette.responses import RedirectResponse, Response

from fastapi_cabinet import CabinetAdmin, EditableConfigWidget, ListWidget, SidebarItem, cabinet_site
from fastapi_cabinet.contracts.widgets import ConfigEntryRow, EditableConfigWidgetMap, ListWidgetMap
from src.frontend.config.settings import settings
from src.frontend.integrations.backend_api.combat_ai_testing import CombatAiSimulationRun, CombatAiTestingApi
from src.frontend.integrations.backend_api.game_config import GameConfigApi

_UPDATE_URL = "/admin/game-settings/update-config"
_RESET_URL = "/admin/game-settings/reset-config"
_RESET_NAMESPACE_URL = "/admin/game-settings/reset-namespace"

_COMBAT_AI_ENTRY_META = {
    "ACTIVE_POLICY_ID": {
        "label": "Активная политика ИИ",
        "description": "Версия обучения для новых боев. Пусто означает runtime default или env override.",
    },
    "EXPLORATION_RANDOMNESS_MULT": {
        "label": "Множитель случайности",
        "description": "Управляет случайностью выбора хода: 0.0 почти детерминированно, 1.0 как в policy.",
    },
    "TRAINING_ENABLED": {
        "label": "Разрешить обучение",
        "description": "Флаг для training entry points. В live-бой сам по себе обученные веса не включает.",
    },
    "TRAINING_SEED": {
        "label": "Seed обучения",
        "description": "Фиксирует воспроизводимость тренировок. 0 оставляет текущий дефолт.",
    },
}


def _config_provider(
    widget_key: str,
    title: str,
    namespace: str,
    redirect_to: str,
    *,
    entry_meta: dict[str, dict[str, str]] | None = None,
) -> Callable:
    async def provider(request: Request) -> EditableConfigWidgetMap:
        client: httpx.AsyncClient = request.app.state.backend_http_client
        api = GameConfigApi(client=client, base_url=settings.backend_base_url)
        try:
            entries = await api.list_namespace(namespace)
        except (httpx.HTTPStatusError, httpx.RequestError):
            entries = []
        metadata = entry_meta or {}
        choices_by_key = await _config_choices(request, namespace)
        return EditableConfigWidgetMap(
            key=widget_key,
            title=title,
            namespace=namespace,
            redirect_to=redirect_to,
            update_url=_UPDATE_URL,
            reset_url=_RESET_URL,
            reset_namespace_url=_RESET_NAMESPACE_URL,
            entries=[
                ConfigEntryRow(
                    key=e.key,
                    current=e.current,
                    default=e.default,
                    value_type=e.value_type,
                    is_modified=e.is_modified,
                    label=metadata.get(e.key, {}).get("label"),
                    description=metadata.get(e.key, {}).get("description"),
                    choices=choices_by_key.get(e.key, []),
                )
                for e in entries
            ],
        )

    return provider


async def _config_choices(request: Request, namespace: str) -> dict[str, list[dict[str, str]]]:
    if namespace != "combat_ai":
        return {}
    client: httpx.AsyncClient = request.app.state.backend_http_client
    api = CombatAiTestingApi(client=client, base_url=settings.backend_base_url)
    try:
        runs = await api.list_runs(limit=50, run_kind="training")
    except (AttributeError, httpx.HTTPStatusError, httpx.RequestError):
        runs = []
    return {"ACTIVE_POLICY_ID": _policy_choices(runs)}


def _policy_choices(runs: list[CombatAiSimulationRun]) -> list[dict[str, str]]:
    choices = [{"value": "", "label": "runtime default / env override"}]
    for run in runs:
        if run.status != "completed" or not isinstance(run.metadata.get("best_policy"), dict):
            continue
        reward = f"{run.reward:.3f}" if run.reward is not None else "n/a"
        policy_id = str(run.metadata.get("best_policy", {}).get("policy_id") or run.policy_ref or "candidate")
        created = run.created_at[:16] if run.created_at else run.id[:8]
        choices.append(
            {
                "value": run.id,
                "label": f"{created} | reward {reward} | {policy_id}",
            }
        )
    return choices


async def _overview_provider(request: Request) -> ListWidgetMap:
    return ListWidgetMap(
        key="settings_overview",
        title="Разделы настроек",
        items=[
            "Бой — параметры боевой системы (Redis, live)",
            "Поведение ИИ боя — активная политика, случайность и training-флаги (Redis, live)",
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
        SidebarItem(key="combat_ai", label="Поведение ИИ боя", path="/admin/game-settings/combat-ai", order=15),
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
        "combat-ai": (
            EditableConfigWidget(
                key="combat_ai_cfg",
                title="Поведение ИИ боя",
                provider="game_settings.combat_ai",
                order=10,
            ),
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
        "reset-namespace": ("POST", "handle_reset_namespace"),
    }
    providers: ClassVar = {
        "game_settings.overview": _overview_provider,
        "game_settings.combat": _config_provider(
            "combat_cfg", "Настройки боя", "combat", "/admin/game-settings/combat"
        ),
        "game_settings.combat_ai": _config_provider(
            "combat_ai_cfg",
            "Поведение ИИ боя",
            "combat_ai",
            "/admin/game-settings/combat-ai",
            entry_meta=_COMBAT_AI_ENTRY_META,
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
        # Dedupe values per key — last occurrence wins. Needed for boolean
        # checkboxes which submit a hidden "false" followed by "true" when
        # checked (template uses this trick to send a value even when unchecked).
        values: dict[str, str] = {}
        for raw_key, value in form.multi_items():
            if raw_key.startswith("values[") and raw_key.endswith("]"):
                values[raw_key[7:-1]] = str(value)
        for key, value in values.items():
            with contextlib.suppress(httpx.HTTPStatusError, httpx.RequestError):
                await api.set_value(namespace, key, value)
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

    async def handle_reset_namespace(self, request: Request) -> Response:
        form = await request.form()
        namespace = str(form.get("namespace", ""))
        redirect_to = str(form.get("redirect_to", "/admin/game-settings"))
        client: httpx.AsyncClient = request.app.state.backend_http_client
        api = GameConfigApi(client=client, base_url=settings.backend_base_url)
        with contextlib.suppress(httpx.HTTPStatusError, httpx.RequestError):
            await api.reset_namespace(namespace)
        return RedirectResponse(url=redirect_to, status_code=303)


cabinet_site.register(GameSettingsAdmin)

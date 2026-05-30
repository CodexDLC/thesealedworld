from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
from fastapi import Request

from fastapi_cabinet.contracts.widgets import EditableConfigWidgetMap, ListWidgetMap
from src.frontend.features.cabinet.modules.game_settings.cabinet import (
    GameSettingsAdmin,
    _config_provider,
    _overview_provider,
    _streams_provider,
    _workers_provider,
)


def _make_request(handler) -> Request:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    app = SimpleNamespace(state=SimpleNamespace(backend_http_client=http_client))
    request = Request(
        {
            "type": "http",
            "app": app,
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 50000),
        }
    )
    return request


class TestStaticProviders:
    async def test_overview_provider_returns_non_empty_list_widget(self) -> None:
        request = _make_request(lambda r: httpx.Response(200, json=[]))
        widget = await _overview_provider(request)
        assert isinstance(widget, ListWidgetMap)
        assert widget.items, "overview must list at least one section"

    async def test_streams_provider_returns_list_widget(self) -> None:
        request = _make_request(lambda r: httpx.Response(200, json=[]))
        widget = await _streams_provider(request)
        assert isinstance(widget, ListWidgetMap)
        assert widget.key == "streams_status"

    async def test_workers_provider_returns_list_widget(self) -> None:
        request = _make_request(lambda r: httpx.Response(200, json=[]))
        widget = await _workers_provider(request)
        assert isinstance(widget, ListWidgetMap)
        assert widget.key == "workers_status"


class TestConfigProvider:
    async def test_returns_editable_widget_with_entries_from_backend(self) -> None:
        payload = [
            {
                "key": "PARRY_SKILL_MULT_PER_POINT",
                "namespace": "combat",
                "current": "7.0",
                "default": "4.0",
                "value_type": "float",
                "is_modified": True,
                "label": "Множитель навыка парирования",
                "description": "Усиливает шанс парирования от навыка.",
                "group": "Парирование и щит",
                "unit": "multiplier",
                "min_value": 0.0,
                "max_value": 10.0,
                "step": 0.1,
                "risk": "medium",
                "live_scope": "new_exchange",
                "tags": ["combat", "balance"],
            },
            {
                "key": "SESSION_TTL_SECONDS",
                "namespace": "combat",
                "current": "3600",
                "default": "3600",
                "value_type": "int",
                "is_modified": False,
            },
        ]

        def handler(req: httpx.Request) -> httpx.Response:
            assert req.method == "GET"
            assert req.url.path == "/api/internal/config/combat"
            return httpx.Response(200, content=json.dumps(payload).encode())

        request = _make_request(handler)
        provider = _config_provider("combat_cfg", "Combat", "combat", "/admin/game-settings/combat")
        widget = await provider(request)

        assert isinstance(widget, EditableConfigWidgetMap)
        assert widget.key == "combat_cfg"
        assert widget.namespace == "combat"
        assert widget.update_url == "/admin/game-settings/update-config"
        assert widget.reset_url == "/admin/game-settings/reset-config"
        assert widget.reset_namespace_url == "/admin/game-settings/reset-namespace"
        assert [e.key for e in widget.entries] == [
            "PARRY_SKILL_MULT_PER_POINT",
            "SESSION_TTL_SECONDS",
        ]
        modified = next(e for e in widget.entries if e.key == "PARRY_SKILL_MULT_PER_POINT")
        assert modified.is_modified is True
        assert modified.value_type == "float"
        assert modified.label == "Множитель навыка парирования"
        assert modified.description == "Усиливает шанс парирования от навыка."
        assert modified.group == "Парирование и щит"
        assert modified.unit == "multiplier"
        assert modified.min_value == 0.0
        assert modified.max_value == 10.0
        assert modified.step == 0.1
        assert modified.risk == "medium"
        assert modified.live_scope == "new_exchange"
        assert modified.tags == ["combat", "balance"]

    async def test_degrades_to_empty_entries_on_backend_error(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(500, content=b'{"detail":"boom"}')

        request = _make_request(handler)
        provider = _config_provider("combat_cfg", "Combat", "combat", "/admin/game-settings/combat")
        widget = await provider(request)

        assert isinstance(widget, EditableConfigWidgetMap)
        assert widget.entries == []

    async def test_degrades_to_empty_entries_on_network_error(self) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("offline", request=req)

        request = _make_request(handler)
        provider = _config_provider("combat_cfg", "Combat", "combat", "/admin/game-settings/combat")
        widget = await provider(request)

        assert isinstance(widget, EditableConfigWidgetMap)
        assert widget.entries == []

    async def test_preserves_backend_labels_without_local_metadata(self) -> None:
        payload = [
            {
                "key": "ACTIVE_POLICY_ID",
                "namespace": "combat_ai",
                "current": "",
                "default": "",
                "value_type": "str",
                "is_modified": False,
                "label": "Активная политика ИИ",
                "description": "Policy id для новых боев.",
            },
        ]

        request = _make_request(lambda _: httpx.Response(200, content=json.dumps(payload).encode()))
        provider = _config_provider(
            "combat_ai_cfg",
            "Поведение ИИ боя",
            "combat_ai",
            "/admin/game-settings/combat-ai",
        )
        widget = await provider(request)

        assert widget.span == 2
        assert widget.entries[0].key == "ACTIVE_POLICY_ID"
        assert widget.entries[0].label == "Активная политика ИИ"
        assert widget.entries[0].description == "Policy id для новых боев."

    async def test_combat_ai_active_policy_entry_gets_training_run_choices(self) -> None:
        config_payload = [
            {
                "key": "ACTIVE_POLICY_ID",
                "namespace": "combat_ai",
                "current": "training-1",
                "default": "",
                "value_type": "str",
                "is_modified": True,
            },
        ]
        runs_payload = {
            "runs": [
                {
                    "id": "training-1",
                    "run_kind": "training",
                    "scenario_key": "synthetic_policy_training",
                    "status": "completed",
                    "policy_ref": "candidate_not_activated",
                    "seed": 0,
                    "max_rounds": 60,
                    "rounds_completed": 60,
                    "winner": None,
                    "reward": 21.8,
                    "telemetry": {},
                    "report_text": "",
                    "metadata": {"best_policy": {"policy_id": "candidate_v1"}},
                    "created_at": "2026-05-29T16:34:03Z",
                }
            ]
        }

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/internal/config/combat_ai":
                return httpx.Response(200, content=json.dumps(config_payload).encode())
            if req.url.path == "/api/admin/combat-ai/simulation-runs":
                assert req.url.params["run_kind"] == "training"
                return httpx.Response(200, content=json.dumps(runs_payload).encode())
            return httpx.Response(404)

        request = _make_request(handler)
        provider = _config_provider(
            "combat_ai_cfg",
            "Поведение ИИ боя",
            "combat_ai",
            "/admin/game-settings/combat-ai",
        )
        widget = await provider(request)

        assert widget.entries[0].choices == [
            {"value": "", "label": "runtime default / env override"},
            {"value": "training-1", "label": "2026-05-29T16:34 | reward 21.800 | candidate_v1"},
        ]


class TestAdminDeclaration:
    def test_sidebar_lists_expected_keys(self) -> None:
        keys = {item.key for item in GameSettingsAdmin.sidebar}
        assert keys == {"combat", "combat_ai", "scenario", "exploration", "streams", "workers"}

    def test_sidebar_names_combat_ai_as_behavior_settings(self) -> None:
        labels = {item.key: item.label for item in GameSettingsAdmin.sidebar}
        assert labels["combat_ai"] == "Поведение ИИ боя"

    def test_sub_pages_register_editable_widgets_for_four_namespaces(self) -> None:
        for ns in ("combat", "combat-ai", "scenario", "exploration"):
            widgets = GameSettingsAdmin.sub_pages[ns]
            assert any(w.kind == "editable_config" for w in widgets), f"{ns} missing editable_config widget"

    def test_providers_registered_for_each_namespace(self) -> None:
        providers = GameSettingsAdmin.providers
        for ns in ("combat", "combat_ai", "scenario", "exploration"):
            assert f"game_settings.{ns}" in providers


class TestActions:
    async def test_handle_update_config_redirects_after_patch(self) -> None:
        calls: list[httpx.Request] = []

        def handler(req: httpx.Request) -> httpx.Response:
            calls.append(req)
            return httpx.Response(200, json={"namespace": "combat", "key": "K", "value": "1"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            app = SimpleNamespace(state=SimpleNamespace(backend_http_client=http))
            scope = {
                "type": "http",
                "method": "POST",
                "app": app,
                "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
                "query_string": b"",
                "server": ("testserver", 80),
                "scheme": "http",
                "client": ("testclient", 50000),
                "path": "/admin/game-settings/update-config",
            }
            body = (
                b"namespace=combat&redirect_to=/admin/game-settings/combat"
                b"&values[PARRY_SKILL_MULT_PER_POINT]=7.0"
            )

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            request = Request(scope, receive=receive)
            response = await GameSettingsAdmin().handle_update_config(request)

        assert response.status_code == 303
        assert response.headers["location"] == "/admin/game-settings/combat"
        assert len(calls) == 1
        assert calls[0].method == "PATCH"
        assert calls[0].url.path == "/api/internal/config/combat/PARRY_SKILL_MULT_PER_POINT"  # pragma: allowlist secret

    async def test_handle_reset_config_redirects_after_delete(self) -> None:
        calls: list[httpx.Request] = []

        def handler(req: httpx.Request) -> httpx.Response:
            calls.append(req)
            return httpx.Response(200, json={"reset": True})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            app = SimpleNamespace(state=SimpleNamespace(backend_http_client=http))
            scope = {
                "type": "http",
                "method": "POST",
                "app": app,
                "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
                "query_string": b"",
                "server": ("testserver", 80),
                "scheme": "http",
                "client": ("testclient", 50000),
                "path": "/admin/game-settings/reset-config",
            }
            body = (
                b"namespace=combat&key=PARRY_SKILL_MULT_PER_POINT"
                b"&redirect_to=/admin/game-settings/combat"
            )

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            request = Request(scope, receive=receive)
            response = await GameSettingsAdmin().handle_reset_config(request)

        assert response.status_code == 303
        assert response.headers["location"] == "/admin/game-settings/combat"
        assert calls[0].method == "DELETE"
        assert calls[0].url.path == "/api/internal/config/combat/PARRY_SKILL_MULT_PER_POINT"  # pragma: allowlist secret

    async def test_handle_reset_namespace_redirects_after_namespace_delete(self) -> None:
        calls: list[httpx.Request] = []

        def handler(req: httpx.Request) -> httpx.Response:
            calls.append(req)
            return httpx.Response(200, json={"namespace": "combat", "reset": True})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            app = SimpleNamespace(state=SimpleNamespace(backend_http_client=http))
            scope = {
                "type": "http",
                "method": "POST",
                "app": app,
                "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
                "query_string": b"",
                "server": ("testserver", 80),
                "scheme": "http",
                "client": ("testclient", 50000),
                "path": "/admin/game-settings/reset-namespace",
            }
            body = b"namespace=combat&redirect_to=/admin/game-settings/combat"

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            request = Request(scope, receive=receive)
            response = await GameSettingsAdmin().handle_reset_namespace(request)

        assert response.status_code == 303
        assert response.headers["location"] == "/admin/game-settings/combat"
        assert len(calls) == 1
        assert calls[0].method == "DELETE"
        assert calls[0].url.path == "/api/internal/config/combat"

    async def test_handle_update_config_dedupes_repeated_keys_keeping_last(self) -> None:
        """Bool checkbox renders a hidden 'false' before a 'true' value;
        dedupe keeps the last occurrence so only one PATCH is issued per key."""
        calls: list[httpx.Request] = []

        def handler(req: httpx.Request) -> httpx.Response:
            calls.append(req)
            return httpx.Response(200, json={"value": "ok"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            app = SimpleNamespace(state=SimpleNamespace(backend_http_client=http))
            scope = {
                "type": "http",
                "method": "POST",
                "app": app,
                "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
                "query_string": b"",
                "server": ("testserver", 80),
                "scheme": "http",
                "client": ("testclient", 50000),
                "path": "/admin/game-settings/update-config",
            }
            body = (
                b"namespace=combat&redirect_to=/admin/game-settings/combat"
                b"&values[ENABLE_X]=false"
                b"&values[ENABLE_X]=true"
            )

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            request = Request(scope, receive=receive)
            response = await GameSettingsAdmin().handle_update_config(request)

        assert response.status_code == 303
        assert len(calls) == 1
        sent_body = json.loads(calls[0].content.decode("utf-8"))
        assert sent_body == {"value": "true"}

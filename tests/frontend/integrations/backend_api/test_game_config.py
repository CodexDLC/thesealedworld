from __future__ import annotations

import json

import httpx
import pytest

from src.frontend.integrations.backend_api.game_config import ConfigEntryDTO, GameConfigApi

BASE_URL = "http://backend.test"


def _entry_payload(**overrides: object) -> dict:
    base: dict = {
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
    }
    base.update(overrides)
    return base


class TestConfigEntryDTO:
    def test_from_dict_parses_full_payload(self) -> None:
        dto = ConfigEntryDTO.from_dict(_entry_payload())
        assert dto.key == "PARRY_SKILL_MULT_PER_POINT"
        assert dto.current == "7.0"
        assert dto.default == "4.0"
        assert dto.value_type == "float"
        assert dto.is_modified is True
        assert dto.label == "Множитель навыка парирования"
        assert dto.description == "Усиливает шанс парирования от навыка."
        assert dto.group == "Парирование и щит"
        assert dto.unit == "multiplier"
        assert dto.min_value == 0.0
        assert dto.max_value == 10.0
        assert dto.step == 0.1
        assert dto.risk == "medium"
        assert dto.live_scope == "new_exchange"
        assert dto.tags == ["combat", "balance"]

    def test_from_dict_supplies_safe_fallbacks(self) -> None:
        dto = ConfigEntryDTO.from_dict({"key": "K", "namespace": "ns", "current": "c", "default": "d"})
        assert dto.value_type == "str"
        assert dto.is_modified is False
        assert dto.label is None
        assert dto.tags == []


class TestGameConfigApi:
    @pytest.fixture()
    def captured(self) -> dict[str, httpx.Request | None]:
        return {"last": None}

    def _client_for(
        self,
        captured: dict[str, httpx.Request | None],
        payload: list | dict | None,
        *,
        status_code: int = 200,
    ) -> httpx.AsyncClient:
        def handler(request: httpx.Request) -> httpx.Response:
            captured["last"] = request
            if payload is None or status_code == 204:
                return httpx.Response(status_code, content=b"")
            return httpx.Response(status_code, content=json.dumps(payload).encode("utf-8"))

        transport = httpx.MockTransport(handler)
        return httpx.AsyncClient(transport=transport)

    async def test_list_namespace_parses_raw_list(self, captured: dict[str, httpx.Request | None]) -> None:
        async with self._client_for(captured, [_entry_payload()]) as http:
            api = GameConfigApi(client=http, base_url=BASE_URL)
            entries = await api.list_namespace("combat")

        assert len(entries) == 1
        assert entries[0].key == "PARRY_SKILL_MULT_PER_POINT"
        assert entries[0].is_modified is True
        req = captured["last"]
        assert req is not None
        assert req.method == "GET"
        assert req.url.path == "/api/internal/config/combat"

    async def test_list_namespace_parses_wrapped_payload(self, captured: dict[str, httpx.Request | None]) -> None:
        # BaseApiClient._request wraps non-dict responses as {"data": ...}. Cover that path too.
        async with self._client_for(captured, {"data": [_entry_payload(), _entry_payload(key="OTHER")]}) as http:
            api = GameConfigApi(client=http, base_url=BASE_URL)
            entries = await api.list_namespace("combat")

        assert [e.key for e in entries] == ["PARRY_SKILL_MULT_PER_POINT", "OTHER"]

    async def test_list_namespace_handles_unexpected_shape(self, captured: dict[str, httpx.Request | None]) -> None:
        async with self._client_for(captured, {"unexpected": "shape"}) as http:
            api = GameConfigApi(client=http, base_url=BASE_URL)
            entries = await api.list_namespace("combat")

        assert entries == []

    async def test_set_value_sends_patch_with_value_body(self, captured: dict[str, httpx.Request | None]) -> None:
        async with self._client_for(captured, {"namespace": "combat", "key": "K", "value": "7"}) as http:
            api = GameConfigApi(client=http, base_url=BASE_URL)
            await api.set_value("combat", "PARRY_SKILL_MULT_PER_POINT", "7.0")

        req = captured["last"]
        assert req is not None
        assert req.method == "PATCH"
        assert req.url.path == "/api/internal/config/combat/PARRY_SKILL_MULT_PER_POINT"  # pragma: allowlist secret
        assert json.loads(req.content) == {"value": "7.0"}

    async def test_reset_key_sends_delete(self, captured: dict[str, httpx.Request | None]) -> None:
        async with self._client_for(captured, {"reset": True}) as http:
            api = GameConfigApi(client=http, base_url=BASE_URL)
            await api.reset_key("combat", "PARRY_SKILL_MULT_PER_POINT")

        req = captured["last"]
        assert req is not None
        assert req.method == "DELETE"
        assert req.url.path == "/api/internal/config/combat/PARRY_SKILL_MULT_PER_POINT"  # pragma: allowlist secret

    async def test_reset_namespace_sends_delete_at_namespace_path(
        self, captured: dict[str, httpx.Request | None]
    ) -> None:
        async with self._client_for(captured, {"namespace": "combat", "reset": True}) as http:
            api = GameConfigApi(client=http, base_url=BASE_URL)
            await api.reset_namespace("combat")

        req = captured["last"]
        assert req is not None
        assert req.method == "DELETE"
        assert req.url.path == "/api/internal/config/combat"

    async def test_internal_service_header_is_attached(self, captured: dict[str, httpx.Request | None]) -> None:
        async with self._client_for(captured, []) as http:
            api = GameConfigApi(
                client=http,
                base_url=BASE_URL,
                internal_service_key="test-key",  # pragma: allowlist secret
                internal_service_header="X-Test-Header",
            )
            await api.list_namespace("combat")

        req = captured["last"]
        assert req is not None
        assert req.headers["X-Test-Header"] == "test-key"

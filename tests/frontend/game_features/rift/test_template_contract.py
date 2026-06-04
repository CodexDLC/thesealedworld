from copy import deepcopy
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from starlette.responses import HTMLResponse

from src.frontend.config.settings import settings
from src.frontend.core.renderer import get_ui_renderer
from src.frontend.game_features.rift.dependencies import (
    get_backend_character_status_api,
    get_backend_inventory_api,
    get_backend_rift_api,
    get_backend_rift_dev_api,
)
from src.frontend.game_features.rift.view_models.screen import build_rift_context
from src.frontend.game_features.session.dependencies import get_session_context_builder
from src.shared.enums import CoreDomain


class _FakeRiftDevApi:
    def __init__(self) -> None:
        self.started = False
        self.start_request = None
        self.moved_to = None
        self.rebuilt = None
        self.travel_started_to = None
        self.travel_tick_request = None
        self.action_request = None

    async def start_starter_rift(self, *, seed=None, void_cells=None, assembly_preset_key=None):
        self.started = True
        self.start_request = {
            "seed": seed,
            "void_cells": void_cells,
            "assembly_preset_key": assembly_preset_key,
        }
        return _rift_payload()

    async def screen(self, rift_instance_id: str):
        payload = _rift_payload()
        payload["meta"]["rift_instance_id"] = rift_instance_id
        return payload

    async def move(self, rift_instance_id: str, *, target_node_id: str):
        self.moved_to = target_node_id
        payload = _rift_payload()
        payload["meta"]["rift_instance_id"] = rift_instance_id
        payload["current_node"]["node_id"] = target_node_id
        payload["current_node"]["title"] = "Коридор кабельных арок"
        return payload

    async def travel_start(self, rift_instance_id: str, *, target_node_id: str):
        self.travel_started_to = target_node_id
        return {
            "travel": {
                "travel_id": "trv-test-001",
                "status": "moving",
                "event_scope": "transition",
                "tick_result": "none",
                "from_node_id": "z01:2_2",
                "to_node_id": target_node_id,
                "kind": "exploration",
                "duration_ms": 3000,
                "tick_interval_ms": 1000,
                "checks_done": 0,
                "checks_total": 3,
                "remaining_ms": 3000,
                "possible_events": ["none", "combat"],
            },
            "combat_prompt": None,
            "screen": None,
        }

    async def travel_tick(self, rift_instance_id: str, *, travel_id: str, force_event: str | None = None):
        self.travel_tick_request = {
            "rift_instance_id": rift_instance_id,
            "travel_id": travel_id,
            "force_event": force_event,
        }
        if force_event == "combat":
            return {
                "travel": {
                    "travel_id": travel_id,
                    "status": "interrupted",
                    "event_scope": "transition",
                    "tick_result": "combat",
                    "from_node_id": "z01:2_2",
                    "to_node_id": "z01:2_1",
                    "kind": "exploration",
                    "duration_ms": 3000,
                    "tick_interval_ms": 1000,
                    "checks_done": 1,
                    "checks_total": 3,
                    "remaining_ms": 2000,
                    "possible_events": ["none", "combat"],
                },
                "combat_prompt": {
                    "source": "rift_transition",
                    "title": "Перехват в переходе",
                    "description": "Серый шум собирается в силуэт.",
                    "enemies": [
                        {
                            "name": "???",
                            "tier": 0,
                            "threat_rating": None,
                            "hp_percent": None,
                            "image": None,
                            "visual": {},
                            "description": "Силуэт угрозы еще не различим в серой пыли перехода.",
                        }
                    ],
                    "actions": [
                        {
                            "id": "attack",
                            "label": "В бой!",
                            "action": "attack",
                            "style": "danger",
                            "is_active": True,
                        }
                    ],
                    "metadata": {
                        "travel_id": travel_id,
                        "rift_instance_id": rift_instance_id,
                        "from_node_id": "z01:2_2",
                        "to_node_id": "z01:2_1",
                        "event_scope": "transition",
                        "combat": {"status": "placeholder", "combat_id": None},
                    },
                },
                "screen": None,
            }

        screen = _rift_payload()
        screen["meta"]["rift_instance_id"] = rift_instance_id
        screen["current_node"]["node_id"] = "z01:2_1"
        screen["current_node"]["title"] = "Коридор кабельных арок"
        return {
            "travel": {
                "travel_id": travel_id,
                "status": "completed",
                "event_scope": "transition",
                "tick_result": "none",
                "from_node_id": "z01:2_2",
                "to_node_id": "z01:2_1",
                "kind": "exploration",
                "duration_ms": 3000,
                "tick_interval_ms": 1000,
                "checks_done": 3,
                "checks_total": 3,
                "remaining_ms": 0,
                "possible_events": ["none", "combat"],
            },
            "combat_prompt": None,
            "screen": screen,
        }

    async def action(
        self,
        rift_instance_id: str,
        *,
        action_type: str,
        action_id: str | None = None,
        target_node_id: str | None = None,
        direction: str | None = None,
        payload: dict | None = None,
    ):
        self.action_request = {
            "rift_instance_id": rift_instance_id,
            "action_type": action_type,
            "action_id": action_id,
            "target_node_id": target_node_id,
            "direction": direction,
            "payload": payload or {},
        }
        screen = _rift_payload()
        screen["meta"]["rift_instance_id"] = rift_instance_id
        if action_type == "resolve_node_event":
            screen["current_node"]["node_id"] = "z02:0_2"
            screen["current_node"]["title"] = "Старт второго уровня"
            message = "Node guard combat resolved. Active rift zone switched to the next prepared zone."
        elif action_type == "resolve_blocker":
            screen["current_node"]["title"] = "Решетка открыта"
            message = "Temporary blocker opened."
        elif action_type == "resolve_heart":
            screen["current_node"]["node_id"] = "z01:9_9"
            screen["current_node"]["title"] = "Сердце разрушено"
            screen["current_node"]["tags"] = ["rift_heart", "black_crystal", "objective"]
            screen["heart"]["status"] = "shattered"
            screen["heart"]["resolved_method"] = "shatter"
            screen["heart"]["is_current_node"] = True
            screen["heart"]["can_exit"] = True
            screen["heart"]["reward"] = {
                "lost_value": 50,
                "symbiote_xp": 25,
                "resource_value": 25,
                "resource_template_id": "currency_dust",
            }
            screen["exit"] = {
                "mode": "heart_exit_only",
                "can_complete": True,
                "actions": [
                    {
                        "action": "complete_rift",
                        "label": "Выбраться из разлома",
                        "style": "primary",
                        "is_active": True,
                    }
                ],
            }
            message = "Rift heart shattered. The rift can now be closed."
        else:
            screen["current_node"]["node_id"] = "z01:2_1"
            screen["current_node"]["title"] = "Коридор кабельных арок"
            screen["last_travel"] = {
                "from_node_id": "z01:2_2",
                "to_node_id": "z01:2_1",
                "kind": "exploration",
                "duration_ms": 3000,
                "event_scope": "transition",
                "event_triggered": True,
                "event_type": "combat",
                "resolved": True,
                "result": "victory",
                "suppress_random_node_combat": True,
            }
            message = "Transition combat placeholder resolved. Travel completed into the target node."
        return {
            "action_type": action_type,
            "result": "victory",
            "message": message,
            "details": {},
            "granted_flags": ["rift_flag:zone:z01:next_zone_guard_cleared"],
            "screen": screen,
        }

    async def rebuild(self, rift_instance_id: str, *, seed=None, void_cells=None):
        self.rebuilt = {
            "rift_instance_id": rift_instance_id,
            "seed": seed,
            "void_cells": void_cells,
        }
        payload = _rift_payload()
        payload["meta"]["rift_instance_id"] = rift_instance_id
        payload["current_node"]["title"] = "Пересобранный разлом"
        return payload


class _FakeRiftApi:
    def __init__(self) -> None:
        self.travel_tick_request = None
        self.complete_request = None

    async def view(self, token: str, *, char_id: int):
        return _rift_payload()

    async def travel_start(self, token: str, *, char_id: int, target_node_id: str):
        return {"travel": None, "combat_prompt": None, "screen": None}

    async def travel_tick(self, token: str, *, char_id: int, travel_id: str, force_event: str | None = None):
        self.travel_tick_request = {
            "token": token,
            "char_id": char_id,
            "travel_id": travel_id,
            "force_event": force_event,
        }
        screen = _rift_payload()
        screen["current_node"]["node_id"] = "z01:2_1"
        screen["current_node"]["title"] = "Коридор кабельных арок"
        return {
            "travel": {"travel_id": travel_id, "status": "completed"},
            "combat_prompt": None,
            "screen": screen,
        }

    async def action(
        self,
        token: str,
        *,
        char_id: int,
        action_type: str,
        action_id: str | None = None,
        target_node_id: str | None = None,
        direction: str | None = None,
        payload: dict | None = None,
    ):
        screen = _rift_payload()
        screen["current_node"]["title"] = "Решенный переход"
        return {
            "action_type": action_type,
            "result": "victory",
            "message": "ok",
            "details": {},
            "granted_flags": [],
            "screen": screen,
        }

    async def complete(self, token: str, *, char_id: int):
        self.complete_request = {
            "token": token,
            "char_id": char_id,
        }
        return {
            "result": "success",
            "action": "complete_rift",
            "target_state": "exploration",
            "location_id": "52_52",
            "rift_session_id": "rift:run:test",
            "rift_instance_id": "runtime-rift-001",
            "exit_reason": "completed",
            "details": {
                "symbiote_reward": {"gift_xp": 25},
            },
        }


class _FakeCharacterStatusApi:
    async def get_panel(self, token: str, *, char_id: int):
        return {
            "char_id": char_id,
            "state": "RIFT",
            "bio": {"name": "Codexen", "avatar": "/static/images/test-avatar.webp"},
            "vitals": {
                "hp": {"cur": 59, "max": 59},
                "energy": {"cur": 25, "max": 25},
                "stamina": {"cur": 120, "max": 120},
            },
            "attributes": {"strength": 17},
            "skills": {"skill_tactics": {"xp": 0.1}},
            "metrics": {"gear_score": 284},
            "symbiote": {"name": "SYSTEM"},
            "sessions": {"inventory_id": "inv-1"},
        }


class _FakeInventoryApi:
    async def view(self, token: str, *, char_id: int, tab: str = "items"):
        class _Response:
            payload = {
                "tabs": [],
                "active_tab": "items",
                "layout": {"columns": 12, "cell_px": 34},
                "sections": [],
                "character": {"name": "Codexen"},
            }

        return _Response()


class _FakeSessionContextBuilder:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def build(self, request, *, state, char_id: int, quest_key=None, transition_context=None, transition_metadata=None):
        self.calls.append(
            {
                "state": state,
                "char_id": char_id,
                "quest_key": quest_key,
                "transition_context": transition_context,
                "transition_metadata": transition_metadata,
            }
        )
        return {
            "domain": state,
            "char_id": char_id,
            "payload_type": "CombatDashboard",
            "combat": {},
            "combat_screen": {"session_id": "combat-rift-1"},
            "combat_outcome_screen": None,
            "nav": {},
            "status_seed": {"char_id": char_id},
        }


class _FakeRenderer:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def render(self, template: str, *, context: dict, status_code: int = 200):
        self.calls.append({"template": template, "context": context, "status_code": status_code})
        return HTMLResponse(
            f'<div id="game-session-root" data-game-state="{context["domain"]}"></div>',
            status_code=status_code,
        )


def test_test_rift_route_renders_game_shell(client) -> None:
    client.app.dependency_overrides[get_backend_rift_dev_api] = _FakeRiftDevApi

    response = client.get("/testrift?rift_instance_id=dev-rift-001")

    assert response.status_code == 200
    assert "Вход у разбитой вехи" in response.text
    assert "Переходы" in response.text
    assert 'data-domain="rift"' in response.text
    assert 'data-game-state="rift"' in response.text
    assert "/static/js/game/states/rift.js?v=" in response.text


def test_test_rift_route_redirects_initial_start_to_instance_url(client) -> None:
    client.app.dependency_overrides[get_backend_rift_dev_api] = _FakeRiftDevApi

    response = client.get("/testrift", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/testrift?rift_instance_id=dev-rift-001"


def test_test_rift_route_can_start_two_level_chain_preset(client) -> None:
    fake_api = _FakeRiftDevApi()
    client.app.dependency_overrides[get_backend_rift_dev_api] = lambda: fake_api

    response = client.get(
        "/testrift?assembly_preset_key=chain_2x_grid_4x4_active_12",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert fake_api.start_request == {
        "seed": None,
        "void_cells": None,
        "assembly_preset_key": "chain_2x_grid_4x4_active_12",
    }
    assert (
        response.headers["location"]
        == "/testrift?rift_instance_id=dev-rift-001&assembly_preset_key=chain_2x_grid_4x4_active_12"
    )


def test_test_rift_route_returns_404_when_dev_rift_disabled(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_dev_rift_routes", False)
    client.app.dependency_overrides[get_backend_rift_dev_api] = _FakeRiftDevApi

    response = client.get("/testrift?rift_instance_id=dev-rift-001")

    assert response.status_code == 404


def test_rift_move_route_updates_session_root(client) -> None:
    fake_api = _FakeRiftDevApi()
    client.app.dependency_overrides[get_backend_rift_dev_api] = lambda: fake_api

    response = client.post(
        "/game/rift/move",
        data={"rift_instance_id": "dev-rift-001", "target_node_id": "z01:2_1"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert fake_api.moved_to == "z01:2_1"
    assert 'id="game-session-root"' in response.text
    assert 'data-game-state="rift"' in response.text
    assert "/static/js/game/states/rift.js?v=" in response.text
    assert "Коридор кабельных арок" in response.text
    assert "Rift tester" in response.text
    assert "INVENTORY_VIEW_MODEL_MISSING" not in response.text


def test_rift_travel_start_route_returns_travel_json(client) -> None:
    fake_api = _FakeRiftDevApi()
    client.app.dependency_overrides[get_backend_rift_dev_api] = lambda: fake_api

    response = client.post(
        "/game/rift/travel/start",
        data={"rift_instance_id": "dev-rift-001", "target_node_id": "z01:2_1"},
    )

    assert response.status_code == 200
    assert fake_api.travel_started_to == "z01:2_1"
    payload = response.json()
    assert payload["travel"]["travel_id"] == "trv-test-001"
    assert payload["travel"]["status"] == "moving"
    assert payload["combat_prompt"] is None
    assert payload["html"] is None


def test_rift_travel_tick_route_returns_combat_prompt_json(client) -> None:
    fake_api = _FakeRiftDevApi()
    client.app.dependency_overrides[get_backend_rift_dev_api] = lambda: fake_api

    response = client.post(
        "/game/rift/travel/tick",
        data={"rift_instance_id": "dev-rift-001", "travel_id": "trv-test-001", "force_event": "combat"},
    )

    assert response.status_code == 200
    assert fake_api.travel_tick_request == {
        "rift_instance_id": "dev-rift-001",
        "travel_id": "trv-test-001",
        "force_event": "combat",
    }
    payload = response.json()
    assert payload["travel"]["status"] == "interrupted"
    assert payload["combat_prompt"]["source"] == "rift_transition"
    assert payload["combat_prompt"]["enemies"][0]["name"] == "???"
    assert payload["combat_prompt"]["actions"][0]["action"] == "attack"
    assert payload["combat_prompt"]["metadata"]["combat"]["status"] == "placeholder"
    assert payload["html"] is None


def test_rift_travel_tick_route_returns_completed_screen_html(client) -> None:
    fake_api = _FakeRiftDevApi()
    client.app.dependency_overrides[get_backend_rift_dev_api] = lambda: fake_api

    response = client.post(
        "/game/rift/travel/tick",
        data={"rift_instance_id": "dev-rift-001", "travel_id": "trv-test-001"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["travel"]["status"] == "completed"
    assert payload["combat_prompt"] is None
    assert 'id="game-session-root"' in payload["html"]
    assert 'data-game-state="rift"' in payload["html"]
    assert "Коридор кабельных арок" in payload["html"]
    assert "Rift tester" in payload["html"]
    assert "INVENTORY_VIEW_MODEL_MISSING" not in payload["html"]


def test_rift_travel_tick_for_character_preserves_status_and_inventory(client) -> None:
    fake_api = _FakeRiftApi()
    client.app.dependency_overrides[get_backend_rift_api] = lambda: fake_api
    client.app.dependency_overrides[get_backend_character_status_api] = _FakeCharacterStatusApi
    client.app.dependency_overrides[get_backend_inventory_api] = _FakeInventoryApi
    client.cookies.set("tbmmorpg_game_access_token", "game-token")

    response = client.post(
        "/game/rift/travel/tick",
        data={
            "rift_instance_id": "runtime-rift-001",
            "travel_id": "trv-test-001",
            "char_id": "4",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert fake_api.travel_tick_request == {
        "token": "game-token",
        "char_id": 4,
        "travel_id": "trv-test-001",
        "force_event": None,
    }
    assert "Codexen" in payload["html"]
    assert "284" in payload["html"]
    assert "INVENTORY_VIEW_MODEL_MISSING" not in payload["html"]


def test_rift_action_route_resolves_transition_combat_as_json(client) -> None:
    fake_api = _FakeRiftDevApi()
    client.app.dependency_overrides[get_backend_rift_dev_api] = lambda: fake_api

    response = client.post(
        "/game/rift/action",
        data={
            "rift_instance_id": "dev-rift-001",
            "action_type": "resolve_transition_combat",
            "travel_id": "trv-test-001",
            "result": "victory",
        },
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 200
    assert fake_api.action_request == {
        "rift_instance_id": "dev-rift-001",
        "action_type": "resolve_transition_combat",
        "action_id": None,
        "target_node_id": None,
        "direction": None,
        "payload": {"travel_id": "trv-test-001", "result": "victory"},
    }
    payload = response.json()
    assert payload["action_type"] == "resolve_transition_combat"
    assert payload["result"] == "victory"
    assert payload["message"]
    assert 'id="game-session-root"' in payload["html"]
    assert 'data-game-state="rift"' in payload["html"]
    assert "Коридор кабельных арок" in payload["html"]


def test_rift_combat_enter_route_renders_combat_fragment(client) -> None:
    fake_builder = _FakeSessionContextBuilder()
    fake_renderer = _FakeRenderer()
    client.app.dependency_overrides[get_session_context_builder] = lambda: fake_builder
    client.app.dependency_overrides[get_ui_renderer] = lambda: fake_renderer
    client.cookies.set("tbmmorpg_game_access_token", "game-token")

    response = client.post(
        "/game/rift/combat/enter",
        data={"char_id": "4", "combat_id": "combat-rift-1"},
    )

    assert response.status_code == 200
    assert fake_renderer.calls[0]["template"] == "game/session_content_inner.html"
    assert fake_builder.calls == [
        {
            "state": "combats",
            "char_id": 4,
            "quest_key": None,
            "transition_context": None,
            "transition_metadata": {"combat_id": "combat-rift-1", "source": "rift"},
        }
    ]
    assert 'id="game-session-root"' in response.text
    assert 'data-game-state="combats"' in response.text


def test_rift_complete_route_returns_target_session_shell(client) -> None:
    fake_api = _FakeRiftApi()
    fake_builder = _FakeSessionContextBuilder()
    fake_renderer = _FakeRenderer()
    client.app.dependency_overrides[get_backend_rift_api] = lambda: fake_api
    client.app.dependency_overrides[get_session_context_builder] = lambda: fake_builder
    client.app.dependency_overrides[get_ui_renderer] = lambda: fake_renderer
    client.cookies.set("tbmmorpg_game_access_token", "game-token")

    response = client.post(
        "/game/rift/complete",
        data={"char_id": "4"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert fake_api.complete_request == {
        "token": "game-token",
        "char_id": 4,
    }
    assert fake_renderer.calls[0]["template"] == "game/session_content_inner.html"
    assert fake_builder.calls[0]["state"] == CoreDomain.EXPLORATION
    assert fake_builder.calls[0]["char_id"] == 4
    assert fake_builder.calls[0]["transition_metadata"]["source"] == "rift"
    assert fake_builder.calls[0]["transition_metadata"]["rift_exit"]["exit_reason"] == "completed"
    assert 'id="game-session-root"' in response.text
    assert 'data-game-state="exploration"' in response.text


def test_rift_action_route_switches_screen_for_node_event(client) -> None:
    fake_api = _FakeRiftDevApi()
    client.app.dependency_overrides[get_backend_rift_dev_api] = lambda: fake_api

    response = client.post(
        "/game/rift/action",
        data={
            "rift_instance_id": "dev-rift-001",
            "action_type": "resolve_node_event",
            "event_key": "next_zone_guard",
            "result": "victory",
        },
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert fake_api.action_request == {
        "rift_instance_id": "dev-rift-001",
        "action_type": "resolve_node_event",
        "action_id": None,
        "target_node_id": None,
        "direction": None,
        "payload": {"result": "victory", "event_key": "next_zone_guard"},
    }
    assert 'id="game-session-root"' in response.text
    assert 'data-game-state="rift"' in response.text
    assert "Старт второго уровня" in response.text


def test_rift_action_route_resolves_blocker(client) -> None:
    fake_api = _FakeRiftDevApi()
    client.app.dependency_overrides[get_backend_rift_dev_api] = lambda: fake_api

    response = client.post(
        "/game/rift/action",
        data={
            "rift_instance_id": "dev-rift-001",
            "action_type": "resolve_blocker",
            "target_node_id": "z01:1_2",
            "direction": "west",
        },
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert fake_api.action_request == {
        "rift_instance_id": "dev-rift-001",
        "action_type": "resolve_blocker",
        "action_id": None,
        "target_node_id": "z01:1_2",
        "direction": "west",
        "payload": {"result": "victory"},
    }
    assert 'id="game-session-root"' in response.text
    assert 'data-game-state="rift"' in response.text
    assert "Решетка открыта" in response.text


def test_rift_action_route_resolves_heart(client) -> None:
    fake_api = _FakeRiftDevApi()
    client.app.dependency_overrides[get_backend_rift_dev_api] = lambda: fake_api

    response = client.post(
        "/game/rift/action",
        data={
            "rift_instance_id": "dev-rift-001",
            "action_type": "resolve_heart",
            "action_id": "shatter",
        },
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert fake_api.action_request == {
        "rift_instance_id": "dev-rift-001",
        "action_type": "resolve_heart",
        "action_id": "shatter",
        "target_node_id": None,
        "direction": None,
        "payload": {"result": "victory"},
    }
    assert 'id="game-session-root"' in response.text
    assert 'data-game-state="rift"' in response.text
    assert "Сердце разрушено" in response.text
    assert "Лабиринт потерял устойчивость" in response.text
    assert "Осколочная пыль" in response.text


def test_rift_rebuild_route_updates_session_root(client) -> None:
    fake_api = _FakeRiftDevApi()
    client.app.dependency_overrides[get_backend_rift_dev_api] = lambda: fake_api

    response = client.post(
        "/game/rift/rebuild",
        data={"rift_instance_id": "dev-rift-001", "seed": "manual-reset", "void_cells": "7"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert fake_api.rebuilt == {
        "rift_instance_id": "dev-rift-001",
        "seed": "manual-reset",
        "void_cells": 7,
    }
    assert 'id="game-session-root"' in response.text
    assert 'data-game-state="rift"' in response.text
    assert "/static/js/game/states/rift.js?v=" in response.text
    assert "Пересобранный разлом" in response.text


def test_game_base_loads_shared_game_bundle_before_alpine() -> None:
    base_template = Path("src/frontend/templates/game/base_game.html").read_text(encoding="utf-8")

    assert '/static/js/game.js?v={{ static_version }}' in base_template
    assert base_template.index('/static/js/game.js') < base_template.index('/static/js/vendor/alpine.js')


def test_rift_template_uses_session_shell_slots() -> None:
    session_template = Path("src/frontend/templates/game/session_content_inner.html").read_text(encoding="utf-8")
    page_template = Path("src/frontend/templates/game/testrift.html").read_text(encoding="utf-8")
    viewport_template = Path("src/frontend/templates/game/domains/rift/viewport/main.html").read_text(encoding="utf-8")
    right_template = Path("src/frontend/templates/game/domains/rift/right_sidebar/main.html").read_text(encoding="utf-8")

    assert 'extends "game/base_game.html"' in page_template
    assert 'include "game/session_content_inner.html"' in page_template
    assert "domain == 'rift'" in session_template
    assert "game/domains/rift/viewport/main.html" in session_template
    assert 'include "game/components/status/main.html"' in session_template
    assert "game/domains/rift/left_sidebar/main.html" not in session_template
    assert not Path("src/frontend/templates/game/domains/rift/left_sidebar/main.html").exists()
    assert "game/domains/rift/right_sidebar/main.html" in session_template
    assert "data-game-state" in session_template
    assert "data-game-scripts" in session_template
    assert "versioned_game_scripts" in session_template
    assert "'v=' ~ static_version" in session_template
    assert "rift.current_node" in viewport_template
    assert "rift.surroundings" in viewport_template
    assert "rift-surroundings-copy" in viewport_template
    assert "rift-surrounding-line" not in viewport_template
    assert "rift.movement" in viewport_template
    assert "map_view.visible_nodes" in viewport_template
    assert "map_view.visible_edges" in viewport_template
    assert "heading_rotation" in viewport_template
    assert "--rift-current-marker-rotation" in viewport_template
    assert "rift-node-art" not in viewport_template
    assert "rift-radar-cross" not in viewport_template
    assert "game-action-panel game-action-panel--bottom rift-action-panel" in viewport_template
    assert 'hx-post="/game/rift/move"' in viewport_template
    assert 'hx-post="/game/rift/action"' in viewport_template
    assert "hx-push-url" not in viewport_template
    assert 'action_type="resolve_node_event"' not in viewport_template
    assert 'action_type="resolve_blocker"' in viewport_template
    assert 'hx-target="#game-session-root"' in viewport_template
    assert "rift.meta.rift_instance_id" in viewport_template
    assert "data-rift-map-scope-id" in viewport_template
    assert "RiftMapStore.merge" not in viewport_template
    assert "rift.map_view|tojson" in viewport_template
    assert "data-rift-map-canvas" in viewport_template
    assert 'hx-post="/game/rift/rebuild"' not in viewport_template
    assert "data-rift-reset-map" not in viewport_template
    assert "data-tippy-content" in viewport_template
    assert 'data-tippy-theme="game-hint"' in viewport_template
    assert "data-rift-target" in viewport_template
    assert "rift-info-dock" in right_template
    assert "rift.hud.objective" in right_template
    assert "rift.debug_map" in right_template
    assert "rift-debug-map" in right_template
    assert 'hx-post="/game/rift/rebuild"' in right_template
    assert "data-rift-reset-map" in right_template
    assert "hx-push-url" not in right_template


def test_rift_template_renders_contract_payload() -> None:
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/rift/viewport/main.html")
    context = build_rift_context(_rift_payload())

    html = template.render(**context)

    assert "Вход у разбитой вехи" in html
    assert "Пойти прямо к просевшему тракту" in html
    assert 'data-rift-direction="forward"' in html
    assert 'data-rift-target="z01:2_1"' in html
    assert 'data-rift-instance-id="dev-rift-001"' in html
    assert 'data-rift-map-scope-id="dev-rift-001:zone-01"' in html
    assert 'data-rift-travel-start-url="/game/rift/travel/start"' in html
    assert 'data-rift-travel-tick-url="/game/rift/travel/tick"' in html
    assert 'data-rift-action-url="/game/rift/action"' in html
    assert 'data-rift-combat-enter-url="/game/rift/combat/enter"' in html
    assert "window.RiftMapStore.merge" not in html
    assert 'hx-post="/game/rift/move"' in html
    assert 'hx-post="/game/rift/action"' in html
    assert "hx-push-url" not in html
    assert '"rift_instance_id": "dev-rift-001"' in html
    assert '"target_node_id": "z01:2_1"' in html
    assert "is-state-void" not in html
    assert "Справа прохода нет" not in html
    assert "Рваный тракт" in html
    assert "rift-map-stage" in html
    assert "rift-surroundings-copy" in html
    assert "Впереди виден узкий коридор." in html
    assert "Справа зияет черный провал." in html
    assert "rift-surrounding-line" not in html
    assert "rift-travel-overlay" in html
    assert 'data-rift-travel-overlay' in html
    assert 'data-rift-combat-prompt' in html
    assert 'data-rift-combat-actions' in html
    combat_prompt_html = html[
        html.index('data-rift-combat-prompt') : html.index('data-rift-combat-actions')
    ]
    assert "mobile-encounter-interrupt" in combat_prompt_html
    assert "mobile-encounter-layout" in combat_prompt_html
    assert "mobile-encounter-roster" in combat_prompt_html
    assert "mobile-encounter-target-card" in combat_prompt_html
    assert "mobile-encounter-target-switcher" in combat_prompt_html
    assert "rift-encounter-panel" not in combat_prompt_html
    assert "rift-encounter-head" not in combat_prompt_html
    assert "rift-encounter-body" not in combat_prompt_html
    assert "rift-encounter-roster" not in combat_prompt_html
    assert "rift-encounter-detail" not in combat_prompt_html
    assert "PRIORITY INTERRUPT" in combat_prompt_html
    assert "ENCOUNTER DETECTED" in combat_prompt_html
    assert 'data-rift-combat-detail' in combat_prompt_html
    assert 'data-rift-combat-prompt-count' in combat_prompt_html
    assert 'data-rift-combat-enemies' in combat_prompt_html
    assert 'data-rift-combat-enemies' in html
    assert 'rift-combat-actions__body' in html
    assert 'data-rift-combat-action-grid' in html
    assert "rift-map-node is-state-current" in html
    assert "--rift-current-marker-rotation: 0deg" in html
    assert "rift-map-edge rift-map-edge--north is-state-open" in html
    assert "rift-map-edge rift-map-edge--east is-state-void" not in html
    assert "rift-map-edge rift-map-edge--west is-state-blocked_temporary" in html
    assert 'data-tippy-content="Коридор кабельных арок // открыта"' in html
    assert 'aria-label="Коридор кабельных арок"' in html
    assert 'style="--rift-node-dx: 0; --rift-node-dy: -1;"' in html
    assert 'data-rift-relative-direction="forward"' in html
    assert "rift-action-button--forward" in html
    assert "rift-action-button--back" in html
    assert "rift-action-button--right" not in html
    assert "rift-action-button--left" in html
    assert 'data-rift-travel-kind="exploration"' in html
    assert 'data-rift-travel-duration="3000"' in html
    assert 'data-rift-travel-tick-interval="1000"' in html
    assert 'data-rift-travel-check-count="3"' in html
    assert 'data-rift-travel-event-scope="transition"' in html
    assert 'data-rift-travel-possible-events=\'[&#34;none&#34;, &#34;combat&#34;]\'' in html
    assert 'data-rift-travel-can-trigger-event="true"' in html
    assert 'data-rift-travel-kind="return"' in html
    assert 'data-rift-travel-duration="1000"' in html
    assert "Разломать частокол" in html
    assert "Разломать частокол (Сила 15)" not in html
    assert "is-inspect-blocker" in html
    assert 'data-rift-blocker-key="jammed_service_gate"' in html
    assert 'data-rift-blocker-requirements="strength"' in html
    assert 'data-tippy-content="Требуется: Сила 15. У тебя: 16. Можно пройти."' in html
    assert "is-target-new" in html
    assert "is-target-visited" in html
    assert "rift-node-art" not in html
    assert "rift-radar-cross" not in html


def test_rift_template_renders_heart_action_on_current_heart_node() -> None:
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/rift/viewport/main.html")
    payload = deepcopy(_rift_payload())
    payload["current_node"]["node_id"] = "z01:9_9"
    payload["current_node"]["title"] = "Сердце рваного тракта"
    payload["current_node"]["tags"] = ["rift_heart", "black_crystal", "objective"]
    payload["movement"] = []
    payload["heart"] = {
        **payload["heart"],
        "node_id": "z01:9_9",
        "status": "intact",
        "is_current_node": True,
    }
    context = build_rift_context(payload)

    html = template.render(**context)

    assert "rift-heart-event" in html
    assert "data-rift-heart-state=\"choice\"" in html
    assert "Сердце разлома" in html
    assert "Выберите способ завершить сердце" in html
    assert "Разбить сердце" in html
    assert 'data-rift-action="resolve_heart"' in html
    assert '"action_type": "resolve_heart"' in html
    assert '"action_id": "shatter"' in html
    assert 'data-rift-heart-method="shatter"' in html
    assert 'data-rift-heart-method="absorb"' not in html
    assert 'data-rift-heart-method="dismantle"' not in html
    assert "Поглотить энергию" not in html
    assert "Демонтировать" not in html
    assert "not_unlocked" not in html
    assert "artifact_craft_required" not in html
    assert "rift-action-grid" in html
    assert "rift-heart-action-grid" in html


def test_rift_template_renders_heart_result_with_reward_and_exit_actions() -> None:
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/rift/viewport/main.html")
    payload = deepcopy(_rift_payload())
    payload["current_node"]["node_id"] = "z01:9_9"
    payload["current_node"]["title"] = "Сердце разрушено"
    payload["current_node"]["tags"] = ["rift_heart", "black_crystal", "objective"]
    payload["movement"] = deepcopy(_rift_payload()["movement"][:1])
    payload["heart"] = {
        **payload["heart"],
        "node_id": "z01:9_9",
        "status": "shattered",
        "resolved_method": "shatter",
        "is_current_node": True,
        "can_exit": True,
        "reward": {
            "lost_value": 50,
            "symbiote_xp": 25,
            "resource_value": 25,
            "resource_template_id": "currency_dust",
        },
    }
    payload["exit"] = {
        "mode": "heart_exit_only",
        "completion_exit": "from_heart",
        "can_leave": False,
        "can_complete": True,
        "actions": [{"action": "complete_rift", "label": "Выбраться из разлома", "style": "primary", "is_active": True}],
    }
    context = build_rift_context(payload, char_id=7)

    html = template.render(**context)

    assert "data-rift-heart-state=\"result\"" in html
    assert "Лабиринт потерял устойчивость" in html
    assert "Сердце рваного тракта ломается" in html
    assert "Опыт дара" in html
    assert "Опыт симбиота" not in html
    assert "+25" in html
    assert "Осколочная пыль" in html
    assert "currency_dust" in html
    assert "Продолжить путь" in html
    assert 'data-rift-dismiss-heart-result="true"' in html
    assert "Выбраться из разлома" in html
    assert 'hx-post="/game/rift/complete"' in html
    assert '"char_id": 7' in html


def test_rift_template_hides_exit_action_when_heart_requires_return_to_exit() -> None:
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/rift/viewport/main.html")
    payload = deepcopy(_rift_payload())
    payload["current_node"]["node_id"] = "z01:9_9"
    payload["current_node"]["title"] = "Сердце разрушено"
    payload["current_node"]["tags"] = ["rift_heart", "black_crystal", "objective"]
    payload["movement"] = deepcopy(_rift_payload()["movement"][:1])
    payload["heart"] = {
        **payload["heart"],
        "node_id": "z01:9_9",
        "status": "shattered",
        "resolved_method": "shatter",
        "is_current_node": True,
        "can_exit": True,
        "reward": {"symbiote_xp": 25},
    }
    payload["exit"] = {
        "mode": "heart_exit_only",
        "completion_exit": "return_to_exit",
        "exit_node_id": "z01:0_0",
        "can_leave": False,
        "can_complete": False,
        "reason": "return_to_exit_required",
        "actions": [],
    }
    context = build_rift_context(payload, char_id=7)

    html = template.render(**context)

    assert "Продолжить путь" in html
    assert "Выбраться из разлома" not in html
    assert 'hx-post="/game/rift/complete"' not in html


def test_rift_template_does_not_render_heart_action_on_non_heart_node() -> None:
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/rift/viewport/main.html")
    payload = deepcopy(_rift_payload())
    payload["current_node"]["node_id"] = "z01:2_2"
    payload["current_node"]["title"] = "Вход у разбитой вехи"
    payload["current_node"]["tags"] = ["road", "starter_rift"]
    payload["heart"] = {
        **payload["heart"],
        "node_id": "z01:2_2",
        "status": "intact",
        "is_current_node": True,
    }
    context = build_rift_context(payload)

    html = template.render(**context)

    assert 'data-rift-action="resolve_heart"' not in html
    assert "Разбить сердце" not in html


def test_rift_template_keeps_failed_blocker_clickable_for_feedback_modal() -> None:
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/rift/viewport/main.html")
    payload = deepcopy(_rift_payload())
    blocked = next(item for item in payload["movement"] if item["action"] == "inspect_blocker")
    blocked["style"] = "disabled"
    blocked["is_active"] = False
    blocked["tooltip"] = "Требуется: Сила 15. У тебя: 12. Не хватает: 3."
    blocked["debug_text_parts"]["check_result"] = {
        "key": "strength",
        "attribute_label": "Сила",
        "dc": 15,
        "current_known": True,
        "current_value": 12,
        "shortfall": 3,
        "can_pass": False,
    }
    context = build_rift_context(payload)

    html = template.render(**context)
    button_html = html[html.index('data-rift-action="inspect_blocker"') - 240 : html.index("Не хватает: 3.") + 80]

    assert 'data-rift-blocker-feedback="Требуется: Сила 15. У тебя: 12. Не хватает: 3."' in button_html
    assert 'aria-disabled="true"' in button_html
    assert 'disabled aria-disabled="true"' not in button_html
    assert 'hx-post="/game/rift/action"' not in button_html


def test_rift_right_sidebar_renders_full_debug_canvas_with_void_cells() -> None:
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/rift/right_sidebar/main.html")
    context = build_rift_context(_rift_payload())

    html = template.render(**context)

    assert "Стартовый разлом" in html
    assert "Рваный тракт" in html
    assert "Сердце не найдено" in html
    assert "HEART" in html
    assert "intact" in html
    assert "PARTY" in html
    assert "Current" in html
    assert "Вход у разбитой вехи" in html
    assert 'hx-post="/game/rift/rebuild"' in html
    assert "data-rift-reset-map" in html
    assert "hx-push-url" not in html
    assert "4x3" in html
    assert 'aria-label="4 by 3 rift zone debug map"' in html
    assert 'style="--rift-map-width: 4; --rift-map-height: 3;"' in html
    assert 'data-rift-cell="0,0"' in html
    assert "is-canvas-void" in html
    assert 'data-map-tooltip="VOID // 0:0"' in html
    assert 'data-rift-node-id="z01:0_0"' not in html
    assert ">0:0<" not in html
    assert 'data-rift-node-id="z01:2_2"' in html
    assert 'style="grid-column: 1; grid-row: 1;"' in html
    assert 'style="grid-column: 3; grid-row: 3;"' in html
    assert "rift-debug-edge rift-debug-edge--vertical is-state-open" in html
    assert "rift-debug-edge rift-debug-edge--horizontal is-state-blocked_temporary" in html
    assert "is-state-blocked_permanent" not in html
    assert "Preset" in html
    assert "grid_5x5_active_15" in html
    assert "Zone" in html
    assert "z01" in html
    assert "Depth" in html
    assert "1/2" in html
    assert "Chain" in html
    assert "z01 -&gt; z02" in html
    assert "Instance" in html
    assert "dev-rift-001:zone-01" in html


def test_rift_right_sidebar_keeps_player_view_free_of_debug_fields() -> None:
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/rift/right_sidebar/main.html")
    payload = deepcopy(_rift_payload())
    payload["meta"]["debug"] = False
    payload["corpse_ids"] = ["corpse-rat-1"]
    payload["loot_context"] = {
        "corpses": [
            {
                "corpse_id": "corpse-rat-1",
                "label": "Гнилозуб",
                "items": [{"name": "Сломанный клык"}],
            }
        ]
    }
    context = build_rift_context(payload, debug_enabled=False)

    html = template.render(**context)

    assert "Стартовый разлом" in html
    assert "Current" in html
    assert "Вход у разбитой вехи" in html
    assert "OBJECTIVE" in html
    assert "HEART" in html
    assert "LOOT" in html
    assert "Гнилозуб" in html
    assert "DEBUG MAP" not in html
    assert "PAYLOAD" not in html
    assert "Visible" not in html
    assert "Discovered" not in html
    assert "Visited" not in html
    assert "grid_5x5_active_15" not in html
    assert "dev-rift-001:zone-01" not in html
    assert "road" not in html
    assert "starter_rift" not in html


def test_rift_css_is_source_domain_import_only() -> None:
    bundle = Path("src/frontend/static/css/game_bundle.css").read_text(encoding="utf-8")
    index_css = Path("src/frontend/static/css/game/domains/rift/index.css").read_text(encoding="utf-8")
    screen_css = Path("src/frontend/static/css/game/domains/rift/screen.css").read_text(encoding="utf-8")
    encounter_css = Path("src/frontend/static/css/game/domains/exploration/encounters.css").read_text(encoding="utf-8")
    sidebars_css = Path("src/frontend/static/css/game/domains/rift/sidebars.css").read_text(encoding="utf-8")
    responsive_css = Path("src/frontend/static/css/game/domains/rift/responsive.css").read_text(encoding="utf-8")

    assert '@import url("game/domains/rift/index.css");' in bundle
    assert "game/domains/rift/screen.css" not in bundle
    assert '@import url("screen.css");' in index_css
    assert '@import url("sidebars.css");' in index_css
    assert '@import url("responsive.css");' in index_css
    assert ".rift-main-dock" in screen_css
    assert "width: min(100%, 460px)" in screen_css
    assert "justify-self: center" in screen_css
    assert "text-align: left" in screen_css
    assert 'grid-template-areas:' in screen_css
    assert '"left forward"' in screen_css
    assert '"back right"' in screen_css
    assert ".rift-action-button--left" in screen_css
    assert ".rift-action-button--forward" in screen_css
    assert ".rift-action-button--right" in screen_css
    assert ".rift-action-button--back" in screen_css
    assert ".rift-map-node.is-visited" in screen_css
    assert "/static/images/ui/rift-icons/orb-direction.svg" in screen_css
    assert ".rift-map-node.is-current > span::before" in screen_css
    assert "--rift-current-marker-rotation" in screen_css
    assert ".rift-node-copy .rift-surroundings-copy" in screen_css
    assert ".rift-node-copy[hidden]" in screen_css
    assert ".rift-center-screens.is-encounter-ready .rift-node-copy" in screen_css
    assert ".rift-surrounding-line" not in screen_css
    assert ".rift-map-node.is-state-blocked_temporary" in screen_css
    assert ".rift-map-edge.is-state-blocked_temporary" in screen_css
    assert ".rift-travel-overlay" in screen_css
    assert ".rift-travel-track" in screen_css
    assert ".rift-combat-prompt" in screen_css
    assert ".rift-center-screens.is-encounter-revealing .rift-node-copy" in screen_css
    assert ".rift-center-screens.is-encounter-ready .rift-node-copy" in screen_css
    assert ".rift-center-screens.is-encounter-revealing .rift-combat-prompt" in screen_css
    assert "@keyframes riftEncounterAssemble" in screen_css
    assert "@keyframes riftMapInterruptPulse" in screen_css
    assert ".rift-combat-prompt .mobile-encounter-layout" in screen_css
    assert ".rift-combat-prompt .mobile-encounter-interrupt" in screen_css
    assert "@media (min-width: 900px)" in screen_css
    assert ".rift-combat-prompt .mobile-encounter-layout {\n        width: min(100%, 860px);" in screen_css
    assert "grid-template-columns: 300px minmax(0, 1fr);" in screen_css
    assert ".rift-combat-prompt .mobile-encounter-roster {\n        grid-column: 1;" in screen_css
    assert ".rift-combat-prompt .mobile-encounter-target-card {\n        grid-column: 2;" in screen_css
    assert ".rift-combat-prompt .mobile-encounter-target-switcher {\n        display: none;" in screen_css
    assert "@media (max-width: 899px)" in screen_css
    assert ".rift-combat-prompt .mobile-encounter-roster {\n        display: none;" in screen_css
    assert ".rift-encounter-panel" not in screen_css
    assert ".rift-encounter-head" not in screen_css
    assert ".rift-encounter-body" not in screen_css
    assert ".rift-encounter-roster" not in screen_css
    assert ".rift-encounter-target" not in screen_css
    assert ".rift-encounter-detail" not in screen_css
    assert ".rift-encounter-target-detail" not in screen_css
    assert ".rift-encounter-target-art" not in screen_css
    assert ".mobile-encounter-target-art" in encounter_css
    assert "min-height: 66px" in encounter_css
    assert ".mobile-encounter-target-image" in screen_css
    assert "object-fit: cover" in screen_css
    assert ".mobile-encounter-target-image.is-family-fallback" in screen_css
    assert "object-fit: contain" in screen_css
    assert ".rift-combat-actions" in screen_css
    assert ".rift-combat-actions__body" in screen_css
    assert ".rift-combat-action-grid" in screen_css
    assert ".rift-combat-action-grid .mobile-encounter-action" in screen_css
    assert ".rift-center-screens.has-combat-prompt .rift-action-panel > .game-action-panel__head" in screen_css
    assert ".rift-center-screens.has-combat-prompt .rift-action-grid" in screen_css
    assert ".rift-action-button.is-travel-running" in screen_css
    assert ".rift-map-edge.is-state-void" not in screen_css
    assert ".rift-map-edge.is-state-blocked_permanent" not in screen_css
    assert "--rift-map-step: 112px" in screen_css
    assert ".rift-action-button.is-state-blocked_temporary:not(.is-disabled)" in screen_css
    assert ".rift-action-button.is-target-new" in screen_css
    assert ".rift-action-button.is-target-visited" in screen_css
    assert ".rift-action-grid" not in responsive_css
    assert ".game-screen-area--vertical" not in screen_css
    assert ".rift-info-dock" in sidebars_css
    assert ".rift-info-card" in sidebars_css
    assert ".rift-debug-reset" in sidebars_css
    assert ".rift-debug-map" in sidebars_css
    assert ".rift-debug-edge" in sidebars_css
    assert ".rift-debug-edge.is-state-blocked_temporary" in sidebars_css
    assert ".rift-debug-cell.is-canvas-void" in sidebars_css
    assert "20% 20%" not in sidebars_css
    assert "@media (max-width: 767px)" in responsive_css


def test_rift_compiled_css_contains_current_marker_icon() -> None:
    game_css = Path("src/frontend/static/css/game.css").read_text(encoding="utf-8")

    assert "/static/images/ui/rift-icons/orb-direction.svg" in game_css
    assert ".rift-map-node.is-current > span::before" in game_css
    assert "--rift-current-marker-rotation" in game_css


def test_rift_context_matches_draft_contract_shape() -> None:
    context = build_rift_context(_rift_payload())
    rift = context["rift"]

    assert context["domain"] == "rift"
    assert context["payload_type"] == "rift_screen"
    assert context["meta"]["robots"] == "noindex, nofollow"
    assert context["character_status"]["bio"]["name"] == "Rift tester"
    assert context["inventory_window"] is not None
    assert rift["meta"]["schema_version"] == 1
    assert rift["meta"]["current_zone_key"] == "z01"
    assert rift["meta"]["zone_depth"] == 1
    assert rift["meta"]["zone_chain_order"] == ["z01", "z02"]
    assert rift["meta"]["zone_chain_total"] == 2
    assert rift["current_node"]["coord"] == {"x": 2, "y": 2}
    assert {action["relative_direction"] for action in rift["movement"]} == {"forward", "back", "right", "left"}
    assert len(rift["radar"]["arms"]) == 4
    assert rift["debug_map"]["width"] == 4
    assert rift["debug_map"]["height"] == 3
    assert len(rift["debug_map"]["cells"]) == rift["debug_map"]["width"] * rift["debug_map"]["height"]
    assert any(cell["node_id"] is None and cell["state"] == "void" for cell in rift["debug_map"]["cells"])
    assert rift["map_view"]["center_node_id"] == "z01:2_2"
    assert len(rift["map_view"]["visible_nodes"]) == 4
    assert {node["state"] for node in rift["map_view"]["visible_nodes"]} <= {"current", "open", "blocked_temporary"}
    assert len(rift["map_view"]["visible_edges"]) == 2
    assert rift["movement"][0]["travel"]["duration_ms"] == 3000
    assert rift["movement"][0]["travel"]["possible_events"] == ["none", "combat"]
    assert rift["movement"][1]["travel"]["kind"] == "return"
    assert rift["node_entry_event"]["event_scope"] == "node_entry"
    assert context["game_state_scripts"] == ["/static/js/game/states/rift.js"]


def test_rift_state_js_is_loaded_outside_shared_game_bundle() -> None:
    config = Path("src/frontend/static/css/compiler_config.json").read_text(encoding="utf-8")
    loader_source = Path("src/frontend/static/js/core/game_state_loader.js").read_text(encoding="utf-8")
    rift_source = Path("src/frontend/static/js/game/states/rift.js").read_text(encoding="utf-8")
    game_bundle = Path("src/frontend/static/js/game.js").read_text(encoding="utf-8")

    assert "core/game_state_loader.js" in config
    assert "core/rift_map_store.js" not in config
    assert "core/rift_map_pan.js" not in config
    assert "window.RiftMapStore" not in game_bundle
    assert "window.RiftMapPan" not in game_bundle
    assert "window.GameStateLoader" in game_bundle
    assert "window.GameStateLoader" in loader_source
    assert "data-game-state" in loader_source
    assert "gameScripts" in loader_source
    assert "ensureScript" in loader_source
    assert "htmx:load" in loader_source
    assert "htmx:afterSwap" in loader_source
    assert "window.GameStates.rift" in rift_source
    assert "window.RiftMapStore" in rift_source
    assert "window.RiftMapPan" in rift_source
    assert 'const version = "v3"' in rift_source
    assert "mapScopeId" in rift_source
    assert "sessionStorage" in rift_source
    assert "localStorage" in rift_source
    assert "localStorage.setItem" in rift_source
    assert "removeStoredMaps" in rift_source
    assert "visible_nodes" in rift_source
    assert "visible_edges" in rift_source
    assert "headingRotation" in rift_source
    assert "--rift-current-marker-rotation" in rift_source
    assert "state.heading" in rift_source
    assert "shouldRenderEdge" in rift_source
    assert "shouldRenderNode" in rift_source
    assert 'edge.state === "open" || edge.state === "blocked_temporary"' in rift_source
    assert 'node.state === "open" || node.state === "blocked_temporary"' in rift_source
    assert 'state: "open"' in rift_source
    assert "renderAccumulatedMap" in rift_source
    assert "bindResetButtons" in rift_source
    assert "bindTravelButtons" in rift_source
    assert "bindHeartResultButtons" in rift_source
    assert "data-rift-dismiss-heart-result" in rift_source
    assert "has-heart-event" in rift_source
    assert "data-rift-blocker-feedback" in rift_source
    assert "game-modal-open" in rift_source
    assert "Проход закрыт" in rift_source
    assert "runTravelFlow" in rift_source
    assert "setupTravelOverlay" in rift_source
    assert "animateTravelSegment" in rift_source
    assert "postForm" in rift_source
    assert "replaceSessionRoot" in rift_source
    assert "refreshCatalog(nextRoot)" in rift_source
    assert "GameCatalogCache.resolveDom" in rift_source
    assert "refreshCharacterStatus()" in rift_source
    assert "renderCombatPrompt" in rift_source
    assert "RIFT_ENCOUNTER_REVEAL_MS" in rift_source
    assert "RIFT_ENCOUNTER_READY_DELAY_MS" in rift_source
    assert "revealCombatPrompt" in rift_source
    assert "await revealCombatPrompt(riftRoot, response.combat_prompt)" in rift_source
    assert "riftRoot.dataset.riftPhase = \"encounter-reveal\"" in rift_source
    assert "riftRoot.dataset.riftPhase = \"encounter-ready\"" in rift_source
    render_prompt_block = rift_source.split("function renderCombatPrompt", maxsplit=1)[1].split(
        "async function revealCombatPrompt",
        maxsplit=1,
    )[0]
    assert "hideTravelOverlay(riftRoot)" not in render_prompt_block
    assert "nodeCopy.hidden = true" not in render_prompt_block
    assert "enterCombatFromPrompt" in rift_source
    assert "formatCombatPromptSource" in rift_source
    assert "promptData.source || \"\"" not in rift_source
    assert "createEnemyRosterButton" in rift_source
    assert "createEnemyDetail" in rift_source
    assert "mobile-encounter-roster-target" in rift_source
    assert "mobile-encounter-target-view" in rift_source
    assert "mobile-encounter-target-art" in rift_source
    assert "mobile-encounter-target-copy" in rift_source
    assert "mobile-encounter-target-stats" in rift_source
    assert "rift-encounter-target" not in rift_source
    assert "rift-encounter-target-detail" not in rift_source
    assert "rift-encounter-target-art" not in rift_source
    assert "rift-encounter-target-copy" not in rift_source
    assert "enemyImageCandidates" in rift_source
    assert "visual.image_url" in rift_source
    assert "visual.generated_image_url" in rift_source
    assert "visual.placeholder_image_url" in rift_source
    assert "isFamilyFallbackImage" in rift_source
    assert "/static/images/monsters/families/" in rift_source
    assert "uniqueImageCandidates" in rift_source
    assert 'visual.status === "generated" ? visual.generated_image_url : null' not in rift_source
    assert 'image.classList.toggle("is-family-fallback", isFamilyFallbackImage(images[index]))' in rift_source
    assert "appendEnemyImage" in rift_source
    assert "appendEnemyArtFallback" in rift_source
    assert "mobile-encounter-target-image" in rift_source
    assert 'image.addEventListener("error"' in rift_source
    assert "backgroundImageLayer" not in rift_source
    assert "selectEnemyDetail" in rift_source
    assert "riftEnemyIndex" in rift_source
    assert "aria-pressed" in rift_source
    assert "data-rift-combat-detail" in rift_source
    assert "TIER" in rift_source
    assert "THREAT" not in rift_source
    assert "HEALTH" in rift_source
    assert "ENERGY" in rift_source
    assert "CONC" in rift_source
    assert "DANGER" in rift_source
    assert "RIFT CONTACT" not in rift_source
    assert "ENCOUNTER DETECTED" in rift_source
    assert "riftCombatMode" in rift_source
    assert "mobile-encounter-action--fight" in rift_source
    assert "/game/rift/travel/start" in rift_source
    assert "/game/rift/travel/tick" in rift_source
    assert "/game/rift/action" in rift_source
    assert "resolve_transition_combat" in rift_source
    assert "resolveCombatPlaceholder" in rift_source
    assert "combat_prompt" in rift_source
    assert "requestAnimationFrame" in rift_source
    assert "riftTravelReadyToSend" not in rift_source
    assert "riftTravelPossibleEvents" in rift_source
    assert "Object.values(nodes)" in rift_source
    assert "rotateDelta" not in rift_source
    assert "pointerdown" in rift_source
    assert "--rift-pan-x" in rift_source
    assert 'join(" - ")' in rift_source
    assert 'join(" // ")' not in rift_source


def _rift_payload() -> dict:
    return {
        "meta": {
            "rift_instance_id": "dev-rift-001",
            "zone_instance_id": "dev-rift-001:zone-01",
            "zone_canvas_key": "grid_5x5_active_15",
            "current_zone_key": "z01",
            "zone_depth": 1,
            "zone_chain_order": ["z01", "z02"],
            "zone_chain_total": 2,
            "schema_version": 1,
            "debug": True,
        },
        "hud": {
            "title": "Стартовый разлом",
            "subtitle": "Рваный тракт",
            "tier": 0,
            "danger_label": "нестабильно",
            "objective": {
                "type": "reach_heart",
                "title": "Найти сердце разлома",
                "description": "Пройдите через осколок дороги и доберитесь до сердца.",
                "progress_label": "Сердце не найдено",
                "is_complete": False,
            },
        },
        "current_node": {
            "node_id": "z01:2_2",
            "coord": {"x": 2, "y": 2},
            "title": "Вход у разбитой вехи",
            "description": "Старая дорожная веха торчит из земли под невозможным углом.",
            "visited": True,
            "tags": ["road", "starter_rift"],
            "image_url": None,
        },
        "surroundings": [
            {
                "absolute_direction": "north",
                "relative_direction": "forward",
                "state": "open",
                "target_node_id": "z01:2_1",
                "text": "Впереди виден узкий коридор.",
                "tone": "open",
            },
            {
                "absolute_direction": "east",
                "relative_direction": "right",
                "state": "void",
                "target_node_id": "z01:3_2",
                "text": "Справа зияет черный провал.",
                "tone": "blocked",
            },
        ],
        "movement": [
            {
                "id": "move:z01:2_1",
                "label": "Пойти прямо к просевшему тракту",
                "action": "move",
                "style": "primary",
                "is_active": True,
                "target_node_id": "z01:2_1",
                "target_coord": {"x": 2, "y": 1},
                "absolute_direction": "north",
                "relative_direction": "forward",
                "state": "open",
                "travel": {
                    "kind": "exploration",
                    "duration_ms": 3000,
                    "tick_interval_ms": 1000,
                    "event_check_count": 3,
                    "event_scope": "transition",
                    "possible_events": ["none", "combat"],
                    "can_trigger_event": True,
                    "event_chance": 0.2,
                },
            },
            {
                "id": "move:z01:2_3",
                "label": "Вернуться назад к треснувшему шлюзу",
                "action": "move",
                "style": "secondary",
                "is_active": True,
                "target_node_id": "z01:2_3",
                "target_coord": {"x": 2, "y": 3},
                "absolute_direction": "south",
                "relative_direction": "back",
                "state": "open",
                "travel": {
                    "kind": "return",
                    "duration_ms": 1000,
                    "tick_interval_ms": 1000,
                    "event_check_count": 0,
                    "event_scope": "transition",
                    "possible_events": ["none"],
                    "can_trigger_event": False,
                    "event_chance": 0.0,
                },
            },
            {
                "id": "void:3:2",
                "label": "Справа прохода нет",
                "action": "none",
                "style": "disabled",
                "is_active": False,
                "target_node_id": None,
                "target_coord": {"x": 3, "y": 2},
                "absolute_direction": "east",
                "relative_direction": "right",
                "state": "void",
            },
            {
                "id": "blocked:z01:1_2",
                "label": "Разломать частокол",
                "action": "inspect_blocker",
                "style": "primary",
                "is_active": True,
                "target_node_id": "z01:1_2",
                "target_coord": {"x": 1, "y": 2},
                "absolute_direction": "west",
                "relative_direction": "left",
                "state": "blocked_temporary",
                "tooltip": "Требуется: Сила 15. У тебя: 16. Можно пройти.",
                "debug_text_parts": {
                    "blocker_key": "jammed_service_gate",
                    "requirements": ["strength"],
                    "requirement_label": "Сила 15",
                    "check_result": {
                        "key": "strength",
                        "attribute_label": "Сила",
                        "dc": 15,
                        "current_known": True,
                        "current_value": 16,
                        "shortfall": 0,
                        "can_pass": True,
                    },
                    "requirement": {
                        "type": "skill_or_attribute_check",
                        "mode": "single_attribute",
                        "check": {
                            "kind": "attribute",
                            "key": "strength",
                            "dc": 15,
                            "label": "Разломать частокол",
                        },
                        "checks": [
                            {
                                "kind": "attribute",
                                "key": "strength",
                                "dc": 15,
                                "label": "Разломать частокол",
                            }
                        ],
                        "status": "contract_only",
                    },
                    "interaction": {
                        "mode": "single_attribute_check",
                        "resolved_checks": [
                            {
                                "kind": "attribute",
                                "key": "strength",
                                "dc": 15,
                                "label": "Разломать частокол",
                            }
                        ],
                    },
                },
            },
        ],
        "radar": {
            "center_node_id": "z01:2_2",
            "heading": "north",
            "arms": [
                {"absolute_direction": "north", "relative_direction": "forward", "state": "open"},
                {"absolute_direction": "east", "relative_direction": "right", "state": "void"},
                {"absolute_direction": "south", "relative_direction": "back", "state": "open"},
                {"absolute_direction": "west", "relative_direction": "left", "state": "blocked_temporary"},
            ],
        },
        "map_view": {
            "center_node_id": "z01:2_2",
            "current_coord": {"x": 2, "y": 2},
            "heading": "north",
            "visible_nodes": [
                {
                    "node_id": "z01:2_2",
                    "coord": {"x": 2, "y": 2},
                    "title": "Вход у разбитой вехи",
                    "state": "current",
                    "visited": True,
                    "discovered": True,
                },
                {
                    "node_id": "z01:2_1",
                    "coord": {"x": 2, "y": 1},
                    "title": "Коридор кабельных арок",
                    "state": "open",
                    "visited": False,
                    "discovered": True,
                },
                {
                    "node_id": "z01:2_3",
                    "coord": {"x": 2, "y": 3},
                    "title": "Треснувший шлюз",
                    "state": "open",
                    "visited": True,
                    "discovered": True,
                },
                {
                    "node_id": "z01:1_2",
                    "coord": {"x": 1, "y": 2},
                    "title": "Заклинившая решетка",
                    "state": "blocked_temporary",
                    "visited": False,
                    "discovered": True,
                },
            ],
            "visible_edges": [
                {
                    "from_node_id": "z01:2_2",
                    "to_node_id": "z01:2_1",
                    "absolute_direction": "north",
                    "relative_direction": "forward",
                    "state": "open",
                },
                {
                    "from_node_id": "z01:2_2",
                    "to_node_id": "z01:1_2",
                    "absolute_direction": "west",
                    "relative_direction": "left",
                    "state": "blocked_temporary",
                },
            ],
        },
        "node_entry_event": {
            "event_scope": "node_entry",
            "state": "placeholder",
            "possible_events": ["none", "combat"],
        },
        "heart": {
            "node_id": "z01:9_9",
            "status": "intact",
            "tier": 1,
            "base_value": 100,
            "is_current_node": False,
            "methods": [
                {"method": "shatter", "label": "Разбить сердце", "enabled": True},
                {
                    "method": "absorb",
                    "label": "Поглотить энергию",
                    "enabled": False,
                    "locked_reason": "not_unlocked",
                },
                {
                    "method": "dismantle",
                    "label": "Демонтировать",
                    "enabled": False,
                    "locked_reason": "artifact_craft_required",
                },
            ],
            "resolved_method": None,
            "reward": None,
            "can_exit": False,
        },
        "debug_map": {
            "width": 4,
            "height": 3,
            "passage_edges": [
                {
                    "from_node_id": "z01:2_2",
                    "to_node_id": "z01:2_1",
                    "from_coord": {"x": 2, "y": 2},
                    "to_coord": {"x": 2, "y": 1},
                    "state": "open",
                },
                {
                    "from_node_id": "z01:2_2",
                    "to_node_id": "z01:1_2",
                    "from_coord": {"x": 2, "y": 2},
                    "to_coord": {"x": 1, "y": 2},
                    "state": "blocked_temporary",
                },
                {
                    "from_node_id": "z01:2_2",
                    "to_node_id": "z01:1_2",
                    "from_coord": {"x": 2, "y": 2},
                    "to_coord": {"x": 1, "y": 2},
                    "state": "blocked_permanent",
                },
            ],
            "cells": [
                {
                    "node_id": None if (x, y) == (0, 0) else f"z01:{x}_{y}",
                    "coord": {"x": x, "y": y},
                    "title": None if (x, y) == (0, 0) else f"Узел {x}:{y}",
                    "state": "void" if (x, y) == (0, 0) else ("current" if (x, y) == (2, 2) else "open"),
                    "visited": (x, y) == (2, 2),
                    "discovered": (x, y) in {(0, 0), (2, 2)},
                }
                for y in range(3)
                for x in range(4)
            ],
        },
        "messages": [],
    }

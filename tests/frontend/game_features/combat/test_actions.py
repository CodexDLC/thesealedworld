from types import SimpleNamespace

import httpx
import pytest

from src.frontend.game_features.combat.routes.actions import (
    game_combat_feint_pin,
    game_combat_move,
    game_combat_result_continue,
)
from src.shared.schemas.combat import CombatActorCardDTO, CombatDashboardDTO, CombatResultDTO
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader, StateTransitionDTO


class FakeRenderer:
    def __init__(self) -> None:
        self.template = None
        self.context = None

    async def render(self, template, *, context, **kwargs):
        self.template = template
        self.context = context
        return SimpleNamespace(template=template, context=context)


class FakeAuthService:
    async def require_current_user(self, request):
        return SimpleNamespace(id="user-1")


class RejectingCombatApi:
    async def register_move(self, token, *, char_id, body):
        request = httpx.Request("POST", f"http://backend/api/game/combat/{char_id}/moves")
        response = httpx.Response(400, request=request, json={"detail": "Target is not available in your queue"})
        raise httpx.HTTPStatusError("bad request", request=request, response=response)

    async def snapshot(self, token, *, char_id):
        return CombatDashboardDTO(
            session_id="combat-1",
            status="active",
            hero=CombatActorCardDTO(actor_id=str(char_id), name="Hero"),
        )


class StructuredRejectingCombatApi(RejectingCombatApi):
    async def register_move(self, token, *, char_id, body):
        request = httpx.Request("POST", f"http://backend/api/game/combat/{char_id}/moves")
        response = httpx.Response(
            400,
            request=request,
            json={
                "error": {
                    "code": "combat_target_unavailable",
                    "message": "Target is not available in your queue",
                    "domain": "combat",
                    "frontend_action": "show_message",
                    "retriable": False,
                    "context": {"target_id": "2"},
                }
            },
        )
        raise httpx.HTTPStatusError("bad request", request=request, response=response)


class CapturingPinCombatApi:
    def __init__(self) -> None:
        self.pin_body = None

    async def pin_feint(self, token, *, char_id, body):
        self.pin_body = body
        return CombatDashboardDTO(
            session_id="combat-1",
            status="active",
            hero=CombatActorCardDTO(actor_id=str(char_id), name="Hero"),
        )


class ResultCombatApi:
    async def register_move(self, token, *, char_id, body):
        return CombatResultDTO(char_id=char_id, combat_id="combat-1", reason="combat_session_finished")


class ContinueCombatApi:
    def __init__(self) -> None:
        self.char_id = None

    async def continue_result(self, token, *, char_id):
        self.char_id = char_id
        return CoreResponseDTO(
            header=GameStateHeader(current_state="arena"),
            payload=StateTransitionDTO(char_id=char_id, target_state="arena", reason="combat_result_continued"),
            payload_type="state_transition",
        )


class FakeContextBuilder:
    def __init__(self) -> None:
        self.response = None

    def build_combat_dashboard_context(self, dashboard, *, char_id):
        return {"combat": dashboard, "char_id": char_id}

    def build_combat_result_context(self, result, *, char_id):
        return {"combat_result": result, "char_id": char_id}

    async def build_from_response(self, request, response, *, char_id):
        self.response = response
        return {"domain": "arena", "char_id": char_id, "transition": response.payload}


@pytest.mark.asyncio
async def test_combat_move_rejection_refreshes_dashboard_instead_of_raising() -> None:
    ui = FakeRenderer()
    request = SimpleNamespace(cookies={"tbmmorpg_access_token": "token"}, state=SimpleNamespace())

    response = await game_combat_move(
        request,
        ui,
        FakeAuthService(),
        RejectingCombatApi(),
        FakeContextBuilder(),
        char_id=5,
        action="exchange",
    )

    assert response.template == "game/session_content_inner.html"
    assert ui.context["combat"].events_delta.events[-1].text == "Target is not available in your queue"


@pytest.mark.asyncio
async def test_combat_move_rejection_preserves_structured_error_code() -> None:
    ui = FakeRenderer()
    request = SimpleNamespace(cookies={"tbmmorpg_access_token": "token"}, state=SimpleNamespace())

    await game_combat_move(
        request,
        ui,
        FakeAuthService(),
        StructuredRejectingCombatApi(),
        FakeContextBuilder(),
        char_id=5,
        action="exchange",
    )

    event = ui.context["combat"].events_delta.events[-1]
    assert event.text == "Target is not available in your queue"
    assert event.data["code"] == "combat_target_unavailable"
    assert event.data["context"] == {"target_id": "2"}


@pytest.mark.asyncio
async def test_combat_move_renders_result_when_backend_returns_result() -> None:
    ui = FakeRenderer()
    request = SimpleNamespace(cookies={"tbmmorpg_access_token": "token"}, state=SimpleNamespace())

    response = await game_combat_move(
        request,
        ui,
        FakeAuthService(),
        ResultCombatApi(),
        FakeContextBuilder(),
        char_id=5,
        action="exchange",
    )

    assert response.template == "game/session_content_inner.html"
    assert ui.context["combat_result"].reason == "combat_session_finished"


@pytest.mark.asyncio
async def test_combat_feint_pin_forwards_pin_request() -> None:
    ui = FakeRenderer()
    api = CapturingPinCombatApi()
    request = SimpleNamespace(cookies={"tbmmorpg_access_token": "token"}, state=SimpleNamespace())

    response = await game_combat_feint_pin(
        request,
        ui,
        FakeAuthService(),
        api,
        FakeContextBuilder(),
        char_id=5,
        feint_id="true_strike",
    )

    assert response.template == "game/session_content_inner.html"
    assert api.pin_body.feint_id == "true_strike"


@pytest.mark.asyncio
async def test_combat_result_continue_uses_backend_transition() -> None:
    ui = FakeRenderer()
    api = ContinueCombatApi()
    builder = FakeContextBuilder()
    request = SimpleNamespace(cookies={"tbmmorpg_access_token": "token"}, state=SimpleNamespace())

    response = await game_combat_result_continue(
        request,
        ui,
        FakeAuthService(),
        api,
        builder,
        char_id=5,
    )

    assert response.template == "game/session_content_inner.html"
    assert api.char_id == 5
    assert builder.response.payload.reason == "combat_result_continued"
    assert ui.context["domain"] == "arena"

from types import SimpleNamespace

import httpx
import pytest

from src.frontend.game_features.combat.routes.actions import game_combat_move
from src.shared.schemas.combat import CombatActorCardDTO, CombatDashboardDTO


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


class FakeContextBuilder:
    def build_combat_dashboard_context(self, dashboard, *, char_id):
        return {"combat": dashboard, "char_id": char_id}


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

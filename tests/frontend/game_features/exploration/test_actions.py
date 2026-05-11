from types import SimpleNamespace

import pytest

from src.frontend.game_features.exploration.routes.actions import game_exploration_interact
from src.shared.enums import CoreDomain
from src.shared.schemas import CoreResponseDTO, GameStateHeader, StateTransitionDTO


class FakeAuthService:
    async def require_current_user(self, request):
        return SimpleNamespace(id="user-1")


class FakeExplorationActionService:
    async def interact(self, request, *, char_id, action, target_id=None):
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.COMBAT, previous_state=CoreDomain.EXPLORATION),
            payload=StateTransitionDTO(char_id=char_id, target_state=CoreDomain.COMBAT, reason="encounter_attack"),
            payload_type="state_transition",
        )


class FakeResponseDirector:
    def __init__(self):
        self.redirect_transitions = None

    async def resolve(self, request, response, *, source_state, char_id, redirect_transitions=False):
        self.redirect_transitions = redirect_transitions
        return "__session_redirect__", {"char_id": char_id}


@pytest.mark.asyncio
async def test_exploration_combat_transition_redirects_to_full_session_shell():
    director = FakeResponseDirector()

    response = await game_exploration_interact(
        SimpleNamespace(headers={"HX-Request": "true"}),
        SimpleNamespace(render=None),
        FakeAuthService(),
        FakeExplorationActionService(),
        director,
        char_id=7,
        action="attack",
    )

    assert director.redirect_transitions is True
    assert response.status_code == 204
    assert response.headers["HX-Redirect"] == "/game/session"
    assert "tbmmorpg_active_character_id=7" in response.headers["set-cookie"]

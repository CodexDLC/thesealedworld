"""Smoke tests for the ``/game/keepalive`` realtime supervisor hook.

The route is non-destructive: it relies on ``GameTokenRefreshMiddleware`` to
rotate the access cookie via the refresh token (the path matches
``GAME_TOKEN_REFRESH_PATH_PREFIXES``). When middleware can't recover the
session we return 401 so the supervisor stops retrying and bails to lobby.

Critically: this route MUST NOT mint a fresh ``session_id`` by re-selecting
the character. Doing so causes a session-replaced ping-pong between tabs.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.frontend.game_features.session.middleware import (
    GAME_TOKEN_REFRESH_PATH_PREFIXES,
    _should_refresh_for_path,
)


def test_keepalive_path_is_covered_by_refresh_middleware() -> None:
    # The whole point of the route is to be picked up by the refresh
    # middleware — if the prefix list ever stops covering /game, the WS
    # supervisor would silently call a 204 that does nothing useful.
    assert any(path.startswith("/game") for path in GAME_TOKEN_REFRESH_PATH_PREFIXES)
    assert _should_refresh_for_path("/game/keepalive") is True


@pytest.mark.unit
def test_keepalive_returns_401_when_unauthenticated() -> None:
    from fastapi import FastAPI

    from src.frontend.game_features.session.routes.pages import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/game/keepalive")
    # No cookies, no active character → middleware can't refresh anything,
    # so the supervisor must see a non-2xx and bail to the lobby instead of
    # spinning a reconnect loop.
    assert response.status_code == 401

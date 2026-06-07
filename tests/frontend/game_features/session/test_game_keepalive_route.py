"""Smoke tests for the ``/game/keepalive`` realtime supervisor hook.

The route itself only returns 204; the value it provides is that its path
matches ``GAME_TOKEN_REFRESH_PATH_PREFIXES``, so a call exercises the
auto-refresh middleware and rotates the access cookie. These tests pin both
contracts: the handler shape and the path-prefix match.
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
def test_keepalive_route_returns_204_no_content() -> None:
    from fastapi import FastAPI

    from src.frontend.game_features.session.routes.pages import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/game/keepalive")
    assert response.status_code == 204
    assert response.content == b""

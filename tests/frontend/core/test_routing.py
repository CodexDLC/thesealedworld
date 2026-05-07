from fastapi import FastAPI

from src.frontend.core.routing import include_frontend_routers


def test_frontend_registers_combat_move_route() -> None:
    app = FastAPI()

    include_frontend_routers(app)

    route = next(route for route in app.routes if getattr(route, "name", None) == "game_combat_move")
    assert getattr(route, "path", None) == "/game/combat/move"
    assert "POST" in getattr(route, "methods", set())


def test_frontend_registers_combat_logs_route() -> None:
    app = FastAPI()

    include_frontend_routers(app)

    route = next(route for route in app.routes if getattr(route, "name", None) == "game_combat_logs")
    assert getattr(route, "path", None) == "/game/combat/logs"
    assert "GET" in getattr(route, "methods", set())


def test_frontend_router_list_does_not_register_legacy_cabinet_route() -> None:
    app = FastAPI()

    include_frontend_routers(app)

    assert all(getattr(route, "name", None) != "cabinet" for route in app.routes)

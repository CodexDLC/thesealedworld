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


def test_frontend_registers_combat_feint_pin_route() -> None:
    app = FastAPI()

    include_frontend_routers(app)

    route = next(route for route in app.routes if getattr(route, "name", None) == "game_combat_feint_pin")
    assert getattr(route, "path", None) == "/game/combat/feint-pin"
    assert "POST" in getattr(route, "methods", set())


def test_frontend_registers_test_rift_route() -> None:
    app = FastAPI()

    include_frontend_routers(app)

    route = next(route for route in app.routes if getattr(route, "name", None) == "test_rift")
    assert getattr(route, "path", None) == "/testrift"
    assert "GET" in getattr(route, "methods", set())


def test_frontend_registers_rift_travel_routes() -> None:
    app = FastAPI()

    include_frontend_routers(app)

    start_route = next(route for route in app.routes if getattr(route, "name", None) == "game_rift_travel_start")
    tick_route = next(route for route in app.routes if getattr(route, "name", None) == "game_rift_travel_tick")
    action_route = next(route for route in app.routes if getattr(route, "name", None) == "game_rift_action")
    assert getattr(start_route, "path", None) == "/game/rift/travel/start"
    assert "POST" in getattr(start_route, "methods", set())
    assert getattr(tick_route, "path", None) == "/game/rift/travel/tick"
    assert "POST" in getattr(tick_route, "methods", set())
    assert getattr(action_route, "path", None) == "/game/rift/action"
    assert "POST" in getattr(action_route, "methods", set())


def test_frontend_router_list_does_not_register_legacy_cabinet_route() -> None:
    app = FastAPI()

    include_frontend_routers(app)

    assert all(getattr(route, "name", None) != "cabinet" for route in app.routes)

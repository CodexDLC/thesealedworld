from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_cabinet import include_cabinet
from src.frontend.cabinet import CABINET_MODULES


def test_project_cabinet_modules_render_engine_cabinet() -> None:
    app = FastAPI()

    include_cabinet(app, modules=CABINET_MODULES, mount_path="/admin")

    response = TestClient(app).get("/admin")
    assert response.status_code == 200
    # Admin cabinet renders the first registered project module.
    assert "Аналитика сайта" in response.text
    assert "Активных боёв" in response.text


def test_project_cabinet_module_route_renders() -> None:
    app = FastAPI()

    include_cabinet(app, modules=CABINET_MODULES, mount_path="/admin")

    response = TestClient(app).get("/admin/game-server")
    assert response.status_code == 200
    assert "Game Server" in response.text

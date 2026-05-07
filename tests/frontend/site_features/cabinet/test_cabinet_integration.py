from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_cabinet import include_cabinet
from src.frontend.cabinet import CABINET_MODULES


def test_project_cabinet_modules_render_engine_cabinet() -> None:
    app = FastAPI()

    include_cabinet(app, modules=CABINET_MODULES, mount_path="/cabinet")

    response = TestClient(app).get("/cabinet")
    assert response.status_code == 200
    assert "Game Server" in response.text
    assert "Game Server Status" in response.text
    assert "Runtime Checks" in response.text


def test_project_cabinet_module_route_renders() -> None:
    app = FastAPI()

    include_cabinet(app, modules=CABINET_MODULES, mount_path="/cabinet")

    response = TestClient(app).get("/cabinet/game-server")
    assert response.status_code == 200
    assert "Game Server" in response.text

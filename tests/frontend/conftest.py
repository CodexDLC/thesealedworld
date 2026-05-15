from typing import Any

import pytest


@pytest.fixture
def app() -> Any:
    from src.frontend.app import app

    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app: Any) -> Any:
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c

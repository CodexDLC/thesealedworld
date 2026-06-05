import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.testclient import TestClient

from src.frontend.config.settings import settings
from src.frontend.core.csrf import CsrfMiddleware


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CsrfMiddleware)

    @app.get("/page")
    async def page(request: Request) -> PlainTextResponse:
        return PlainTextResponse(request.state.csrf_token)

    @app.post("/submit")
    async def submit(request: Request) -> JSONResponse:
        body = await request.body()
        return JSONResponse({"received": body.decode("utf-8")})

    @app.post("/auth/refresh")
    async def auth_refresh() -> JSONResponse:
        return JSONResponse({"ok": True})

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.mark.unit
def test_get_issues_csrf_cookie_and_exposes_token_to_state(client: TestClient) -> None:
    response = client.get("/page")
    assert response.status_code == 200
    token = response.text
    assert len(token) >= 32
    assert response.cookies.get(settings.csrf_cookie_name) == token


@pytest.mark.unit
def test_post_without_cookie_rejected(client: TestClient) -> None:
    response = client.post("/submit", data={"hello": "world"})
    assert response.status_code == 403
    assert "CSRF token missing" in response.text


@pytest.mark.unit
def test_post_with_matching_form_token_accepted(client: TestClient) -> None:
    bootstrap = client.get("/page")
    token = bootstrap.text
    response = client.post(
        "/submit",
        data={"hello": "world", settings.csrf_field_name: token},
    )
    assert response.status_code == 200
    body = response.json()["received"]
    assert "hello=world" in body
    assert f"{settings.csrf_field_name}={token}" in body


@pytest.mark.unit
def test_post_with_matching_header_token_accepted(client: TestClient) -> None:
    bootstrap = client.get("/page")
    token = bootstrap.text
    response = client.post(
        "/submit",
        data={"hello": "world"},
        headers={settings.csrf_header_name: token},
    )
    assert response.status_code == 200


@pytest.mark.unit
def test_post_with_mismatched_token_rejected(client: TestClient) -> None:
    client.get("/page")
    response = client.post(
        "/submit",
        data={"hello": "world", settings.csrf_field_name: "wrong-token"},
    )
    assert response.status_code == 403


@pytest.mark.unit
def test_auth_prefix_skipped(client: TestClient) -> None:
    response = client.post("/auth/refresh")
    assert response.status_code == 200

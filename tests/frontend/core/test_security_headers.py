import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from src.frontend.core.security_headers import SecurityHeadersMiddleware


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/ping")
    async def ping() -> PlainTextResponse:
        return PlainTextResponse("pong")

    return TestClient(app)


@pytest.mark.unit
def test_security_headers_present(client: TestClient) -> None:
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "SAMEORIGIN"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert "permissions-policy" in response.headers


@pytest.mark.unit
def test_security_headers_do_not_override_existing(client: TestClient) -> None:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/custom")
    async def custom() -> PlainTextResponse:
        return PlainTextResponse("ok", headers={"X-Frame-Options": "DENY"})

    other_client = TestClient(app)
    response = other_client.get("/custom")
    assert response.headers["x-frame-options"] == "DENY"

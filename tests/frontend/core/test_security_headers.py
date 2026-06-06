import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from src.frontend.core.security_headers import SecurityHeadersMiddleware, build_content_security_policy


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
    assert "img-src 'self' data: blob:" in response.headers["content-security-policy"]
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


@pytest.mark.unit
def test_content_security_policy_allows_configured_s3_image_origin() -> None:
    csp = build_content_security_policy(
        image_origins=["https://nbg1.your-objectstorage.com/generated-assets?ignored=1"]
    )

    assert "img-src 'self' data: blob: https://nbg1.your-objectstorage.com;" in csp
    assert "ignored" not in csp

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

@pytest.mark.unit
def test_root_endpoint(client):
    """Test the root endpoint of the backend."""
    # We don't need to mock lifespan here as 'client' fixture already handled it
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "status": "online",
        "service": "backend-logic",
        "features": ["event-bus", "game-streams"]
    }

@pytest.mark.unit
def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.unit
def test_app_initialization(app):
    """Test that the app initialization (lifespan) works with mocks."""
    from fastapi.testclient import TestClient

    # We need to use a fresh TestClient to trigger the lifespan
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200

@pytest.mark.unit
def test_exception_handler(client):
    """Test that the custom exception handler is working."""
    from src.backend.core.exceptions import BaseAPIException
    from src.backend.app import app

    @app.get("/test-exception")
    async def raise_exception():
        raise BaseAPIException(status_code=418, detail="Test error")

    response = client.get("/test-exception")
    assert response.status_code == 418
    assert response.json()["error"]["message"] == "Test error"

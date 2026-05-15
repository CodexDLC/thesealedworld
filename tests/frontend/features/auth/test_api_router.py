import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.frontend.features.auth.dependencies.providers import get_auth_service, get_current_user


@pytest.mark.unit
class TestAuthRouter:
    @pytest.fixture
    def mock_service(self):
        return MagicMock()

    @pytest.fixture
    def override_deps(self, app, mock_service):
        app.dependency_overrides[get_auth_service] = lambda: mock_service
        yield
        app.dependency_overrides.clear()

    def test_register(self, client, override_deps, mock_service):
        mock_service.register_user = AsyncMock(return_value={
            "id": str(uuid.uuid4()),
            "email": "test@e.com",
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.now().isoformat()
        })

        response = client.post("/auth/register", json={"email": "test@e.com", "password": "password123"})
        assert response.status_code == 201
        assert response.json()["email"] == "test@e.com"

    def test_login_success(self, client, override_deps, mock_service):
        mock_user = MagicMock()
        mock_service.authenticate_user = AsyncMock(return_value=mock_user)
        mock_service.create_tokens = AsyncMock(return_value={"access_token": "a", "refresh_token": "r", "token_type": "bearer"})

        response = client.post("/auth/login", data={"username": "test@e.com", "password": "password123"})
        assert response.status_code == 200
        assert response.json()["access_token"] == "a"

    def test_login_failure(self, client, override_deps, mock_service):
        mock_service.authenticate_user = AsyncMock(return_value=None)

        response = client.post("/auth/login", data={"username": "test@e.com", "password": "password123"})
        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Incorrect email or password"

    def test_read_me(self, client, app):
        mock_user = MagicMock(
            id=uuid.uuid4(),
            email="test@e.com",
            is_active=True,
            is_superuser=False,
            created_at=datetime.now()
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.get("/auth/me", headers={"Authorization": "Bearer token"})
        assert response.status_code == 200
        assert response.json()["email"] == "test@e.com"
        app.dependency_overrides.clear()

    def test_refresh_token(self, client, override_deps, mock_service):
        mock_service.refresh_token = AsyncMock(return_value={"access_token": "new_a", "refresh_token": "new_r", "token_type": "bearer"})

        response = client.post("/auth/refresh", json={"refresh_token": "old_r"})
        assert response.status_code == 200
        assert response.json()["access_token"] == "new_a"

    def test_logout(self, client, override_deps, mock_service):
        mock_service.logout = AsyncMock()

        response = client.post("/auth/logout", json={"refresh_token": "r"})
        assert response.status_code == 204
        mock_service.logout.assert_called_with("r")

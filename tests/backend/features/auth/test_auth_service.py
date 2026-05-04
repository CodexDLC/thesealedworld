import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from src.backend.core.exceptions import BusinessLogicException
from src.backend.features_site.auth.dto.user import UserCreate, UserResponse
from src.backend.features_site.auth.services.auth_service import AuthService


@pytest.mark.unit
class TestAuthService:
    @pytest.fixture
    def user_repo(self):
        return MagicMock()

    @pytest.fixture
    def token_repo(self):
        return MagicMock()

    @pytest.fixture
    def service(self, user_repo, token_repo):
        return AuthService(user_repository=user_repo, token_repository=token_repo)

    async def test_register_user_success(self, service, user_repo):
        user_in = UserCreate(email="test@example.com", password="password123")  # pragma: allowlist secret
        mock_user = MagicMock(
            id=uuid.uuid4(),
            email="test@example.com",
            is_active=True,
            is_superuser=False,
            created_at=datetime.now()
        )
        user_repo.create = AsyncMock(return_value=mock_user)
        user_repo.commit = AsyncMock()

        result = await service.register_user(user_in)

        assert isinstance(result, UserResponse)
        assert result.email == "test@example.com"
        user_repo.create.assert_called_once()
        user_repo.commit.assert_called_once()

    async def test_register_user_duplicate_email(self, service, user_repo):
        user_in = UserCreate(email="test@example.com", password="password123")  # pragma: allowlist secret
        user_repo.create = AsyncMock(side_effect=IntegrityError(None, None, None))

        with pytest.raises(BusinessLogicException, match="User with this email already exists"):
            await service.register_user(user_in)

    async def test_authenticate_user_success(self, service, user_repo, mocker):
        mocker.patch("src.backend.features_site.auth.services.auth_service.verify_password", return_value=True)
        user = MagicMock(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password="hashed",  # pragma: allowlist secret
            is_active=True,
            is_superuser=False,
            created_at=datetime.now()
        )
        user_repo.get_by_email = AsyncMock(return_value=user)

        result = await service.authenticate_user("test@example.com ", "password123")  # pragma: allowlist secret

        assert result is not None
        assert result.email == "test@example.com"

    async def test_authenticate_user_invalid_password(self, service, user_repo, mocker):
        mocker.patch("src.backend.features_site.auth.services.auth_service.verify_password", return_value=False)
        user = MagicMock(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password="hashed",  # pragma: allowlist secret
            is_active=True
        )
        user_repo.get_by_email = AsyncMock(return_value=user)

        result = await service.authenticate_user("test@example.com", "wrong")

        assert result is None

    async def test_authenticate_user_inactive(self, service, user_repo, mocker):
        mocker.patch("src.backend.features_site.auth.services.auth_service.verify_password", return_value=True)
        user = MagicMock(is_active=False)
        user_repo.get_by_email = AsyncMock(return_value=user)
        assert await service.authenticate_user("test@example.com", "password") is None

    async def test_create_tokens(self, service, token_repo, mocker):
        mocker.patch("src.backend.features_site.auth.services.auth_service.create_access_token", return_value="access")
        mocker.patch("secrets.token_urlsafe", return_value="refresh")
        token_repo.create = AsyncMock()
        token_repo.commit = AsyncMock()

        user = UserResponse(id=uuid.uuid4(), email="test@example.com", is_active=True, is_superuser=False, created_at=datetime.now())
        tokens = await service.create_tokens(user)

        assert tokens.access_token == "access"
        assert tokens.refresh_token == "refresh"
        token_repo.create.assert_called_once()
        token_repo.commit.assert_called_once()

    async def test_refresh_token_success(self, service, token_repo, user_repo, mocker):
        from datetime import UTC, timedelta
        db_token = MagicMock(user_id=uuid.uuid4(), expires_at=datetime.now(UTC) + timedelta(days=1))
        token_repo.get_by_token = AsyncMock(return_value=db_token)
        token_repo.delete = AsyncMock()
        token_repo.commit = AsyncMock()

        user = MagicMock(id=db_token.user_id, email="t@e.com", is_active=True, created_at=datetime.now())
        user_repo.get_by_id = AsyncMock(return_value=user)

        mocker.patch.object(service, "create_tokens", AsyncMock(return_value="new_tokens"))

        result = await service.refresh_token("valid_token")
        assert result == "new_tokens"
        token_repo.delete.assert_called_with("valid_token")

    async def test_refresh_token_invalid(self, service, token_repo):
        token_repo.get_by_token = AsyncMock(return_value=None)
        from src.backend.core.exceptions import AuthException
        with pytest.raises(AuthException, match="Invalid refresh token"):
            await service.refresh_token("invalid")

    async def test_refresh_token_expired(self, service, token_repo):
        from datetime import UTC, timedelta
        db_token = MagicMock(expires_at=datetime.now(UTC) - timedelta(days=1))
        token_repo.get_by_token = AsyncMock(return_value=db_token)
        token_repo.delete = AsyncMock()
        token_repo.commit = AsyncMock()

        from src.backend.core.exceptions import AuthException
        with pytest.raises(AuthException, match="Refresh token expired"):
            await service.refresh_token("expired")
        token_repo.delete.assert_called_once()

    async def test_refresh_token_user_not_found_or_inactive(self, service, token_repo, user_repo):
        from datetime import UTC, timedelta
        db_token = MagicMock(user_id=uuid.uuid4(), expires_at=datetime.now(UTC) + timedelta(days=1))
        token_repo.get_by_token = AsyncMock(return_value=db_token)
        token_repo.delete = AsyncMock()
        token_repo.commit = AsyncMock()

        user_repo.get_by_id = AsyncMock(return_value=None)

        from src.backend.core.exceptions import AuthException
        with pytest.raises(AuthException, match="User not found or inactive"):
            await service.refresh_token("token")

        # Test inactive user branch
        user_repo.get_by_id = AsyncMock(return_value=MagicMock(is_active=False))
        with pytest.raises(AuthException, match="User not found or inactive"):
            await service.refresh_token("token")

    async def test_logout(self, service, token_repo):
        token_repo.delete = AsyncMock()
        token_repo.commit = AsyncMock()
        await service.logout("token")
        token_repo.delete.assert_called_with("token")
        token_repo.commit.assert_called_once()

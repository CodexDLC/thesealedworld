import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.frontend.features.auth.dto.user import UserCreate, UserResponse
from src.frontend.features.auth.integrations import DuplicateEmailError
from src.frontend.features.auth.services.site_auth_service import AuthService
from src.shared.exceptions import BusinessLogicException


@pytest.mark.unit
class TestAuthService:
    @pytest.fixture
    def persistence(self):
        return MagicMock()

    @pytest.fixture
    def service(self, persistence):
        return AuthService(persistence=persistence)

    async def test_register_user_success(self, service, persistence):
        user_in = UserCreate(email="test@example.com", password="password123")  # pragma: allowlist secret
        mock_user = MagicMock(
            id=uuid.uuid4(),
            email="test@example.com",
            is_active=True,
            is_superuser=False,
            tester_status="none",
            tester_approved_at=None,
            referral_code="SEAL-ABCD2345",
            created_at=datetime.now()
        )
        persistence.register_user = AsyncMock(return_value=mock_user)

        result = await service.register_user(user_in)

        assert isinstance(result, UserResponse)
        assert result.email == "test@example.com"
        assert result.tester_status == "none"
        assert result.tester_approved_at is None
        assert result.referral_code == "SEAL-ABCD2345"
        persistence.register_user.assert_called_once()

    async def test_register_user_duplicate_email(self, service, persistence):
        user_in = UserCreate(email="test@example.com", password="password123")  # pragma: allowlist secret
        persistence.register_user = AsyncMock(side_effect=DuplicateEmailError)

        with pytest.raises(BusinessLogicException, match="User with this email already exists"):
            await service.register_user(user_in)

    async def test_authenticate_user_success(self, service, persistence, mocker):
        mocker.patch("src.frontend.features.auth.services.site_auth_service.verify_password", return_value=True)
        user = MagicMock(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password="hashed",  # pragma: allowlist secret
            is_active=True,
            is_superuser=False,
            tester_status="none",
            tester_approved_at=None,
            referral_code="SEAL-ABCD2345",
            created_at=datetime.now()
        )
        persistence.get_user_by_email = AsyncMock(return_value=user)

        result = await service.authenticate_user("test@example.com ", "password123")  # pragma: allowlist secret

        assert result is not None
        assert result.email == "test@example.com"

    async def test_authenticate_user_invalid_password(self, service, persistence, mocker):
        mocker.patch("src.frontend.features.auth.services.site_auth_service.verify_password", return_value=False)
        user = MagicMock(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password="hashed",  # pragma: allowlist secret
            is_active=True
        )
        persistence.get_user_by_email = AsyncMock(return_value=user)

        result = await service.authenticate_user("test@example.com", "wrong")

        assert result is None

    async def test_authenticate_user_inactive(self, service, persistence, mocker):
        mocker.patch("src.frontend.features.auth.services.site_auth_service.verify_password", return_value=True)
        user = MagicMock(is_active=False)
        persistence.get_user_by_email = AsyncMock(return_value=user)
        assert await service.authenticate_user("test@example.com", "password") is None

    async def test_authenticate_user_missing_still_runs_verify_password(self, service, persistence, mocker):
        """Missing email must still trigger verify_password against a dummy hash to keep
        timing parity and avoid email enumeration."""
        verify_mock = mocker.patch(
            "src.frontend.features.auth.services.site_auth_service.verify_password",
            return_value=False,
        )
        persistence.get_user_by_email = AsyncMock(return_value=None)

        result = await service.authenticate_user("ghost@example.com", "anything")

        assert result is None
        verify_mock.assert_called_once()
        called_password, called_hash = verify_mock.call_args.args
        assert called_password == "anything"  # pragma: allowlist secret
        assert called_hash.startswith("pbkdf2_sha256$")

    async def test_create_tokens(self, service, persistence, mocker):
        mocker.patch("src.frontend.features.auth.services.site_auth_service.create_access_token", return_value="access")
        mocker.patch("secrets.token_urlsafe", return_value="refresh")
        persistence.create_refresh_token = AsyncMock()

        user = UserResponse(id=uuid.uuid4(), email="test@example.com", is_active=True, is_superuser=False, created_at=datetime.now())
        tokens = await service.create_tokens(user)

        assert tokens.access_token == "access"
        assert tokens.refresh_token == "refresh"
        persistence.create_refresh_token.assert_called_once()

    async def test_refresh_token_rotates_when_near_expiry(self, service, persistence, mocker):
        from datetime import UTC, timedelta
        db_token = MagicMock(user_id=uuid.uuid4(), expires_at=datetime.now(UTC) + timedelta(days=1))
        persistence.get_refresh_token = AsyncMock(return_value=db_token)
        persistence.delete_refresh_token = AsyncMock()

        user = MagicMock(id=db_token.user_id, email="t@e.com", is_active=True, tester_status="none", tester_approved_at=None, referral_code="SEAL-ABCD2345", created_at=datetime.now())
        persistence.get_user_by_id = AsyncMock(return_value=user)

        mocker.patch.object(service, "create_tokens", AsyncMock(return_value="new_tokens"))

        result = await service.refresh_token("valid_token")
        assert result == "new_tokens"
        persistence.delete_refresh_token.assert_called_with("valid_token")

    async def test_refresh_token_keeps_existing_when_healthy(self, service, persistence, mocker):
        """Refresh with >7d left: only issue new access; do NOT rotate refresh."""
        from datetime import UTC, timedelta
        db_token = MagicMock(user_id=uuid.uuid4(), expires_at=datetime.now(UTC) + timedelta(days=20))
        persistence.get_refresh_token = AsyncMock(return_value=db_token)
        persistence.delete_refresh_token = AsyncMock()

        user = MagicMock(
            id=db_token.user_id,
            email="t@e.com",
            is_active=True,
            tester_status="none",
            tester_approved_at=None,
            referral_code="SEAL-ABCD2345",
            created_at=datetime.now(),
        )
        persistence.get_user_by_id = AsyncMock(return_value=user)
        mocker.patch(
            "src.frontend.features.auth.services.site_auth_service.create_access_token",
            return_value="fresh-access",
        )
        create_tokens_spy = mocker.patch.object(service, "create_tokens", AsyncMock())

        result = await service.refresh_token("plenty-of-life-left")

        assert result.access_token == "fresh-access"
        assert result.refresh_token == "plenty-of-life-left"
        persistence.delete_refresh_token.assert_not_called()
        create_tokens_spy.assert_not_called()

    async def test_refresh_token_not_found_raises_specific_error(self, service, persistence):
        from src.frontend.features.auth.services.site_auth_service import RefreshTokenNotFoundError

        persistence.get_refresh_token = AsyncMock(return_value=None)
        with pytest.raises(RefreshTokenNotFoundError):
            await service.refresh_token("ghost")

    async def test_refresh_token_expired(self, service, persistence):
        from datetime import UTC, timedelta
        db_token = MagicMock(expires_at=datetime.now(UTC) - timedelta(days=1))
        persistence.get_refresh_token = AsyncMock(return_value=db_token)
        persistence.delete_refresh_token = AsyncMock()

        from src.shared.exceptions import AuthException
        with pytest.raises(AuthException, match="Refresh token expired"):
            await service.refresh_token("expired")
        persistence.delete_refresh_token.assert_called_once()

    async def test_refresh_token_user_not_found_or_inactive(self, service, persistence):
        from datetime import UTC, timedelta
        db_token = MagicMock(user_id=uuid.uuid4(), expires_at=datetime.now(UTC) + timedelta(days=1))
        persistence.get_refresh_token = AsyncMock(return_value=db_token)
        persistence.delete_refresh_token = AsyncMock()

        persistence.get_user_by_id = AsyncMock(return_value=None)

        from src.shared.exceptions import AuthException
        with pytest.raises(AuthException, match="User not found or inactive"):
            await service.refresh_token("token")

        # Test inactive user branch
        persistence.get_user_by_id = AsyncMock(return_value=MagicMock(is_active=False))
        with pytest.raises(AuthException, match="User not found or inactive"):
            await service.refresh_token("token")

    async def test_logout(self, service, persistence):
        persistence.delete_refresh_token = AsyncMock()
        await service.logout("token")
        persistence.delete_refresh_token.assert_called_with("token")

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.shared.exceptions import AuthException
from src.frontend.features.auth.dependencies.providers import (
    get_auth_service,
    get_current_user,
    get_token_repository,
    get_user_repository,
)
from src.frontend.features.auth.services.site_auth_service import AuthService


@pytest.mark.unit
class TestAuthDependencies:
    def test_get_user_repository(self):
        db = MagicMock()
        repo = get_user_repository(db)
        assert repo.session == db

    def test_get_token_repository(self):
        db = MagicMock()
        repo = get_token_repository(db)
        assert repo.session == db

    def test_get_auth_service(self):
        user_repo = MagicMock()
        token_repo = MagicMock()
        service = get_auth_service(user_repo, token_repo)
        assert isinstance(service, AuthService)

    async def test_get_current_user_success(self, mocker):
        user_id = uuid.uuid4()
        mocker.patch(
            "src.frontend.features.auth.dependencies.providers.decode_access_token",
            return_value={"sub": str(user_id)},
        )

        auth_service = MagicMock()
        auth_service.get_user_by_id = AsyncMock(return_value="user")

        user = await get_current_user("token", auth_service)
        assert user == "user"
        auth_service.get_user_by_id.assert_called_with(user_id=user_id)

    async def test_get_current_user_invalid_token(self, mocker):
        mocker.patch(
            "src.frontend.features.auth.dependencies.providers.decode_access_token",
            side_effect=ValueError("invalid"),
        )

        with pytest.raises(AuthException, match="Could not validate credentials"):
            await get_current_user("token", MagicMock())

    async def test_get_current_user_not_found(self, mocker):
        user_id = uuid.uuid4()
        mocker.patch(
            "src.frontend.features.auth.dependencies.providers.decode_access_token",
            return_value={"sub": str(user_id)},
        )

        auth_service = MagicMock()
        auth_service.get_user_by_id = AsyncMock(return_value=None)

        with pytest.raises(AuthException, match="User not found"):
            await get_current_user("token", auth_service)

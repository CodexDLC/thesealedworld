import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.backend.features.auth.dependencies import (
    get_user_repository,
    get_token_repository,
    get_auth_service,
    get_current_user
)
from src.backend.core.exceptions import AuthException

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
        assert service.user_repository == user_repo
        assert service.token_repository == token_repo

    async def test_get_current_user_success(self, mocker):
        user_id = uuid.uuid4()
        mocker.patch("src.backend.features.auth.dependencies.decode_access_token", return_value={"sub": str(user_id)})

        auth_service = MagicMock()
        auth_service.user_repository.get_by_id = AsyncMock(return_value="user")

        user = await get_current_user("token", auth_service)
        assert user == "user"
        auth_service.user_repository.get_by_id.assert_called_with(user_id=user_id)

    async def test_get_current_user_invalid_token(self, mocker):
        mocker.patch("src.backend.features.auth.dependencies.decode_access_token", side_effect=ValueError("invalid"))

        with pytest.raises(AuthException, match="Could not validate credentials"):
            await get_current_user("token", MagicMock())

    async def test_get_current_user_not_found(self, mocker):
        user_id = uuid.uuid4()
        mocker.patch("src.backend.features.auth.dependencies.decode_access_token", return_value={"sub": str(user_id)})

        auth_service = MagicMock()
        auth_service.user_repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(AuthException, match="User not found"):
            await get_current_user("token", auth_service)

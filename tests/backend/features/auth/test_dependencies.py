import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.core.exceptions import AuthException
from src.backend.features_site.auth.dependencies import (
    get_auth_service,
    get_current_user,
    get_token_repository,
    get_user_repository,
)


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
        mocker.patch("src.backend.features_site.auth.dependencies.decode_access_token", return_value={"sub": str(user_id)})

        auth_service = MagicMock()
        auth_service.user_repository.get_by_id = AsyncMock(return_value="user")

        user = await get_current_user("token", auth_service)
        assert user == "user"
        auth_service.user_repository.get_by_id.assert_called_with(user_id=user_id)

    async def test_get_current_user_uses_redis_cache(self, mocker):
        user_id = uuid.uuid4()
        mocker.patch("src.backend.features_site.auth.dependencies.decode_access_token", return_value={"sub": str(user_id)})

        auth_service = MagicMock()
        auth_service.user_repository.get_by_id = AsyncMock()
        user_cache = MagicMock()
        user_cache.get = AsyncMock(return_value="cached_user")

        user = await get_current_user("token", auth_service, user_cache)

        assert user == "cached_user"
        user_cache.get.assert_awaited_once_with(user_id)
        auth_service.user_repository.get_by_id.assert_not_called()

    async def test_get_current_user_warms_redis_cache_after_db_lookup(self, mocker):
        user_id = uuid.uuid4()
        mocker.patch("src.backend.features_site.auth.dependencies.decode_access_token", return_value={"sub": str(user_id)})

        auth_service = MagicMock()
        auth_service.user_repository.get_by_id = AsyncMock(return_value="db_user")
        user_cache = MagicMock()
        user_cache.get = AsyncMock(return_value=None)
        user_cache.set = AsyncMock()

        user = await get_current_user("token", auth_service, user_cache)

        assert user == "db_user"
        user_cache.get.assert_awaited_once_with(user_id)
        auth_service.user_repository.get_by_id.assert_awaited_once_with(user_id=user_id)
        user_cache.set.assert_awaited_once_with("db_user")

    async def test_get_current_user_invalid_token(self, mocker):
        mocker.patch("src.backend.features_site.auth.dependencies.decode_access_token", side_effect=ValueError("invalid"))

        with pytest.raises(AuthException, match="Could not validate credentials"):
            await get_current_user("token", MagicMock())

    async def test_get_current_user_not_found(self, mocker):
        user_id = uuid.uuid4()
        mocker.patch("src.backend.features_site.auth.dependencies.decode_access_token", return_value={"sub": str(user_id)})

        auth_service = MagicMock()
        auth_service.user_repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(AuthException, match="User not found"):
            await get_current_user("token", auth_service)

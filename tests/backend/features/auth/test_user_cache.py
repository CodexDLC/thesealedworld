import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features_site.auth.models import User
from src.backend.features_site.auth.services.user_cache import AuthUserCache


@pytest.mark.unit
class TestAuthUserCache:
    async def test_get_returns_cached_user(self):
        user_id = uuid.uuid4()
        redis = MagicMock()
        redis.string.get = AsyncMock(
            return_value=(
                f'{{"id":"{user_id}","email":"player@example.com","is_active":true,'
                '"is_superuser":false,"created_at":"2026-05-02T00:00:00Z"}'
            )
        )

        user = await AuthUserCache(redis).get(user_id)

        assert user is not None
        assert user.id == user_id
        assert user.email == "player@example.com"
        assert user.is_active is True
        redis.string.get.assert_awaited_once_with(f"auth:user:{user_id}")

    async def test_get_returns_none_on_cache_miss(self):
        user_id = uuid.uuid4()
        redis = MagicMock()
        redis.string.get = AsyncMock(return_value=None)

        user = await AuthUserCache(redis).get(user_id)

        assert user is None

    async def test_set_stores_user_with_access_token_ttl(self):
        user_id = uuid.uuid4()
        redis = MagicMock()
        redis.string.set = AsyncMock()
        user = User(
            id=user_id,
            email="player@example.com",
            hashed_password="hashed",
            is_active=True,
            is_superuser=False,
            created_at=datetime(2026, 5, 2, tzinfo=UTC),
        )

        await AuthUserCache(redis).set(user)

        redis.string.set.assert_awaited_once()
        key, payload = redis.string.set.await_args.args
        assert key == f"auth:user:{user_id}"
        assert '"email":"player@example.com"' in payload
        assert redis.string.set.await_args.kwargs["ttl"] == 1800

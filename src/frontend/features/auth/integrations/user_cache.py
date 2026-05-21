from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.frontend.config.settings import settings
from src.frontend.features.auth.dto.user import UserResponse

if TYPE_CHECKING:
    import uuid

    from codex_platform.redis_service import RedisService


class RedisFrontendAuthUserCache:
    key_prefix = "site:auth:user"

    def __init__(self, redis: RedisService) -> None:
        self.redis = redis

    async def get(self, user_id: uuid.UUID) -> UserResponse | None:
        key = self._key(user_id)
        try:
            raw = await self.redis.string.get(key)
        except Exception:
            logger.bind(user_id=str(user_id)).opt(exception=True).warning("FrontendAuthUserCacheReadFailed")
            return None

        if not raw:
            return None

        try:
            user = UserResponse.model_validate_json(raw)
        except Exception:
            logger.bind(user_id=str(user_id)).opt(exception=True).warning("FrontendAuthUserCachePayloadInvalid")
            return None

        logger.bind(user_id=str(user_id)).debug("FrontendAuthUserCacheHit")
        return user

    async def set(self, user: UserResponse) -> None:
        key = self._key(user.id)
        ttl = max(settings.auth_user_cache_ttl_seconds, 60)
        try:
            await self.redis.string.set(key, user.model_dump_json(), ttl=ttl)
        except Exception:
            logger.bind(user_id=str(user.id)).opt(exception=True).warning("FrontendAuthUserCacheWriteFailed")
            return
        logger.bind(user_id=str(user.id), ttl_seconds=ttl).debug("FrontendAuthUserCacheStored")

    @classmethod
    def _key(cls, user_id: uuid.UUID) -> str:
        return f"{cls.key_prefix}:{user_id}"

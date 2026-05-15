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
            logger.opt(exception=True).warning("Frontend auth user cache read failed: user_id={}", user_id)
            return None

        if not raw:
            return None

        try:
            user = UserResponse.model_validate_json(raw)
        except Exception:
            logger.opt(exception=True).warning("Frontend auth user cache payload invalid: user_id={}", user_id)
            return None

        logger.info("Frontend auth user cache hit: user_id={}", user_id)
        return user

    async def set(self, user: UserResponse) -> None:
        key = self._key(user.id)
        ttl = max(settings.auth_user_cache_ttl_seconds, 60)
        try:
            await self.redis.string.set(key, user.model_dump_json(), ttl=ttl)
        except Exception:
            logger.opt(exception=True).warning("Frontend auth user cache write failed: user_id={}", user.id)
            return
        logger.info("Frontend auth user cache stored: user_id={} ttl={}", user.id, ttl)

    @classmethod
    def _key(cls, user_id: uuid.UUID) -> str:
        return f"{cls.key_prefix}:{user_id}"

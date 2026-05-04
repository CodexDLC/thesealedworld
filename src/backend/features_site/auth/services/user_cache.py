import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.config.settings import settings
from src.backend.features_site.auth.dto.user import UserResponse
from src.backend.features_site.auth.models import User

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class AuthUserCache:
    key_prefix = "auth:user"

    def __init__(self, redis: "RedisService") -> None:
        self.redis = redis

    async def get(self, user_id: uuid.UUID) -> User | None:
        key = self._key(user_id)
        try:
            raw = await self.redis.string.get(key)
        except Exception:
            logger.opt(exception=True).warning("Auth user cache read failed: user_id={}", user_id)
            return None

        if not raw:
            return None

        try:
            dto = UserResponse.model_validate_json(raw)
        except Exception:
            logger.opt(exception=True).warning("Auth user cache payload invalid: user_id={}", user_id)
            return None

        logger.info("Auth user cache hit: user_id={}", user_id)
        return self._user_from_dto(dto)

    async def set(self, user: User) -> None:
        key = self._key(user.id)
        dto = UserResponse.model_validate(user)
        ttl = max(settings.access_token_expire_minutes * 60, 60)
        try:
            await self.redis.string.set(key, dto.model_dump_json(), ttl=ttl)
        except Exception:
            logger.opt(exception=True).warning("Auth user cache write failed: user_id={}", user.id)
            return
        logger.info("Auth user cache stored: user_id={} ttl={}", user.id, ttl)

    @classmethod
    def _key(cls, user_id: uuid.UUID) -> str:
        return f"{cls.key_prefix}:{user_id}"

    @staticmethod
    def _user_from_dto(dto: UserResponse) -> User:
        data: dict[str, Any] = dto.model_dump()
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            data["created_at"] = datetime.fromisoformat(created_at)
        return User(**data, hashed_password="")  # nosec B106

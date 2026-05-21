from codex_platform.redis_service import RedisService
from redis.asyncio import Redis


class RedisContainer:
    """
    Container for Redis managers.
    Provides a unified entry point to the Redis data layer.
    Assembled by CLI when adding new Redis managers.
    """

    def __init__(self, redis_client: Redis) -> None:
        self.redis_client = redis_client
        self.service = RedisService(redis_client)

        # --- Registered Managers ---
        # [REDIS_MANAGERS_INITIALIZATION]

        # Example:
        # from .managers.example_cache import ExampleCacheManager
        # self.example_cache = ExampleCacheManager(redis_client)

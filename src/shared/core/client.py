from loguru import logger
from redis.asyncio import ConnectionPool, Redis

from src.shared.core.config import CommonSettings


async def get_redis_client(settings: CommonSettings) -> Redis:
    """
    Creates and returns a Redis client instance.
    Uses ConnectionPool for efficient connection management.
    """
    logger.debug(f"RedisClient | action=connect host={settings.redis_host} port={settings.redis_port}")

    pool = ConnectionPool.from_url(
        settings.redis_url,
        max_connections=settings.redis_max_connections,
        decode_responses=True,  # Automatically decode bytes to strings
        socket_timeout=settings.redis_timeout,
        socket_connect_timeout=settings.redis_timeout,
    )

    client = Redis(connection_pool=pool)

    # Test connection
    try:
        # TODO: Убрать type: ignore после обновления типов redis-py
        # Проблема: client.ping() имеет Union[Awaitable[bool], bool] в зависимости от версии
        # Решение: Обновить redis-py до версии с правильными async типами
        await client.ping()  # type: ignore[misc]
        logger.info("RedisClient | status=connected")
    except Exception as e:
        logger.critical(f"RedisClient | status=failed error={e}")
        raise e

    return client

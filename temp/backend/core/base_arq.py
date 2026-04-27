from typing import Any

from arq.connections import ArqRedis, RedisSettings, create_pool
from loguru import logger as log

from src.backend.core.config import settings
from src.backend.database.redis.redis_service import RedisService
from src.shared.core.client import get_redis_client


async def base_startup(ctx: dict) -> None:
    """
    Базовая инициализация для всех воркеров.
    Создает клиент Redis и RedisService.

    Args:
        ctx: Контекст ARQ воркера.
    """
    log.info("ArqWorkerStartup | status=starting")
    try:
        # Используем нашу фабрику для создания клиента (с пулом и настройками)
        redis_client = await get_redis_client(settings)

        # Оборачиваем в сервис
        redis_service = RedisService(redis_client)

        ctx["redis_client_internal"] = redis_client
        ctx["redis_service"] = redis_service
        log.info("ArqWorkerStartup | status=success")
    except Exception as e:  # noqa: BLE001
        log.exception(f"ArqWorkerStartup | status=failed error={e}")
        raise


async def base_shutdown(ctx: dict) -> None:
    """
    Базовая очистка ресурсов.

    Args:
        ctx: Контекст ARQ воркера.
    """
    log.info("ArqWorkerShutdown | status=starting")
    if "redis_client_internal" in ctx:
        try:
            # Закрываем соединение (или возвращаем в пул)
            await ctx["redis_client_internal"].close()
            log.info("ArqWorkerShutdown | status=success")
        except Exception as e:  # noqa: BLE001
            log.exception(f"ArqWorkerShutdown | status=failed error={e}")


class BaseArqSettings:
    """
    Базовые настройки для всех ARQ воркеров в проекте.
    """

    redis_settings = RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password,
        database=0,  # ARQ обычно использует 0, но можно вынести в конфиг
    )

    max_jobs = 20
    job_timeout = 60
    keep_result = 5

    on_startup = base_startup
    on_shutdown = base_shutdown


class ArqService:
    """
    Обертка над клиентом ARQ.
    Позволяет создавать пул один раз и переиспользовать его.
    """

    def __init__(self):
        self.pool: ArqRedis | None = None

    async def init(self):
        """Инициализация пула (вызывать при старте приложения)."""
        if not self.pool:
            try:
                self.pool = await create_pool(BaseArqSettings.redis_settings)
                log.debug("ArqService | action=init status=success")
            except Exception as e:  # noqa: BLE001
                log.exception(f"ArqService | action=init status=failed error={e}")
                raise

    async def close(self):
        """Закрытие пула (вызывать при остановке приложения)."""
        if self.pool:
            try:
                await self.pool.close()
                log.debug("ArqService | action=close status=success")
            except Exception as e:  # noqa: BLE001
                log.exception(f"ArqService | action=close status=failed error={e}")

    async def enqueue_job(self, function: str, *args: Any, **kwargs: Any) -> Any | None:
        """
        Отправка задачи в очередь.

        Args:
            function: Имя функции задачи.
            *args: Аргументы задачи.
            **kwargs: Ключевые аргументы задачи.

        Returns:
            Any | None: Результат отправки (Job) или None при ошибке.
        """
        if not self.pool:
            # Ленивая инициализация (на случай, если init не вызвали)
            await self.init()

        if self.pool:
            try:
                job = await self.pool.enqueue_job(function, *args, **kwargs)
                log.debug(f"ArqService | action=enqueue_job function={function} job_id={job.job_id if job else 'None'}")
                return job
            except Exception as e:  # noqa: BLE001
                log.exception(f"ArqService | action=enqueue_job status=failed function={function} error={e}")
                return None
        return None


async def get_arq_pool() -> ArqRedis:
    """
    Хелпер для получения сырого пула (если нужно).
    """
    return await create_pool(BaseArqSettings.redis_settings)

import asyncio
import importlib
from typing import Any

from aiogram import Bot

# 1. Base Library Imports
from codex_bot.engine.container import BaseBotContainer
from codex_bot.engine.discovery.service import FeatureDiscoveryService
from codex_bot.redis.dispatcher import BotRedisDispatcher
from codex_bot.redis.stream_processor import RedisStreamProcessor
from loguru import logger as log
from redis.asyncio import Redis

# 2. Local Project Imports
from tg_bot.core.config import BotSettings
from tg_bot.core.settings import INSTALLED_FEATURES, INSTALLED_REDIS_FEATURES
from tg_bot.infrastructure.redis.stream_storage import RedisStreamStorageAdapter
from tg_bot.sender import TelegramMediaSender


class BotContainer(BaseBotContainer):
    """
    Project-specific Dependency Injection Container.

    Coordinates lifecycle of infrastructure (Redis, DB) and business logic (Features).
    """

    def __init__(self, settings: BotSettings, redis_client: Redis | None = None):
        # Settings protocol ensures availability of owner/superuser lists
        super().__init__(settings, redis_client=redis_client)

        # --- 1. Infrastructure Services (Redis, Stream Processor) ---
        self.redis_dispatcher = BotRedisDispatcher()

        # Stream processor is initialized only if redis is active
        # The stream and consumer group are settings-driven for independence from monolith defaults
        self.stream_processor: RedisStreamProcessor | None = None
        if redis_client:
            self.stream_processor = RedisStreamProcessor(
                storage=RedisStreamStorageAdapter(redis_client),
                stream_name=settings.redis_stream_name,
                consumer_group_name=settings.redis_consumer_group,
                consumer_name="bot_worker_tg_bot",
            )

        # --- 2. Data Persistence (SQLAlchemy) ---

        # --- 3. Feature Discovery & Scaffolding ---
        discovery_dispatcher: Any = self.redis_dispatcher

        # Convention over Configuration: Automatically find and mount features
        self.discovery_service = FeatureDiscoveryService(
            module_prefix="tg_bot.features",
            installed_features=INSTALLED_FEATURES,
            installed_redis_features=INSTALLED_REDIS_FEATURES,
            redis_dispatcher=discovery_dispatcher,
        )

        # Discover routers and configurations
        self.discovery_service.discover_all()
        self._include_feature_redis_routers()

        # Instantiate all discovered feature orchestrators
        self.features = self.discovery_service.create_feature_orchestrators(self)

    def set_bot(self, bot: Bot) -> None:
        """Configures services that require an active Bot instance."""
        super().set_bot(bot)

        if self.redis_client and self.stream_processor:
            # Connect Redis dispatcher to the container and worker
            self.redis_dispatcher.setup(container=self)
            self.stream_processor.set_message_callback(self.redis_dispatcher.process_message)

        self.media_sender = TelegramMediaSender(bot=bot, manager=self.view_sender.manager)

    def _include_feature_redis_routers(self) -> None:
        """Register Redis routers declared by each redis feature setting module."""
        for feature_name in INSTALLED_REDIS_FEATURES:
            module_path = f"tg_bot.features.redis.{feature_name}.feature_setting"
            try:
                module = importlib.import_module(module_path)
            except ImportError as exc:
                log.bind(module_path=module_path, error_type=exc.__class__.__name__).warning(
                    "BotRedisFeatureSettingsImportFailed"
                )
                continue

            router_factory = getattr(module, "get_redis_router", None)
            if not callable(router_factory):
                log.bind(feature_name=feature_name).debug("BotRedisFeatureRouterMissing")
                continue

            self.redis_dispatcher.include_router(router_factory())

    async def shutdown(self) -> None:
        """Gracefully cleanup all infrastructure resources."""
        log.info("BotContainerShutdownStarted")

        # 1. First, shutdown features while DB/Redis are still alive
        await super().shutdown()

        # 2. Then, close infrastructure connections
        cleanup_tasks = []

        if self.stream_processor:
            cleanup_tasks.append(self.stream_processor.stop_listening())

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        log.info("BotContainerShutdownCompleted")

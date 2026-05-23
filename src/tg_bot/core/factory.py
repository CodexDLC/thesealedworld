from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from codex_bot.engine.factory.bot_builder import BotBuilder
from codex_bot.engine.protocols import ContainerProtocol
from loguru import logger as log
from redis.asyncio import Redis

from tg_bot.core.settings import CUSTOM_MIDDLEWARES

if TYPE_CHECKING:
    from tg_bot.core.config import BotSettings


def build_bot(
    settings: BotSettings, redis_client: Redis | None, container: ContainerProtocol
) -> tuple[Bot, Dispatcher]:
    """
    Builds and configures Bot and Dispatcher using BotBuilder.
    """
    # 1. FSM Storage Selection
    storage = RedisStorage(redis=redis_client) if redis_client else MemoryStorage()

    # 2. Initialize Builder
    builder = BotBuilder(
        bot_token=settings.bot_token,
        fsm_storage=storage,
    )

    # --- 3. Register Middlewares (ORDER IS CRITICAL) ---

    # A. Data Infrastructure (if enabled)

    # B. MANDATORY CORE (Container, Director, UserValidation)
    # The builder will automatically link the Bot instance to the Container.
    builder.setup_core(container=container)

    # C. Security & Localization (Optional)
    from codex_bot.engine.middlewares.throttling import ThrottlingMiddleware

    if redis_client:
        builder.add_project_middleware(
            ThrottlingMiddleware(redis=redis_client, rate_limit=settings.bot_throttling_rate)
        )

    # D. Register User Custom Middlewares
    for mw in CUSTOM_MIDDLEWARES:
        builder.add_project_middleware(mw)

    # --- 4. Build Core ---
    bot, dp = builder.build()

    discovery = getattr(container, "discovery_service", None)
    if discovery:
        for router in discovery.collect_aiogram_routers():
            dp.include_router(router)
            log.bind(router_name=router.name).info("BotFactoryAiogramRouterIncluded")

    return bot, dp

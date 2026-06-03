from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from codex_platform.streams import StreamRuntime, StreamRuntimeConfig
from fastapi import FastAPI
from loguru import logger

from src.backend.chat.services.connection_manager import ChatConnectionManager
from src.backend.chat.services.session_service import PlayerChatSession
from src.backend.config.settings import settings
from src.backend.realtime.core.lifespan import bootstrap_realtime
from src.backend.realtime.services.notice_service import RealtimeNoticeService


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ChatServiceStartup")

    # Chat persistence is managed by backend Alembic, not by runtime create_all().
    app.state.redis = aioredis.from_url(settings.effective_redis_url, decode_responses=True)

    app.state.chat_manager = ChatConnectionManager()
    app.state.chat_sessions = PlayerChatSession(app.state.redis)

    # Realtime gateway (stage 1 co-locates the realtime module here; see
    # docs/planning/tech-debt/realtime/player_realtime_gateway.md).
    bootstrap_realtime(app)
    app.state.realtime_notice_service = RealtimeNoticeService(app.state.realtime_manager)

    from src.backend.chat.events import bind as bind_chat_events
    from src.backend.chat.events import router as chat_events_router
    from src.backend.realtime.events import bind as bind_realtime_events
    from src.backend.realtime.events import router as realtime_events_router

    bind_chat_events(app)
    bind_realtime_events(app)

    runtime = StreamRuntime(
        redis=app.state.redis,
        config=StreamRuntimeConfig(
            stream_name=settings.game_stream_name,
            consumer_group=settings.stream_consumer_group,
            consumer_name=settings.worker_name,
            enabled_groups=None,
        ),
    )
    runtime.include_router(chat_events_router)
    runtime.include_router(realtime_events_router)
    app.state.stream_runtime = runtime
    await runtime.start()

    logger.info("ChatServiceReady")
    yield

    logger.info("ChatServiceShutdown")
    await runtime.stop()
    await app.state.redis.aclose()

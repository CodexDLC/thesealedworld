from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from codex_platform.streams import StreamRuntime, StreamRuntimeConfig
from fastapi import FastAPI
from loguru import logger

from src.chat.config import settings
from src.chat.core.database import create_db_tables
from src.chat.services.connection_manager import ChatConnectionManager
from src.chat.services.session_service import PlayerChatSession


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Chat service startup")

    # 1. Database tables
    await create_db_tables()

    # 2. Redis client
    app.state.redis = aioredis.from_url(settings.effective_redis_url, decode_responses=True)

    # 3. ConnectionManager
    app.state.chat_manager = ChatConnectionManager()

    # 4. PlayerChatSession helper (stateless, uses app.state.redis)
    app.state.chat_sessions = PlayerChatSession(app.state.redis)

    # 5. Stream Runtime — consumer group "chat", separate from backend "monolith"
    from src.chat.events import bind as bind_chat_events
    from src.chat.events import router as chat_events_router

    bind_chat_events(app)

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
    app.state.stream_runtime = runtime
    await runtime.start()

    logger.info("Chat service ready")
    yield

    logger.info("Chat service shutdown")
    await runtime.stop()
    await app.state.redis.aclose()

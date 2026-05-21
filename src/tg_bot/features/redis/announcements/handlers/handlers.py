from typing import Any

from codex_bot.redis import RedisRouter
from loguru import logger as log

# Router for events from Redis Stream
redis_router = RedisRouter()


@redis_router.message("news.published")
async def handle_news_published(message_data: dict[str, Any], container: Any) -> None:
    """Handler for news.published events from Redis Stream.

    Do NOT catch exceptions here — let them propagate to the dispatcher.
    """
    log.info(f"Announcements | Processing event type='{message_data.get('type')}'")

    try:
        orchestrator = container.get_feature("redis_announcements")
    except KeyError:
        log.warning("Announcements | Orchestrator 'redis_announcements' not found in container features")
        return

    # Call orchestrator processing logic
    await orchestrator.process_news(message_data)


@redis_router.message("news.unpublished")
async def handle_news_unpublished(message_data: dict[str, Any], container: Any) -> None:
    """Handler for news.unpublished events from Redis Stream."""
    log.info(f"Announcements | Processing event type='{message_data.get('type')}'")

    try:
        orchestrator = container.get_feature("redis_announcements")
    except KeyError:
        log.warning("Announcements | Orchestrator 'redis_announcements' not found in container features")
        return

    await orchestrator.process_news_unpublished(message_data)

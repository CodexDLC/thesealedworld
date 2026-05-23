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
    log.bind(event_type=message_data.get("type")).info("AnnouncementEventProcessing")

    try:
        orchestrator = container.get_feature("redis_announcements")
    except KeyError:
        log.bind(feature_key="redis_announcements").warning("AnnouncementOrchestratorMissing")
        return

    # Call orchestrator processing logic
    await orchestrator.process_news(message_data)


@redis_router.message("news.unpublished")
async def handle_news_unpublished(message_data: dict[str, Any], container: Any) -> None:
    """Handler for news.unpublished events from Redis Stream."""
    log.bind(event_type=message_data.get("type")).info("AnnouncementEventProcessing")

    try:
        orchestrator = container.get_feature("redis_announcements")
    except KeyError:
        log.bind(feature_key="redis_announcements").warning("AnnouncementOrchestratorMissing")
        return

    await orchestrator.process_news_unpublished(message_data)

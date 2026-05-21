from typing import Any

from codex_bot.redis import RedisRouter
from loguru import logger as log

# Router for events from Redis Stream
redis_router = RedisRouter()


@redis_router.message("news.published")
async def handle_announcements_event(message_data: dict[str, Any], container: Any) -> None:
    """Handler for news.published events from Redis Stream.

    Do NOT catch exceptions here — let them propagate to the dispatcher.
    """
    log.info(f"Announcements | Processing event type='{message_data.get('type')}'")

    orchestrator = getattr(container, "redis_announcements", None)
    if not orchestrator:
        log.warning("Announcements | Orchestrator 'redis_announcements' not found in container")
        return

    # Call orchestrator processing logic
    await orchestrator.process_news(message_data)

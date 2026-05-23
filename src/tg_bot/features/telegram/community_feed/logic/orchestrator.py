from __future__ import annotations

from typing import TYPE_CHECKING, Any

from codex_bot.base import BaseBotOrchestrator, UnifiedViewDTO, ViewResultDTO
from loguru import logger as log

from ..feature_setting import CommunityFeedStates
from ..ui.ui import CommunityFeedUI

if TYPE_CHECKING:
    from codex_bot.director import Director


class CommunityFeedOrchestrator(BaseBotOrchestrator[Any]):
    """
    Business logic and navigation for the CommunityFeed feature.
    """

    def __init__(self, container: Any = None) -> None:
        # expected_state must be a string for Director
        super().__init__(expected_state=CommunityFeedStates.main.state)
        self.container = container
        self.ui = CommunityFeedUI()

    async def process_group_message(self, message: Any, container: Any) -> None:
        """Moderates the group message and publishes approved ones to the Redis Stream."""
        # 1. Extract content
        text = message.text or message.caption or ""
        text = text.strip()

        # 2. Moderation checks
        # Skip empty messages or commands
        if not text or text.startswith("/"):
            return

        # Skip excessively short messages
        if len(text) < 4:
            log.bind(message_length=len(text)).debug("CommunityFeedMessageTooShort")
            return

        # Simple keyword blacklist for moderation
        blacklist = ["spam", "buy crypto", "casino", "poker", "scam", "реклама", "продам"]
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in blacklist):
            log.bind(message_length=len(text), chat_id=message.chat.id).info("CommunityFeedMessageBlocked")
            return

        # 3. Message Approved! Prepare the stream payload.
        user = message.from_user
        if user:
            author_name = user.full_name
            username = user.username or ""
        else:
            author_name = "Anonymous"
            username = ""

        # Use chat username to format deep link to message if public
        chat_username = message.chat.username
        message_link = f"https://t.me/{chat_username}/{message.message_id}" if chat_username else ""

        event_data = {
            "message_id": str(message.message_id),
            "chat_id": str(message.chat.id),
            "chat_title": message.chat.title or "Group",
            "author_id": str(user.id) if user else "",
            "author_name": author_name,
            "username": username,
            "text": text,
            "message_link": message_link,
            "timestamp": str(message.date.timestamp()),
        }

        # 4. Publish to Redis Stream
        if container and container.redis_client:
            try:
                from codex_platform.streams.producer import StreamProducer

                stream_name = container.settings.redis_stream_name
                producer = StreamProducer(container.redis_client, stream_name)

                log.bind(stream_name=stream_name, chat_id=message.chat.id).info("CommunityFeedMessagePublishing")
                await producer.publish("community.message.approved", event_data)
            except Exception:
                log.bind(chat_id=message.chat.id).exception("CommunityFeedPublishFailed")
        else:
            log.warning("CommunityFeedPublishSkipped")

    async def render_content(
        self, director: Director | None = None, payload: Any = None
    ) -> ViewResultDTO | UnifiedViewDTO:
        """
        Main logic for rendering feature content.
        """
        if director:
            log.bind(session_key=director.session_key).debug("CommunityFeedContentRendered")

        return self.ui.render_main(payload)

    async def handle_entry(
        self,
        director: Director,
        payload: Any = None,
    ) -> UnifiedViewDTO:
        """Entry point into the feature. Called by Director on set_scene()."""
        log.bind(session_key=director.session_key).debug("CommunityFeedEntryHandled")

        return await self.render(director=director, payload=payload)

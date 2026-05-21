from __future__ import annotations

from typing import TYPE_CHECKING, Any

from codex_bot.base import UnifiedViewDTO, ViewResultDTO
from loguru import logger as log

if TYPE_CHECKING:
    from codex_bot.director.director import Director


class AnnouncementsOrchestrator:
    """Orchestrator for Redis-driven channel announcements."""

    def __init__(self, container: Any) -> None:
        self.container = container

    async def process_news(self, payload: dict[str, Any]) -> None:
        """Posts a published news announcement to the configured Telegram channel."""
        chat_id = self.container.settings.telegram_channel_id
        if not chat_id:
            log.warning("AnnouncementsOrchestrator | TELEGRAM_CHANNEL_ID is not configured. Skipping publication.")
            return

        article_id = str(payload.get("id", "")).strip()
        if not article_id:
            log.warning("AnnouncementsOrchestrator | news.published payload has no article id. Skipping publication.")
            return

        title = payload.get("title", "")
        preview = payload.get("preview", "")
        slug = payload.get("slug", "")
        cover_image = payload.get("cover_image", "")

        sender = self.container.media_sender
        domain = self.container.settings.domain_name
        link = sender.build_absolute_url(domain=domain, path_or_url=f"/news/{slug}")
        photo_url = sender.build_absolute_url(domain=domain, path_or_url=cover_image)
        text = f'📰 <b>{title}</b>\n\n{preview}\n\n🔗 <a href="{link}">Читать далее на сайте</a>'

        try:
            log.info(f"AnnouncementsOrchestrator | Sending announcement to channel {chat_id}.")
            await sender.send_or_replace_html(
                session_key=self._news_session_key(article_id),
                chat_id=chat_id,
                text=text,
                link=link,
                photo_url=photo_url,
            )
        except Exception as e:
            log.error(f"AnnouncementsOrchestrator | Failed to send telegram announcement: {e}")
            raise

    async def process_news_unpublished(self, payload: dict[str, Any]) -> None:
        """Deletes a previously sent Telegram announcement for unpublished news."""
        article_id = str(payload.get("id", "")).strip()
        if not article_id:
            log.warning("AnnouncementsOrchestrator | news.unpublished payload has no article id. Skipping deletion.")
            return

        chat_id = self.container.settings.telegram_channel_id
        if not chat_id:
            log.warning("AnnouncementsOrchestrator | TELEGRAM_CHANNEL_ID is not configured. Skipping deletion.")
            return

        await self.container.media_sender.delete(session_key=self._news_session_key(article_id), chat_id=chat_id)

    async def render_content(
        self, director: Director | None = None, payload: Any = None
    ) -> ViewResultDTO | UnifiedViewDTO:
        """Incoming data processing for the background worker."""
        log.debug(f"AnnouncementsOrchestrator | Handling payload: {payload}")
        return ViewResultDTO(text="OK")

    @staticmethod
    def _news_session_key(article_id: str) -> str:
        return f"news:{article_id}"

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from codex_bot.base import UnifiedViewDTO, ViewResultDTO
from loguru import logger as log

from src.shared.utils.url import build_public_absolute_url

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
            log.warning("AnnouncementPublishSkipped")
            return

        article_id = str(payload.get("id", "")).strip()
        if not article_id:
            log.warning("AnnouncementPublishPayloadInvalid")
            return

        title = payload.get("title", "")
        preview = payload.get("preview", "")
        slug = payload.get("slug", "")
        cover_image = payload.get("cover_image", "")

        sender = self.container.media_sender
        domain = self.container.settings.domain_name
        link = build_public_absolute_url(domain_name=domain, path_or_url=f"/news/{slug}")
        photo_url = build_public_absolute_url(domain_name=domain, path_or_url=cover_image)
        text = f'📰 <b>{title}</b>\n\n{preview}\n\n🔗 <a href="{link}">Читать далее на сайте</a>'

        try:
            log.bind(article_id=article_id, chat_id=chat_id).info("AnnouncementPublishStarted")
            await sender.send_or_replace_html(
                session_key=self._news_session_key(article_id),
                chat_id=chat_id,
                text=text,
                link=link,
                photo_url=photo_url,
            )
        except Exception:
            log.bind(article_id=article_id, chat_id=chat_id).exception("AnnouncementPublishFailed")
            raise

    async def process_news_unpublished(self, payload: dict[str, Any]) -> None:
        """Deletes a previously sent Telegram announcement for unpublished news."""
        article_id = str(payload.get("id", "")).strip()
        if not article_id:
            log.warning("AnnouncementDeletePayloadInvalid")
            return

        chat_id = self.container.settings.telegram_channel_id
        if not chat_id:
            log.warning("AnnouncementDeleteSkipped")
            return

        await self.container.media_sender.delete(session_key=self._news_session_key(article_id), chat_id=chat_id)

    async def render_content(
        self, director: Director | None = None, payload: Any = None
    ) -> ViewResultDTO | UnifiedViewDTO:
        """Incoming data processing for the background worker."""
        log.bind(event_type=payload.get("type") if isinstance(payload, dict) else None).debug(
            "AnnouncementPayloadHandled"
        )
        return ViewResultDTO(text="OK")

    @staticmethod
    def _news_session_key(article_id: str) -> str:
        return f"news:{article_id}"

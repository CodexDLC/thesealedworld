from __future__ import annotations

from typing import TYPE_CHECKING, Any

from codex_bot.base import UnifiedViewDTO, ViewResultDTO
from loguru import logger as log
from tg_bot.features.redis.announcements.storage import TelegramMessageStore
from tg_bot.sender import TelegramMediaSender

if TYPE_CHECKING:
    from codex_bot.director.director import Director


class AnnouncementsOrchestrator:
    """Orchestrator for the background feature Announcements (Redis)."""

    def __init__(self, container: Any) -> None:
        self.container = container
        self.message_store = TelegramMessageStore(container.redis_client)
        self.sender = TelegramMediaSender(container.bot)

    async def process_news(self, payload: dict[str, Any]) -> None:
        """Processes published news events and posts announcements to the Telegram channel.

        The payload contains: title, slug, preview, and optional cover_image.
        """
        chat_id = self.container.settings.telegram_channel_id
        if not chat_id:
            log.warning("AnnouncementsOrchestrator | TELEGRAM_CHANNEL_ID is not configured. Skipping publication.")
            return

        title = payload.get("title", "")
        preview = payload.get("preview", "")
        slug = payload.get("slug", "")
        cover_image = payload.get("cover_image", "")
        article_id = str(payload.get("id", "")).strip()
        if not article_id:
            log.warning("AnnouncementsOrchestrator | news.published payload has no article id. Skipping publication.")
            return

        domain = self.container.settings.domain_name
        link = self.sender.build_absolute_url(domain=domain, path_or_url=f"/news/{slug}")
        photo_url = self.sender.build_absolute_url(domain=domain, path_or_url=cover_image)
        text = f'📰 <b>{title}</b>\n\n{preview}\n\n🔗 <a href="{link}">Читать далее на сайте</a>'

        try:
            await self._delete_stored_message(scope="news", entity_id=article_id)

            log.info(f"AnnouncementsOrchestrator | Sending announcement to channel {chat_id}.")
            result = await self.sender.send_html(chat_id=chat_id, text=text, link=link, photo_url=photo_url)

            await self.message_store.save(
                scope="news",
                entity_id=article_id,
                chat_id=result.chat_id,
                message_id=result.message_id,
                slug=slug,
                kind=result.kind,
            )
        except Exception as e:
            log.error(f"AnnouncementsOrchestrator | Failed to send telegram announcement: {e}")
            raise

    async def process_news_unpublished(self, payload: dict[str, Any]) -> None:
        article_id = str(payload.get("id", "")).strip()
        if not article_id:
            log.warning("AnnouncementsOrchestrator | news.unpublished payload has no article id. Skipping deletion.")
            return

        await self._delete_stored_message(scope="news", entity_id=article_id)

    async def _delete_stored_message(self, *, scope: str, entity_id: str) -> None:
        stored = await self.message_store.get(scope=scope, entity_id=entity_id)
        if not stored:
            return

        chat_id = stored.get("chat_id")
        message_id = stored.get("message_id")
        if chat_id and message_id:
            try:
                await self.sender.delete(chat_id=chat_id, message_id=message_id)
                log.info(
                    f"AnnouncementsOrchestrator | Deleted stored Telegram message scope='{scope}' entity_id='{entity_id}'"
                )
            except Exception as e:
                log.warning(
                    f"AnnouncementsOrchestrator | Failed to delete Telegram message "
                    f"scope='{scope}' entity_id='{entity_id}': {e}"
                )

        await self.message_store.delete(scope=scope, entity_id=entity_id)

    async def render_content(
        self, director: "Director" | None = None, payload: Any = None
    ) -> ViewResultDTO | UnifiedViewDTO:
        """
        Incoming data processing for the background worker.
        """
        log.debug(f"AnnouncementsOrchestrator | Handling payload: {payload}")
        return ViewResultDTO(text="OK")

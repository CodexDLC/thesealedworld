from typing import TYPE_CHECKING, Any

from codex_bot.base import UnifiedViewDTO, ViewResultDTO
from loguru import logger as log

if TYPE_CHECKING:
    from codex_bot.director.director import Director


class AnnouncementsOrchestrator:
    """Orchestrator for the background feature Announcements (Redis)."""

    def __init__(self, container: Any) -> None:
        self.container = container

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

        # Format URL
        domain = self.container.settings.domain_name
        if not domain.startswith(("http://", "https://")):
            protocol = "http://" if "localhost" in domain or "127.0.0.1" in domain else "https://"
            link = f"{protocol}{domain}/news/{slug}"
        else:
            link = f"{domain}/news/{slug}"

        # Format HTML message
        text = f'📰 <b>{title}</b>\n\n{preview}\n\n🔗 <a href="{link}">Читать далее на сайте</a>'

        try:
            # Handle cover image URL if provided
            has_valid_photo = False
            photo_url = ""
            if cover_image:
                if cover_image.startswith(("http://", "https://")):
                    photo_url = cover_image
                    has_valid_photo = True
                else:
                    # Resolve relative path using domain_name
                    base_domain = domain
                    if base_domain.startswith(("http://", "https://")):
                        from urllib.parse import urlparse

                        parsed = urlparse(base_domain)
                        base_domain = parsed.netloc

                    protocol = "http://" if "localhost" in base_domain or "127.0.0.1" in base_domain else "https://"
                    photo_url = f"{protocol}{base_domain}{'/' if not cover_image.startswith('/') else ''}{cover_image}"

                    # Telegram servers cannot fetch from localhost/127.0.0.1
                    if "localhost" not in photo_url and "127.0.0.1" not in photo_url:
                        has_valid_photo = True

            if has_valid_photo:
                log.info(f"AnnouncementsOrchestrator | Sending photo to channel {chat_id} with caption.")
                await self.container.bot.send_photo(chat_id=chat_id, photo=photo_url, caption=text, parse_mode="HTML")
            else:
                log.info(f"AnnouncementsOrchestrator | Sending HTML text to channel {chat_id}.")
                await self.container.bot.send_message(
                    chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=False
                )
        except Exception as e:
            log.error(f"AnnouncementsOrchestrator | Failed to send telegram announcement: {e}")
            raise

    async def render_content(
        self, director: "Director" | None = None, payload: Any = None
    ) -> ViewResultDTO | UnifiedViewDTO:
        """
        Incoming data processing for the background worker.
        """
        log.debug(f"AnnouncementsOrchestrator | Handling payload: {payload}")
        return ViewResultDTO(text="OK")

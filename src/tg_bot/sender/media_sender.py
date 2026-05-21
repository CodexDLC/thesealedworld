from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import Message


@dataclass(frozen=True)
class MediaSendResult:
    chat_id: str
    message_id: str
    kind: str
    link: str
    photo_url: str


class TelegramMediaSender:
    """Sends channel-style Telegram messages with optional public images."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def send_html(
        self,
        *,
        chat_id: int | str,
        text: str,
        link: str,
        photo_url: str = "",
    ) -> MediaSendResult:
        if self._is_public_photo_url(photo_url):
            message = await self.bot.send_photo(chat_id=chat_id, photo=photo_url, caption=text, parse_mode="HTML")
            return self._result(chat_id=chat_id, message=message, kind="photo", link=link, photo_url=photo_url)

        message = await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=False,
        )
        return self._result(chat_id=chat_id, message=message, kind="message", link=link, photo_url=photo_url)

    async def delete(self, *, chat_id: int | str, message_id: int | str) -> None:
        await self.bot.delete_message(chat_id=chat_id, message_id=int(message_id))

    @staticmethod
    def build_absolute_url(*, domain: str, path_or_url: str) -> str:
        if not path_or_url:
            return ""
        if path_or_url.startswith(("http://", "https://")):
            return path_or_url

        base_domain = domain
        if base_domain.startswith(("http://", "https://")):
            from urllib.parse import urlparse

            parsed = urlparse(base_domain)
            base_domain = parsed.netloc

        protocol = "http://" if "localhost" in base_domain or "127.0.0.1" in base_domain else "https://"
        separator = "" if path_or_url.startswith("/") else "/"
        return f"{protocol}{base_domain}{separator}{path_or_url}"

    @staticmethod
    def _is_public_photo_url(photo_url: str) -> bool:
        if not photo_url.startswith(("http://", "https://")):
            return False
        return "localhost" not in photo_url and "127.0.0.1" not in photo_url

    @staticmethod
    def _result(
        *,
        chat_id: int | str,
        message: Message,
        kind: str,
        link: str,
        photo_url: str,
    ) -> MediaSendResult:
        return MediaSendResult(
            chat_id=str(chat_id),
            message_id=str(message.message_id),
            kind=kind,
            link=link,
            photo_url=photo_url,
        )

from __future__ import annotations

import contextlib
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
from codex_bot.sender.sender_manager import SenderManager


@dataclass(frozen=True)
class MediaSendResult:
    chat_id: str
    message_id: str
    kind: str
    link: str
    photo_url: str


class TelegramMediaSender:
    """Persistent sender for channel-style Telegram messages with optional media."""

    def __init__(self, bot: Bot, manager: SenderManager) -> None:
        self.bot = bot
        self.manager = manager

    async def send_or_replace_html(
        self,
        *,
        session_key: int | str,
        chat_id: int | str,
        text: str,
        link: str,
        photo_url: str = "",
        is_channel: bool = True,
    ) -> MediaSendResult:
        await self.delete(session_key=session_key, chat_id=chat_id, is_channel=is_channel)

        if self._is_public_photo_url(photo_url):
            message = await self.bot.send_photo(chat_id=chat_id, photo=photo_url, caption=text, parse_mode="HTML")
            result = self._result(chat_id=chat_id, message=message, kind="photo", link=link, photo_url=photo_url)
        else:
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=False,
            )
            result = self._result(chat_id=chat_id, message=message, kind="message", link=link, photo_url=photo_url)

        await self.manager.update_coords(session_key, {"media_msg_id": int(result.message_id)}, is_channel)
        return result

    async def delete(self, *, session_key: int | str, chat_id: int | str, is_channel: bool = True) -> None:
        coords = await self.manager.get_coords(session_key, is_channel)
        message_id = coords.get("media_msg_id")
        if message_id:
            with contextlib.suppress(TelegramAPIError):
                await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
        await self.manager.clear_coords(session_key, is_channel)

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

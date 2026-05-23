from __future__ import annotations

import contextlib
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import InputMediaPhoto, Message
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
        coords = await self.manager.get_coords(session_key, is_channel)
        old_message_id = coords.get("media_msg_id")

        if old_message_id:
            edited = await self._try_edit_existing(
                message_id=old_message_id,
                chat_id=chat_id,
                text=text,
                link=link,
                photo_url=photo_url,
            )
            if edited:
                await self.manager.update_coords(session_key, {"media_msg_id": int(edited.message_id)}, is_channel)
                return edited

        result = await self._send_new_html(chat_id=chat_id, text=text, link=link, photo_url=photo_url)

        await self.manager.update_coords(session_key, {"media_msg_id": int(result.message_id)}, is_channel)
        if old_message_id and int(result.message_id) != int(old_message_id):
            await self._delete_message(chat_id=chat_id, message_id=old_message_id)
        return result

    async def delete(self, *, session_key: int | str, chat_id: int | str, is_channel: bool = True) -> None:
        coords = await self.manager.get_coords(session_key, is_channel)
        message_id = coords.get("media_msg_id")
        if message_id:
            await self._delete_message(chat_id=chat_id, message_id=message_id)
        await self.manager.clear_coords(session_key, is_channel)

    async def _try_edit_existing(
        self,
        *,
        message_id: int,
        chat_id: int | str,
        text: str,
        link: str,
        photo_url: str,
    ) -> MediaSendResult | None:
        kind = "photo" if self._is_public_photo_url(photo_url) else "message"
        try:
            if kind == "photo":
                media = InputMediaPhoto(media=photo_url, caption=text, parse_mode="HTML")
                edited = await self.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media)
            else:
                edited = await self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    parse_mode="HTML",
                )
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                return None
            return MediaSendResult(
                chat_id=str(chat_id),
                message_id=str(message_id),
                kind=kind,
                link=link,
                photo_url=photo_url,
            )
        except TelegramAPIError:
            return None

        edited_message_id = getattr(edited, "message_id", message_id)
        return MediaSendResult(
            chat_id=str(chat_id),
            message_id=str(edited_message_id),
            kind=kind,
            link=link,
            photo_url=photo_url,
        )

    async def _send_new_html(
        self,
        *,
        chat_id: int | str,
        text: str,
        link: str,
        photo_url: str,
    ) -> MediaSendResult:
        if self._is_public_photo_url(photo_url):
            with contextlib.suppress(TelegramAPIError):
                message = await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo_url,
                    caption=text,
                    parse_mode="HTML",
                )
                return self._result(chat_id=chat_id, message=message, kind="photo", link=link, photo_url=photo_url)

        message = await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=False,
        )
        return self._result(chat_id=chat_id, message=message, kind="message", link=link, photo_url=photo_url)

    async def _delete_message(self, *, chat_id: int | str, message_id: int) -> None:
        with contextlib.suppress(TelegramAPIError):
            await self.bot.delete_message(chat_id=chat_id, message_id=message_id)

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

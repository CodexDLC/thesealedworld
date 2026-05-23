from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from aiogram.exceptions import TelegramBadRequest

from src.tg_bot.sender.media_sender import TelegramMediaSender


@dataclass
class FakeMessage:
    message_id: int


class FakeManager:
    def __init__(self, coords: dict[str, int] | None = None) -> None:
        self.coords = dict(coords or {})
        self.updates: list[tuple[int | str, dict[str, int], bool]] = []
        self.cleared: list[tuple[int | str, bool]] = []

    async def get_coords(self, session_key: int | str, is_channel: bool = False) -> dict[str, int]:
        return dict(self.coords)

    async def update_coords(
        self, session_key: int | str, coords: dict[str, int], is_channel: bool = False
    ) -> None:
        self.updates.append((session_key, dict(coords), is_channel))
        self.coords.update(coords)

    async def clear_coords(self, session_key: int | str, is_channel: bool = False) -> None:
        self.cleared.append((session_key, is_channel))
        self.coords = {}


class FakeBot:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.next_message_id = 100
        self.fail_edit_media = False
        self.fail_send_photo = False

    async def edit_message_media(self, **kwargs: Any) -> FakeMessage:
        self.calls.append(("edit_message_media", kwargs))
        if self.fail_edit_media:
            raise TelegramBadRequest(method=None, message="wrong type of the web page content")
        return FakeMessage(message_id=int(kwargs["message_id"]))

    async def edit_message_text(self, **kwargs: Any) -> FakeMessage:
        self.calls.append(("edit_message_text", kwargs))
        return FakeMessage(message_id=int(kwargs["message_id"]))

    async def send_photo(self, **kwargs: Any) -> FakeMessage:
        self.calls.append(("send_photo", kwargs))
        if self.fail_send_photo:
            raise TelegramBadRequest(method=None, message="wrong type of the web page content")
        self.next_message_id += 1
        return FakeMessage(message_id=self.next_message_id)

    async def send_message(self, **kwargs: Any) -> FakeMessage:
        self.calls.append(("send_message", kwargs))
        self.next_message_id += 1
        return FakeMessage(message_id=self.next_message_id)

    async def delete_message(self, **kwargs: Any) -> None:
        self.calls.append(("delete_message", kwargs))


@pytest.mark.asyncio
async def test_media_sender_edits_existing_photo_without_delete() -> None:
    bot = FakeBot()
    manager = FakeManager({"media_msg_id": 42})
    sender = TelegramMediaSender(bot=bot, manager=manager)

    result = await sender.send_or_replace_html(
        session_key="news:1",
        chat_id="-100",
        text="<b>Title</b>",
        link="https://example.test/news/one",
        photo_url="https://example.test/news/cover.png",
    )

    assert result.message_id == "42"
    assert result.kind == "photo"
    assert [call[0] for call in bot.calls] == ["edit_message_media"]
    assert manager.updates == [("news:1", {"media_msg_id": 42}, True)]
    assert manager.cleared == []


@pytest.mark.asyncio
async def test_media_sender_falls_back_to_text_before_deleting_old_message() -> None:
    bot = FakeBot()
    bot.fail_edit_media = True
    bot.fail_send_photo = True
    manager = FakeManager({"media_msg_id": 42})
    sender = TelegramMediaSender(bot=bot, manager=manager)

    result = await sender.send_or_replace_html(
        session_key="news:1",
        chat_id="-100",
        text="<b>Title</b>",
        link="https://example.test/news/one",
        photo_url="https://example.test/news/bad-cover.png",
    )

    assert result.message_id == "101"
    assert result.kind == "message"
    assert [call[0] for call in bot.calls] == [
        "edit_message_media",
        "send_photo",
        "send_message",
        "delete_message",
    ]
    assert bot.calls[-1] == ("delete_message", {"chat_id": "-100", "message_id": 42})
    assert manager.updates == [("news:1", {"media_msg_id": 101}, True)]
    assert manager.cleared == []


@pytest.mark.asyncio
async def test_media_sender_sends_text_fallback_when_initial_photo_send_fails() -> None:
    bot = FakeBot()
    bot.fail_send_photo = True
    manager = FakeManager()
    sender = TelegramMediaSender(bot=bot, manager=manager)

    result = await sender.send_or_replace_html(
        session_key="news:1",
        chat_id="-100",
        text="<b>Title</b>",
        link="https://example.test/news/one",
        photo_url="https://example.test/news/bad-cover.png",
    )

    assert result.message_id == "101"
    assert result.kind == "message"
    assert [call[0] for call in bot.calls] == ["send_photo", "send_message"]
    assert manager.updates == [("news:1", {"media_msg_id": 101}, True)]
    assert manager.cleared == []


@pytest.mark.asyncio
async def test_media_sender_delete_removes_saved_message_and_clears_coords() -> None:
    bot = FakeBot()
    manager = FakeManager({"media_msg_id": 42})
    sender = TelegramMediaSender(bot=bot, manager=manager)

    await sender.delete(session_key="news:1", chat_id="-100")

    assert bot.calls == [("delete_message", {"chat_id": "-100", "message_id": 42})]
    assert manager.updates == []
    assert manager.cleared == [("news:1", True)]

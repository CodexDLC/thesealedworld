"""Stage 1 removes the chat-system-tab mirror of combat log entries.

These tests pin the chat side: the ``chat.combat_log_message`` handler is no
longer registered and ``MessageService.push_combat_log`` is gone. The combat
channel tab path (``push_combat`` + ``chat.combat_message``) remains
untouched, so the combat-channel UI keeps working.
"""

from __future__ import annotations

import pytest

from src.backend.chat.events import ChatEvents, router
from src.backend.chat.services.message_service import MessageService


@pytest.mark.unit
def test_chat_events_no_longer_exposes_combat_log_constant() -> None:
    assert not hasattr(ChatEvents, "COMBAT_LOG_MESSAGE")


@pytest.mark.unit
def test_stream_router_has_no_combat_log_handler() -> None:
    # The chat StreamRouter only routes events whose ``type`` it has a
    # subscriber for. After stage 1, no chat subscriber for the legacy
    # combat-log mirror.
    handlers = getattr(router, "_handlers", None) or getattr(router, "handlers", None) or {}
    keys: list[str] = []
    if isinstance(handlers, dict):
        keys = list(handlers.keys())
    else:
        for h in handlers:
            event = getattr(h, "event", None) or getattr(h, "event_type", None)
            if event:
                keys.append(event)
    assert "chat.combat_log_message" not in keys


@pytest.mark.unit
def test_message_service_has_no_push_combat_log_method() -> None:
    assert not hasattr(MessageService, "push_combat_log")


@pytest.mark.unit
def test_message_service_keeps_push_combat_channel_method() -> None:
    # Combat *channel* tab path (distinct from system mirroring) is preserved.
    assert hasattr(MessageService, "push_combat")
    assert hasattr(MessageService, "handle_incoming")


@pytest.mark.unit
def test_chat_events_keeps_combat_channel_constant() -> None:
    assert ChatEvents.COMBAT_MESSAGE == "chat.combat_message"
    assert ChatEvents.SYSTEM_MESSAGE == "chat.system_message"

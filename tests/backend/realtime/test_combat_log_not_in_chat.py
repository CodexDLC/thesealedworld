"""Combat does not flow through the chat channels.

These tests pin the chat side:
- the legacy ``chat.combat_log_message`` mirror handler / ``push_combat_log`` are gone;
- the combat *chat tab* path (``push_combat`` + ``chat.combat_message``) is also
  gone — combat start/finish/refresh reach the player via ``player.notice`` only,
  and there is no per-combat chat channel. In-combat talk uses the location/world
  chat. See docs and ``src/backend/realtime/integrations/notice_publisher.py``.
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
def test_message_service_has_no_push_combat_method() -> None:
    # The per-combat chat channel is removed; only system/incoming paths remain.
    assert not hasattr(MessageService, "push_combat")
    assert hasattr(MessageService, "handle_incoming")
    assert hasattr(MessageService, "push_system")


@pytest.mark.unit
def test_chat_events_no_longer_exposes_combat_channel_constant() -> None:
    assert not hasattr(ChatEvents, "COMBAT_MESSAGE")
    assert ChatEvents.SYSTEM_MESSAGE == "chat.system_message"


@pytest.mark.unit
def test_stream_router_has_no_combat_message_handler() -> None:
    handlers = getattr(router, "_handlers", None) or getattr(router, "handlers", None) or {}
    keys: list[str] = []
    if isinstance(handlers, dict):
        keys = list(handlers.keys())
    else:
        for h in handlers:
            event = getattr(h, "event", None) or getattr(h, "event_type", None)
            if event:
                keys.append(event)
    assert "chat.combat_message" not in keys

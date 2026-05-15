from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InboxMessageState:
    id: str
    subject: str
    body: str
    event_type: str  # "system" | "registration" | "game"
    is_read: bool
    created_at: str  # pre-formatted for display


@dataclass
class InboxListState:
    messages: list[InboxMessageState]
    unread_count: int = 0
    empty_message: str = "Входящих сообщений нет"

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class MailingStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"


@dataclass(frozen=True)
class MailingRowState:
    id: str
    subject: str
    status: MailingStatus
    recipient_count: int
    sent_at: str  # pre-formatted, empty string if not sent
    url: str = ""


@dataclass
class MailingListState:
    rows: list[MailingRowState] = field(default_factory=list)
    empty_message: str = "Рассылок нет"

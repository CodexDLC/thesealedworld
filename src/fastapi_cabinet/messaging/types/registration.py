from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RegistrationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


@dataclass(frozen=True)
class RegistrationRequestState:
    id: str
    email: str
    username: str
    status: RegistrationStatus
    submitted_at: str  # pre-formatted for display
    approve_url: str = ""
    deny_url: str = ""


@dataclass
class RegistrationListState:
    rows: list[RegistrationRequestState] = field(default_factory=list)
    pending_count: int = 0
    empty_message: str = "Заявок нет"

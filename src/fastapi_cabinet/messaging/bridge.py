from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from fastapi import Request

    from fastapi_cabinet.messaging.types import (
        InboxListState,
        MailingListState,
        RegistrationListState,
    )


@dataclass(frozen=True)
class MessagingActionResult:
    ok: bool
    code: str
    message: str


@runtime_checkable
class MessagingBridge(Protocol):
    async def get_inbox_state(self, *, request: Request) -> InboxListState: ...
    async def get_mailing_list_state(self, *, request: Request) -> MailingListState: ...
    async def get_registration_list_state(self, *, request: Request) -> RegistrationListState: ...
    async def approve_registration(self, *, request: Request, request_id: str) -> MessagingActionResult: ...
    async def deny_registration(self, *, request: Request, request_id: str) -> MessagingActionResult: ...


__all__ = ["MessagingActionResult", "MessagingBridge"]

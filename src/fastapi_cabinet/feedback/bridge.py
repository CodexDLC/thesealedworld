from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from fastapi import Request

    from fastapi_cabinet.feedback.types import FeedbackListState


@dataclass(frozen=True)
class FeedbackActionResult:
    ok: bool
    code: str
    message: str


@runtime_checkable
class FeedbackBridge(Protocol):
    async def get_feedback_list_state(
        self, *, request: Request, type_filter: str | None = None,
    ) -> FeedbackListState: ...

    async def update_feedback_status(
        self, *, request: Request, feedback_id: str, status: str,
    ) -> FeedbackActionResult: ...


__all__ = ["FeedbackActionResult", "FeedbackBridge"]

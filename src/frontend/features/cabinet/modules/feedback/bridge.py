from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi_cabinet.feedback.bridge import FeedbackActionResult
from fastapi_cabinet.feedback.types import FeedbackItemState, FeedbackListState

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import Request

    from src.frontend.features.feedback.repositories.feedback_repository import FeedbackRepository


class SiteFeedbackBridge:
    def __init__(self, repo: FeedbackRepository | None = None) -> None:
        self._repo = repo

    @asynccontextmanager
    async def _get_repo(self) -> AsyncGenerator[FeedbackRepository]:
        if self._repo is not None:
            yield self._repo
            return
        from src.frontend.core.database.session import get_session_context
        from src.frontend.features.feedback.repositories.feedback_repository import FeedbackRepository

        async with get_session_context() as session:
            yield FeedbackRepository(session=session)

    async def get_feedback_list_state(
        self,
        *,
        request: Request,
        type_filter: str | None = None,
    ) -> FeedbackListState:
        async with self._get_repo() as repo:
            if type_filter:
                items = await repo.get_by_type(type_filter)
            else:
                items = await repo.get_all()

        rows = [
            FeedbackItemState(
                id=str(f.id),
                email="",
                type=f.type,
                title=f.title,
                body=f.body,
                status=f.status,
                priority=f.priority,
                created_at=f.created_at.strftime("%d.%m.%Y %H:%M"),
            )
            for f in items
        ]
        new_count = sum(1 for f in items if f.status == "new")
        return FeedbackListState(rows=rows, total_count=len(rows), new_count=new_count)

    async def update_feedback_status(
        self,
        *,
        request: Request,
        feedback_id: str,
        status: str,
    ) -> FeedbackActionResult:
        async with self._get_repo() as repo:
            fb = await repo.get_by_id(int(feedback_id))
            if fb is None:
                return FeedbackActionResult(ok=False, code="not_found", message="Фидбек не найден")
            await repo.update_status(int(feedback_id), status)
            await repo.commit()
        return FeedbackActionResult(ok=True, code="updated", message=f"Статус обновлён на {status}")

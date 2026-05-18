from __future__ import annotations

from typing import TYPE_CHECKING

from src.frontend.features.feedback.models.feedback import Feedback
from src.shared.exceptions import BusinessLogicException

if TYPE_CHECKING:
    import uuid

    from src.frontend.features.feedback.dto.feedback_dto import FeedbackCreate
    from src.frontend.features.feedback.repositories.feedback_repository import FeedbackRepository


class FeedbackService:
    def __init__(self, repo: FeedbackRepository) -> None:
        self._repo = repo

    async def submit(self, *, user_id: uuid.UUID, tester_status: str, data: FeedbackCreate) -> Feedback:
        if tester_status != "approved":
            raise BusinessLogicException(detail="Only approved testers can submit feedback")
        if data.priority and data.type != "bug":
            raise BusinessLogicException(detail="Priority is only allowed for bug reports")

        feedback = Feedback(
            user_id=user_id,
            type=data.type,
            title=data.title,
            body=data.body,
            priority=data.priority if data.type == "bug" else None,
            status="new",
        )
        created = await self._repo.create(feedback)
        await self._repo.commit()
        return created

    async def list_user_feedback(self, user_id: uuid.UUID) -> list[Feedback]:
        return await self._repo.get_by_user(user_id)

    async def get_feedback(self, feedback_id: int) -> Feedback | None:
        return await self._repo.get_by_id(feedback_id)

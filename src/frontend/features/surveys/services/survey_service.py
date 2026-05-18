from __future__ import annotations

import json
import secrets
from typing import TYPE_CHECKING

from src.frontend.features.surveys.models.survey import Survey, SurveyQuestion, SurveyResponse, SurveySend
from src.shared.exceptions import BusinessLogicException

if TYPE_CHECKING:
    import uuid

    from src.frontend.features.surveys.repositories.survey_repository import SurveyRepository


class SurveyService:
    def __init__(self, repo: SurveyRepository) -> None:
        self._repo = repo

    async def create_survey(
        self, *, title: str, description: str | None, questions: list[dict],
    ) -> Survey:
        survey = Survey(title=title, description=description)
        for i, q in enumerate(questions):
            sq = SurveyQuestion(
                text=q["text"],
                question_type=q.get("question_type", "text"),
                choices_json=json.dumps(q["choices"]) if q.get("choices") else None,
                order=i,
            )
            survey.questions.append(sq)
        created = await self._repo.create_survey(survey)
        await self._repo.commit()
        return created

    async def send_to_user(self, *, survey_id: int, user_id: uuid.UUID) -> SurveySend:
        token = secrets.token_urlsafe(32)
        send = SurveySend(survey_id=survey_id, user_id=user_id, token=token)
        created = await self._repo.create_send(send)
        await self._repo.commit()
        return created

    async def get_survey_by_token(self, token: str) -> SurveySend | None:
        return await self._repo.get_send_by_token(token)

    async def submit_response(self, *, token: str, answers: dict) -> SurveyResponse:
        send = await self._repo.get_send_by_token(token)
        if send is None:
            raise BusinessLogicException(detail="Invalid survey token")
        if send.response is not None:
            raise BusinessLogicException(detail="Survey already completed")

        response = SurveyResponse(
            send_id=send.id,
            answers_json=json.dumps(answers, ensure_ascii=False),
        )
        created = await self._repo.create_response(response)
        await self._repo.commit()
        return created

    async def get_user_surveys(self, user_id: uuid.UUID) -> list[SurveySend]:
        return await self._repo.get_sends_for_user(user_id)

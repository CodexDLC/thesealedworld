from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.frontend.features.surveys.models.survey import Survey, SurveyResponse, SurveySend

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class SurveyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_survey(self, survey: Survey) -> Survey:
        self.session.add(survey)
        await self.session.flush()
        await self.session.refresh(survey)
        return survey

    async def get_survey(self, survey_id: int) -> Survey | None:
        result = await self.session.execute(
            select(Survey).options(selectinload(Survey.questions)).where(Survey.id == survey_id)
        )
        return result.scalar_one_or_none()

    async def get_all_surveys(self) -> list[Survey]:
        result = await self.session.execute(select(Survey).order_by(Survey.created_at.desc()))
        return list(result.scalars().all())

    async def create_send(self, send: SurveySend) -> SurveySend:
        self.session.add(send)
        await self.session.flush()
        await self.session.refresh(send)
        return send

    async def get_send_by_token(self, token: str) -> SurveySend | None:
        result = await self.session.execute(
            select(SurveySend)
            .options(selectinload(SurveySend.survey).selectinload(Survey.questions))
            .options(selectinload(SurveySend.response))
            .where(SurveySend.token == token)
        )
        return result.scalar_one_or_none()

    async def get_sends_for_user(self, user_id: uuid.UUID) -> list[SurveySend]:
        result = await self.session.execute(
            select(SurveySend)
            .options(selectinload(SurveySend.survey))
            .options(selectinload(SurveySend.response))
            .where(SurveySend.user_id == user_id)
            .order_by(SurveySend.sent_at.desc())
        )
        return list(result.scalars().all())

    async def create_response(self, response: SurveyResponse) -> SurveyResponse:
        self.session.add(response)
        await self.session.flush()
        await self.session.refresh(response)
        return response

    async def commit(self) -> None:
        await self.session.commit()

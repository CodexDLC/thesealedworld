from collections import defaultdict

from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.features.actor_state.models import SkillProgress
from src.shared.schemas.skill import SkillProgressDTO


class SkillProgressRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_skills_progress_batch(self, char_ids: list[int]) -> dict[int, list[SkillProgressDTO]]:
        log.debug(f"SkillProgressRepository | action=get_all_skills_progress_batch count={len(char_ids)}")
        if not char_ids:
            return {}

        stmt = select(SkillProgress).where(SkillProgress.character_id.in_(char_ids))
        try:
            result = await self.session.scalars(stmt)
            grouped_skills: dict[int, list[SkillProgressDTO]] = defaultdict(list)
            for skill in result.all():
                grouped_skills[skill.character_id].append(SkillProgressDTO.model_validate(skill))
            return dict(grouped_skills)
        except SQLAlchemyError as exc:
            log.exception(f"SkillProgressRepository | action=get_all_skills_progress_batch status=failed error={exc}")
            raise


SkillProgressRepo = SkillProgressRepository

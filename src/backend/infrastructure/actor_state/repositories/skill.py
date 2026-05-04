from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import SkillProgress


class SkillRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_character_id(self, char_id: int) -> list[SkillProgress]:
        log.debug(f"SkillRepository | action=get_by_character_id char_id={char_id}")
        stmt = select(SkillProgress).where(SkillProgress.character_id == char_id)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_all_skills_progress_batch(self, char_ids: list[int]) -> dict[int, list[SkillProgress]]:
        log.debug(f"SkillRepository | action=get_all_skills_progress_batch count={len(char_ids)}")
        if not char_ids:
            return {}
        stmt = select(SkillProgress).where(SkillProgress.character_id.in_(char_ids))
        result = await self.session.scalars(stmt)
        skills = list(result.all())
        
        by_id: dict[int, list[SkillProgress]] = {char_id: [] for char_id in char_ids}
        for skill in skills:
            by_id[skill.character_id].append(skill)
        return by_id

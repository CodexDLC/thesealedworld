from typing import Any

from loguru import logger as log
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.features.character.models import SkillProgress
from src.shared.enums.skill_enums import SkillProgressState


class SkillRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_character_id(self, char_id: int) -> list[SkillProgress]:
        log.bind(char_id=char_id).debug("SkillRepositoryGetByCharacterId")
        stmt = select(SkillProgress).where(SkillProgress.character_id == char_id)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def upsert_progress_rows(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return

        stmt = insert(SkillProgress).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[SkillProgress.character_id, SkillProgress.skill_key],
            set_={
                "total_xp": stmt.excluded.total_xp,
                "is_unlocked": stmt.excluded.is_unlocked,
                "progress_state": stmt.excluded.progress_state,
            },
        )
        await self.session.execute(stmt)

    async def increment_progress_rows(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return

        stmt = insert(SkillProgress).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[SkillProgress.character_id, SkillProgress.skill_key],
            set_={
                "total_xp": SkillProgress.total_xp + stmt.excluded.total_xp,
                "is_unlocked": True,
                "progress_state": stmt.excluded.progress_state,
            },
        )
        await self.session.execute(stmt)

    async def get_all_skills_progress_batch(self, char_ids: list[int]) -> dict[int, list[SkillProgress]]:
        log.bind(char_id_count=len(char_ids)).debug("SkillRepositoryGetAllSkillsProgressBatch")
        if not char_ids:
            return {}
        stmt = select(SkillProgress).where(SkillProgress.character_id.in_(char_ids))
        result = await self.session.scalars(stmt)
        skills = list(result.all())

        by_id: dict[int, list[SkillProgress]] = {char_id: [] for char_id in char_ids}
        for skill in skills:
            by_id[skill.character_id].append(skill)
        return by_id

    async def unlock_skills(
        self,
        char_id: int,
        skill_keys: list[str],
        *,
        progress_state: SkillProgressState = SkillProgressState.PLUS,
        initial_xp: float = 0.0,
    ) -> None:
        unique_skill_keys = list(dict.fromkeys(skill_key for skill_key in skill_keys if skill_key))
        if not unique_skill_keys:
            return

        starting_xp = min(1.0, max(0.0, float(initial_xp or 0.0)))
        rows = [
            {
                "character_id": char_id,
                "skill_key": skill_key,
                "total_xp": starting_xp,
                "is_unlocked": True,
                "progress_state": progress_state,
            }
            for skill_key in unique_skill_keys
        ]
        stmt = insert(SkillProgress).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[SkillProgress.character_id, SkillProgress.skill_key],
            set_={
                "total_xp": func.greatest(SkillProgress.total_xp, stmt.excluded.total_xp),
                "is_unlocked": True,
                "progress_state": progress_state,
            },
        )
        await self.session.execute(stmt)

from collections import defaultdict

from loguru import logger as log
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.db_contract.i_skill_repo import ISkillProgressRepo
from src.backend.database.postgres.models.skill import CharacterSkillProgress
from src.backend.resources.game_data import GameData
from src.shared.enums.skill_enums import SkillProgressState
from src.shared.schemas.skill import SkillProgressDTO


class SkillProgressRepo(ISkillProgressRepo):
    """
    ORM-реализация репозитория для прогресса навыков персонажа.

    Предоставляет методы для инициализации, добавления опыта,
    обновления состояния и получения прогресса навыков.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует SkillProgressRepo.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.session = session
        log.debug(f"SkillProgressRepo | status=initialized session={session}")

    async def initialize_all_base_skills(self, character_id: int) -> None:
        """
        Инициализирует записи для всех базовых навыков для нового персонажа.
        Использует GameData для получения списка всех доступных навыков.

        Args:
            character_id: Идентификатор персонажа, для которого инициализируются навыки.
        """
        log.debug(f"SkillProgressRepo | action=initialize_all_base_skills char_id={character_id}")

        # Получаем все навыки из библиотеки (они все считаются базовыми в v2.0)
        all_skills = GameData.get_all_skills()

        base_skills = [
            {"character_id": character_id, "skill_key": skill.skill_key, "total_xp": 0.0} for skill in all_skills
        ]

        if not base_skills:
            log.warning("SkillProgressRepo | action=initialize_all_base_skills reason='No skills found in GameData'")
            return

        stmt = pg_insert(CharacterSkillProgress).values(base_skills)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=[CharacterSkillProgress.character_id, CharacterSkillProgress.skill_key]
        )
        try:
            await self.session.execute(stmt)
            log.info(
                f"SkillProgressRepo | action=initialize_all_base_skills status=success count={len(base_skills)} char_id={character_id}"
            )
        except SQLAlchemyError as e:
            log.exception(
                f"SkillProgressRepo | action=initialize_all_base_skills status=failed char_id={character_id} error={e}"
            )
            raise

    async def add_skill_xp(self, character_id: int, skill_key: str, xp_to_add: float) -> SkillProgressDTO | None:
        """
        Атомарно добавляет опыт к указанному навыку персонажа и возвращает обновленный прогресс.

        Args:
            character_id: Идентификатор персонажа.
            skill_key: Ключ навыка.
            xp_to_add: Количество опыта для добавления (Float).

        Returns:
            Обновленный DTO `SkillProgressDTO` прогресса навыка,
            если запись найдена и обновлена. Иначе - None.
        """
        log.debug(
            f"SkillProgressRepo | action=add_skill_xp char_id={character_id} skill='{skill_key}' xp_to_add={xp_to_add}"
        )

        stmt_update = (
            update(CharacterSkillProgress)
            .where(CharacterSkillProgress.character_id == character_id, CharacterSkillProgress.skill_key == skill_key)
            .values(total_xp=CharacterSkillProgress.total_xp + xp_to_add)
        )
        stmt_select = select(CharacterSkillProgress).where(
            CharacterSkillProgress.character_id == character_id, CharacterSkillProgress.skill_key == skill_key
        )

        try:
            await self.session.execute(stmt_update)
            result = await self.session.execute(stmt_select)
            orm_progress = result.scalar_one_or_none()

            if orm_progress:
                log.debug(
                    f"SkillProgressRepo | action=add_skill_xp status=success char_id={character_id} skill='{skill_key}' new_xp={orm_progress.total_xp}"
                )
                return SkillProgressDTO.model_validate(orm_progress)

            log.warning(
                f"SkillProgressRepo | action=add_skill_xp status=failed reason='Skill not found after update' char_id={character_id} skill='{skill_key}'"
            )
            return None

        except SQLAlchemyError as e:
            log.exception(
                f"SkillProgressRepo | action=add_skill_xp status=failed char_id={character_id} skill='{skill_key}' error={e}"
            )
            raise

    async def update_skill_state(self, character_id: int, skill_key: str, state: SkillProgressState) -> None:
        """
        Обновляет состояние развития навыка (PLUS, PAUSE, MINUS).

        Args:
            character_id: Идентификатор персонажа.
            skill_key: Ключ навыка.
            state: Новое состояние навыка (Enum `SkillProgressState`).
        """
        log.debug(
            f"SkillProgressRepo | action=update_skill_state char_id={character_id} skill='{skill_key}' new_state='{state.name}'"
        )
        stmt = (
            update(CharacterSkillProgress)
            .where(CharacterSkillProgress.character_id == character_id, CharacterSkillProgress.skill_key == skill_key)
            .values(progress_state=state)
        )
        try:
            await self.session.execute(stmt)
            log.info(
                f"SkillProgressRepo | action=update_skill_state status=success char_id={character_id} skill='{skill_key}'"
            )
        except SQLAlchemyError as e:
            log.exception(
                f"SkillProgressRepo | action=update_skill_state status=failed char_id={character_id} skill='{skill_key}' error={e}"
            )
            raise

    async def update_skill_unlocked_state(self, character_id: int, skill_key_list: list[str], state: bool) -> None:
        """
        Массово обновляет статус `is_unlocked` для списка навыков персонажа.

        Args:
            character_id: Идентификатор персонажа, чьи навыки обновляются.
            skill_key_list: Список строковых ключей навыков.
            state: Новое состояние для `is_unlocked` (True - разблокирован, False - заблокирован).
        """
        log.debug(
            f"SkillProgressRepo | action=update_skill_unlocked_state char_id={character_id} skills={skill_key_list} new_state={state}"
        )
        stmt = (
            update(CharacterSkillProgress)
            .where(
                CharacterSkillProgress.character_id == character_id,
                CharacterSkillProgress.skill_key.in_(skill_key_list),
            )
            .values(is_unlocked=state)
        )

        try:
            await self.session.execute(stmt)
            log.info(
                f"SkillProgressRepo | action=update_skill_unlocked_state status=success char_id={character_id} skills={skill_key_list}"
            )
        except SQLAlchemyError as e:
            log.exception(
                f"SkillProgressRepo | action=update_skill_unlocked_state status=failed char_id={character_id} skills={skill_key_list} error={e}"
            )
            raise

    async def get_all_skills_progress(self, character_id: int) -> list[SkillProgressDTO]:
        """
        Возвращает прогресс всех навыков для одного персонажа.

        Args:
            character_id: Идентификатор персонажа.

        Returns:
            Список DTO `SkillProgressDTO` с прогрессом всех навыков.
        """
        log.debug(f"SkillProgressRepo | action=get_all_skills_progress char_id={character_id}")
        stmt = select(CharacterSkillProgress).where(CharacterSkillProgress.character_id == character_id)
        try:
            result = await self.session.scalars(stmt)
            orm_progress_list = result.all()
            log.debug(
                f"SkillProgressRepo | action=get_all_skills_progress status=found count={len(orm_progress_list)} char_id={character_id}"
            )
            return [SkillProgressDTO.model_validate(orm_progress) for orm_progress in orm_progress_list]
        except SQLAlchemyError as e:
            log.exception(
                f"SkillProgressRepo | action=get_all_skills_progress status=failed char_id={character_id} error={e}"
            )
            raise

    async def get_all_skills_progress_batch(self, character_ids: list[int]) -> dict[int, list[SkillProgressDTO]]:
        """
        Возвращает прогресс навыков для списка персонажей.

        Args:
            character_ids: Список ID персонажей.

        Returns:
            dict[int, list[SkillProgressDTO]]: Словарь {char_id: [skills]}.
        """
        log.debug(f"SkillProgressRepo | action=get_all_skills_progress_batch count={len(character_ids)}")
        if not character_ids:
            return {}
        stmt = select(CharacterSkillProgress).where(CharacterSkillProgress.character_id.in_(character_ids))
        try:
            result = await self.session.scalars(stmt)
            orm_progress_list = result.all()

            grouped_skills = defaultdict(list)
            for skill in orm_progress_list:
                grouped_skills[skill.character_id].append(SkillProgressDTO.model_validate(skill))

            return dict(grouped_skills)
        except SQLAlchemyError as e:
            log.exception(f"SkillProgressRepo | action=get_all_skills_progress_batch status=failed error={e}")
            raise

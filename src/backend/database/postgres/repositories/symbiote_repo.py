from loguru import logger as log
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.db_contract.i_symbiote_repo import ISymbioteRepo
from src.backend.database.postgres.models.symbiote import CharacterSymbiote


class SymbioteRepoORM(ISymbioteRepo):
    """
    ORM-реализация репозитория для управления сущностью Симбиота (`CharacterSymbiote`).

    Предоставляет методы для получения, обновления имени, установки Дара
    и обновления прогресса Симбиота с использованием SQLAlchemy ORM.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует SymbioteRepoORM.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.session = session
        log.debug(f"SymbioteRepoORM | status=initialized session={session}")

    async def get_symbiote(self, character_id: int) -> CharacterSymbiote | None:
        """
        Получает запись Симбиота по идентификатору персонажа.

        Args:
            character_id: Идентификатор персонажа.

        Returns:
            Объект `CharacterSymbiote`, если найден, иначе None.
        """
        log.debug(f"SymbioteRepoORM | action=get_symbiote char_id={character_id}")
        stmt = select(CharacterSymbiote).where(CharacterSymbiote.character_id == character_id)
        try:
            result = await self.session.execute(stmt)
            symbiote = result.scalar_one_or_none()
            if symbiote:
                log.debug(f"SymbioteRepoORM | action=get_symbiote status=found char_id={character_id}")
            else:
                log.debug(f"SymbioteRepoORM | action=get_symbiote status=not_found char_id={character_id}")
            return symbiote
        except SQLAlchemyError as e:
            log.exception(f"SymbioteRepoORM | action=get_symbiote status=failed char_id={character_id} error={e}")
            raise

    async def get_symbiotes_batch(self, character_ids: list[int]) -> list[CharacterSymbiote]:
        """
        Получает список Симбиотов для списка персонажей.

        Args:
            character_ids: Список идентификаторов персонажей.

        Returns:
            Список объектов `CharacterSymbiote`.
        """
        log.debug(f"SymbioteRepoORM | action=get_symbiotes_batch count={len(character_ids)}")
        if not character_ids:
            return []
        stmt = select(CharacterSymbiote).where(CharacterSymbiote.character_id.in_(character_ids))
        try:
            result = await self.session.execute(stmt)
            symbiotes = result.scalars().all()
            return list(symbiotes)
        except SQLAlchemyError as e:
            log.exception(f"SymbioteRepoORM | action=get_symbiotes_batch status=failed error={e}")
            raise

    async def update_name(self, character_id: int, new_name: str) -> None:
        """
        Обновляет имя Симбиота для указанного персонажа.

        Args:
            character_id: Идентификатор персонажа.
            new_name: Новое имя для Симбиота.
        """
        log.debug(f"SymbioteRepoORM | action=update_name char_id={character_id} new_name='{new_name}'")
        stmt = (
            update(CharacterSymbiote)
            .where(CharacterSymbiote.character_id == character_id)
            .values(symbiote_name=new_name)
        )
        try:
            await self.session.execute(stmt)
            log.info(
                f"SymbioteRepoORM | action=update_name status=success char_id={character_id} new_name='{new_name}'"
            )
        except SQLAlchemyError as e:
            log.exception(f"SymbioteRepoORM | action=update_name status=failed char_id={character_id} error={e}")
            raise

    async def set_gift(self, character_id: int, gift_id: str) -> None:
        """
        Устанавливает выбранный Дар (Gift) для Симбиота персонажа.

        Args:
            character_id: Идентификатор персонажа.
            gift_id: Идентификатор Дара.
        """
        log.debug(f"SymbioteRepoORM | action=set_gift char_id={character_id} gift_id='{gift_id}'")
        stmt = update(CharacterSymbiote).where(CharacterSymbiote.character_id == character_id).values(gift_id=gift_id)
        try:
            await self.session.execute(stmt)
            log.info(f"SymbioteRepoORM | action=set_gift status=success char_id={character_id} gift_id='{gift_id}'")
        except SQLAlchemyError as e:
            log.exception(f"SymbioteRepoORM | action=set_gift status=failed char_id={character_id} error={e}")
            raise

    async def update_progress(self, character_id: int, new_xp: int, new_rank: int) -> None:
        """
        Обновляет опыт и ранг Симбиота.

        Args:
            character_id: Идентификатор персонажа.
            new_xp: Новое значение опыта Симбиота.
            new_rank: Новый ранг Симбиота.
        """
        log.debug(
            f"SymbioteRepoORM | action=update_progress char_id={character_id} new_xp={new_xp} new_rank={new_rank}"
        )
        stmt = (
            update(CharacterSymbiote)
            .where(CharacterSymbiote.character_id == character_id)
            .values(gift_xp=new_xp, gift_rank=new_rank)
        )
        try:
            await self.session.execute(stmt)
            log.info(
                f"SymbioteRepoORM | action=update_progress status=success char_id={character_id} xp={new_xp} rank={new_rank}"
            )
        except SQLAlchemyError as e:
            log.exception(f"SymbioteRepoORM | action=update_progress status=failed char_id={character_id} error={e}")
            raise

    async def update_elements_resonance(self, character_id: int, new_resonance: dict) -> None:
        """
        Обновляет поле резонанса элементов (JSON).

        Полностью перезаписывает поле `elements_resonance` переданным словарем.

        Args:
            character_id: Идентификатор персонажа.
            new_resonance: Словарь с новыми значениями резонанса.
        """
        log.debug(
            f"SymbioteRepoORM | action=update_elements_resonance char_id={character_id} resonance={new_resonance}"
        )
        stmt = (
            update(CharacterSymbiote)
            .where(CharacterSymbiote.character_id == character_id)
            .values(elements_resonance=new_resonance)
        )
        try:
            await self.session.execute(stmt)
            log.info(f"SymbioteRepoORM | action=update_elements_resonance status=success char_id={character_id}")
        except SQLAlchemyError as e:
            log.exception(
                f"SymbioteRepoORM | action=update_elements_resonance status=failed char_id={character_id} error={e}"
            )
            raise

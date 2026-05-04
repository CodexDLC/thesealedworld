from loguru import logger as log
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.db_contract.i_leaderboard_repo import ILeaderboardRepo
from src.backend.database.postgres.models.leaderboard import Leaderboard


class LeaderboardRepoORM(ILeaderboardRepo):
    """
    ORM-реализация репозитория для управления записями в таблице лидеров.

    Предоставляет методы для создания и обновления агрегированных показателей
    персонажей, таких как Gear Score, опыт и PvP-рейтинг, с использованием SQLAlchemy ORM.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует LeaderboardRepoORM.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.session = session
        log.debug(f"LeaderboardRepoORM | status=initialized session={session}")

    async def update_score(
        self, character_id: int, gear_score: int | None = None, xp: int | None = None, rating: int | None = None
    ) -> None:
        """
        Создает новую запись или обновляет существующие показатели персонажа в таблице лидеров.

        Использует Postgres UPSERT для атомарной операции. Обновляются только те поля,
        для которых переданы значения (не None).

        Args:
            character_id: Идентификатор персонажа.
            gear_score: Опциональное новое значение Gear Score.
            xp: Опциональное новое значение общего опыта.
            rating: Опциональное новое значение PvP-рейтинга.
        """
        log.debug(
            f"LeaderboardRepoORM | action=update_score char_id={character_id} gs={gear_score} xp={xp} rating={rating}"
        )
        values = {}
        if gear_score is not None:
            values["gear_score"] = gear_score
        if xp is not None:
            values["total_xp"] = xp
        if rating is not None:
            values["pvp_rating"] = rating

        if not values:
            log.warning(f"LeaderboardRepoORM | action=update_score reason='No values to update' char_id={character_id}")
            return

        stmt = pg_insert(Leaderboard).values(character_id=character_id, **values)
        stmt = stmt.on_conflict_do_update(index_elements=[Leaderboard.character_id], set_=values)
        try:
            await self.session.execute(stmt)
            log.info(f"LeaderboardRepoORM | action=update_score status=success char_id={character_id}")
        except SQLAlchemyError as e:
            log.exception(f"LeaderboardRepoORM | action=update_score status=failed char_id={character_id} error={e}")
            raise

# apps/shared/database/repositories/ORM/monster_repository.py
from uuid import UUID

from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.database.db_contract.i_monster_repository import IMonsterRepository
from src.backend.database.postgres.models import GeneratedClanORM, GeneratedMonsterORM
from src.shared.schemas.monster_dto import GeneratedMonsterDTO


class MonsterRepository(IMonsterRepository):
    """
    Репозиторий для работы с монстрами и кланами.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        log.debug(f"MonsterRepository | status=initialized session={session}")

    async def get_clan_by_unique_hash(self, unique_hash: str) -> GeneratedClanORM | None:
        """
        Получает клан по уникальному хешу.
        """
        log.debug(f"MonsterRepository | action=get_clan_by_unique_hash hash={unique_hash}")
        query = select(GeneratedClanORM).where(GeneratedClanORM.unique_hash == unique_hash)
        try:
            result = await self.session.execute(query)
            return result.scalars().first()
        except SQLAlchemyError as e:
            log.exception(
                f"MonsterRepository | action=get_clan_by_unique_hash status=failed hash={unique_hash} error={e}"
            )
            raise

    async def create_clan_with_members(
        self, clan_orm: GeneratedClanORM, monsters_orm: list[GeneratedMonsterORM]
    ) -> GeneratedClanORM:
        """
        Создает клан вместе с монстрами.
        """
        log.debug(
            f"MonsterRepository | action=create_clan_with_members clan_id={clan_orm.id} members_count={len(monsters_orm)}"
        )
        try:
            clan_orm.members.extend(monsters_orm)
            # Добавляем clan и monsters отдельно для правильного типизирования
            self.session.add(clan_orm)
            self.session.add_all(monsters_orm)
            await self.session.flush([clan_orm])
            log.info(f"MonsterRepository | action=create_clan_with_members status=success clan_id={clan_orm.id}")
            return clan_orm
        except SQLAlchemyError as e:
            log.exception(
                f"MonsterRepository | action=create_clan_with_members status=failed clan_id={clan_orm.id} error={e}"
            )
            raise

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClanORM]:
        """
        Получает кланы по хешу контекста.
        """
        log.debug(f"MonsterRepository | action=get_clans_by_context_hash hash={context_hash}")
        # Оставляем старый метод для совместимости (с жадной загрузкой)
        query = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.context_hash == context_hash)
            .options(selectinload(GeneratedClanORM.members))
        )
        try:
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            log.exception(
                f"MonsterRepository | action=get_clans_by_context_hash status=failed hash={context_hash} error={e}"
            )
            raise

    # --- Новые методы для оптимизированного выбора ---

    async def get_clan_ids_by_context_hash(self, context_hash: str) -> list[UUID]:
        """Возвращает только ID кланов (быстро)."""
        log.debug(f"MonsterRepository | action=get_clan_ids_by_context_hash hash={context_hash}")
        query = select(GeneratedClanORM.id).where(GeneratedClanORM.context_hash == context_hash)
        try:
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            log.exception(
                f"MonsterRepository | action=get_clan_ids_by_context_hash status=failed hash={context_hash} error={e}"
            )
            raise

    async def get_clan_members(self, clan_id: UUID) -> list[GeneratedMonsterORM]:
        """Возвращает всех монстров конкретного клана."""
        log.debug(f"MonsterRepository | action=get_clan_members clan_id={clan_id}")
        query = select(GeneratedMonsterORM).where(GeneratedMonsterORM.clan_id == clan_id)
        try:
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            log.exception(f"MonsterRepository | action=get_clan_members status=failed clan_id={clan_id} error={e}")
            raise

    # ------------------------------------------------

    async def get_monster_by_id(self, monster_id: UUID | str) -> GeneratedMonsterORM | None:
        """Получает монстра по ID."""
        log.debug(f"MonsterRepository | action=get_monster_by_id monster_id={monster_id}")
        try:
            real_uuid = UUID(str(monster_id)) if not isinstance(monster_id, UUID) else monster_id
        except ValueError:
            log.warning(
                f"MonsterRepository | action=get_monster_by_id status=failed reason=invalid_uuid monster_id='{monster_id}'"
            )
            return None

        query = (
            select(GeneratedMonsterORM)
            .where(GeneratedMonsterORM.id == real_uuid)
            .options(selectinload(GeneratedMonsterORM.clan))
        )
        try:
            result = await self.session.execute(query)
            return result.scalars().first()
        except SQLAlchemyError as e:
            log.exception(
                f"MonsterRepository | action=get_monster_by_id status=failed monster_id={monster_id} error={e}"
            )
            raise

    async def get_monsters_batch(self, monster_ids: list[str]) -> list[GeneratedMonsterORM]:
        """Возвращает список монстров по списку ID."""
        log.debug(f"MonsterRepository | action=get_monsters_batch count={len(monster_ids)}")
        if not monster_ids:
            return []

        try:
            # Преобразуем строки в UUID
            uuids = [UUID(mid) for mid in monster_ids]
        except ValueError:
            log.warning(
                f"MonsterRepository | action=get_monsters_batch status=failed reason=invalid_uuid_in_list ids='{monster_ids}'"
            )
            return []

        query = (
            select(GeneratedMonsterORM).where(GeneratedMonsterORM.id.in_(uuids))
            # .options(selectinload(GeneratedMonsterORM.clan)) # Если нужен клан
        )
        try:
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            log.exception(f"MonsterRepository | action=get_monsters_batch status=failed error={e}")
            raise

    async def get_monster_for_combat(self, monster_id: UUID | str) -> GeneratedMonsterDTO | None:
        """Получает DTO монстра для боя."""
        monster_orm = await self.get_monster_by_id(monster_id)
        if not monster_orm:
            return None
        return GeneratedMonsterDTO.model_validate(monster_orm)

    async def get_all_clans(self) -> list[GeneratedClanORM]:
        """Получает все кланы."""
        log.debug("MonsterRepository | action=get_all_clans")
        query = select(GeneratedClanORM).options(selectinload(GeneratedClanORM.members))
        try:
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            log.exception(f"MonsterRepository | action=get_all_clans status=failed error={e}")
            raise

    async def get_clans_by_zone(self, zone_id: str) -> list[GeneratedClanORM]:
        """Получает кланы в зоне."""
        log.debug(f"MonsterRepository | action=get_clans_by_zone zone_id={zone_id}")
        query = select(GeneratedClanORM).where(GeneratedClanORM.zone_id == zone_id)
        try:
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            log.exception(f"MonsterRepository | action=get_clans_by_zone status=failed zone_id={zone_id} error={e}")
            raise

    async def get_monsters_by_role_and_threat(
        self, role: str, min_threat: int, max_threat: int, limit: int = 5
    ) -> list[GeneratedMonsterORM]:
        """Ищет монстров по роли и угрозе."""
        log.debug(
            f"MonsterRepository | action=get_monsters_by_role_and_threat role={role} threat={min_threat}-{max_threat}"
        )
        query = (
            select(GeneratedMonsterORM)
            .where(
                GeneratedMonsterORM.role == role,
                GeneratedMonsterORM.threat_rating >= min_threat,
                GeneratedMonsterORM.threat_rating <= max_threat,
            )
            .limit(limit)
        )
        try:
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            log.exception(f"MonsterRepository | action=get_monsters_by_role_and_threat status=failed error={e}")
            raise

# apps/shared/database/repositories/ORM/characters_repo_orm.py
from loguru import logger as log
from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.db_contract.i_characters_repo import (
    ICharacterAttributesRepo,
    ICharactersRepo,
)
from src.backend.database.postgres.models import Character, CharacterAttributes
from src.backend.database.postgres.models.inventory import ResourceWallet
from src.backend.database.postgres.models.symbiote import CharacterSymbiote
from src.shared.schemas.character import (
    CharacterAttributesReadDTO,
    CharacterAttributesUpdateDTO,
    CharacterOnboardingUpdateDTO,
    CharacterReadDTO,
    CharacterShellCreateDTO,
)


class CharactersRepoORM(ICharactersRepo):
    """
    ORM-реализация репозитория для управления персонажами.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        log.debug(f"CharactersRepoORM | status=initialized session={session}")

    async def create_character_shell(self, character_data: CharacterShellCreateDTO) -> CharacterReadDTO:
        """
        Создает "оболочку" персонажа (базовая запись).

        Args:
            character_data: DTO с данными для создания.

        Returns:
            CharacterReadDTO: Созданный персонаж.
        """
        log.debug(f"CharactersRepoORM | action=create_character_shell user_id={character_data.user_id}")
        try:
            orm_character = Character(**character_data.model_dump())
            orm_character.attributes = CharacterAttributes()
            orm_character.symbiote = CharacterSymbiote()
            orm_character.wallet = ResourceWallet()
            self.session.add(orm_character)
            await self.session.flush()
            log.info(
                f"CharactersRepoORM | action=create_character_shell status=success char_id={orm_character.character_id}"
            )
            return CharacterReadDTO.model_validate(orm_character)
        except SQLAlchemyError as e:
            log.exception(
                f"CharactersRepoORM | action=create_character_shell status=failed user_id={character_data.user_id} error={e}"
            )
            raise

    async def update_character_onboarding(
        self, character_id: int, character_data: CharacterOnboardingUpdateDTO
    ) -> None:
        """
        Обновляет данные персонажа после онбординга.

        Args:
            character_id: ID персонажа.
            character_data: Новые данные.
        """
        log.debug(f"CharactersRepoORM | action=update_character_onboarding char_id={character_id}")
        stmt = update(Character).where(Character.character_id == character_id).values(**character_data.model_dump())
        try:
            await self.session.execute(stmt)
            log.info(f"CharactersRepoORM | action=update_character_onboarding status=success char_id={character_id}")
        except SQLAlchemyError as e:
            log.exception(
                f"CharactersRepoORM | action=update_character_onboarding status=failed char_id={character_id} error={e}"
            )
            raise

    async def get_character(self, character_id: int) -> CharacterReadDTO | None:
        """
        Получает персонажа по ID.

        Args:
            character_id: ID персонажа.

        Returns:
            CharacterReadDTO | None: Персонаж или None.
        """
        log.debug(f"CharactersRepoORM | action=get_character char_id={character_id}")
        stmt = select(Character).where(Character.character_id == character_id)
        try:
            result = await self.session.execute(stmt)
            orm_character = result.scalar_one_or_none()
            if orm_character:
                log.debug(f"CharactersRepoORM | action=get_character status=found char_id={character_id}")
                return CharacterReadDTO.model_validate(orm_character)
            log.debug(f"CharactersRepoORM | action=get_character status=not_found char_id={character_id}")
            return None
        except SQLAlchemyError as e:
            log.exception(f"CharactersRepoORM | action=get_character status=failed char_id={character_id} error={e}")
            raise

    async def get_characters(self, user_id: int) -> list[CharacterReadDTO]:
        """
        Получает всех персонажей пользователя.

        Args:
            user_id: ID пользователя.

        Returns:
            list[CharacterReadDTO]: Список персонажей.
        """
        log.debug(f"CharactersRepoORM | action=get_characters user_id={user_id}")
        stmt = select(Character).where(Character.user_id == user_id)
        try:
            result = await self.session.scalars(stmt)
            orm_characters_list = result.all()
            log.debug(f"CharactersRepoORM | action=get_characters status=success count={len(orm_characters_list)}")
            return [CharacterReadDTO.model_validate(orm_char) for orm_char in orm_characters_list]
        except SQLAlchemyError as e:
            log.exception(f"CharactersRepoORM | action=get_characters status=failed user_id={user_id} error={e}")
            raise

    async def get_characters_batch(self, character_ids: list[int]) -> list[CharacterReadDTO]:
        """
        Получает список персонажей по списку ID.

        Args:
            character_ids: Список ID персонажей.

        Returns:
            list[CharacterReadDTO]: Список персонажей.
        """
        log.debug(f"CharactersRepoORM | action=get_characters_batch count={len(character_ids)}")
        if not character_ids:
            return []
        stmt = select(Character).where(Character.character_id.in_(character_ids))
        try:
            result = await self.session.scalars(stmt)
            orm_characters_list = result.all()
            log.debug(
                f"CharactersRepoORM | action=get_characters_batch status=success count={len(orm_characters_list)}"
            )
            return [CharacterReadDTO.model_validate(orm_char) for orm_char in orm_characters_list]
        except SQLAlchemyError as e:
            log.exception(f"CharactersRepoORM | action=get_characters_batch status=failed error={e}")
            raise

    async def delete_characters(self, character_id: int) -> None:
        """
        Удаляет персонажа.

        Args:
            character_id: ID персонажа.
        """
        log.debug(f"CharactersRepoORM | action=delete_characters char_id={character_id}")
        stmt = delete(Character).where(Character.character_id == character_id)
        try:
            await self.session.execute(stmt)
            log.info(f"CharactersRepoORM | action=delete_characters status=success char_id={character_id}")
        except SQLAlchemyError as e:
            log.exception(
                f"CharactersRepoORM | action=delete_characters status=failed char_id={character_id} error={e}"
            )
            raise

    async def update_character_game_stage(self, character_id: int, game_stage: str) -> None:
        """
        Обновляет стадию игры персонажа.

        Args:
            character_id: ID персонажа.
            game_stage: Новая стадия.
        """
        log.debug(
            f"CharactersRepoORM | action=update_character_game_stage char_id={character_id} new_stage='{game_stage}'"
        )
        stmt = update(Character).where(Character.character_id == character_id).values(game_stage=game_stage)
        try:
            await self.session.execute(stmt)
            log.info(f"CharactersRepoORM | action=update_character_game_stage status=success char_id={character_id}")
        except SQLAlchemyError as e:
            log.exception(
                f"CharactersRepoORM | action=update_character_game_stage status=failed char_id={character_id} error={e}"
            )
            raise

    async def update_dynamic_state(self, character_id: int, state_data: dict) -> None:
        """
        Обновляет динамические параметры персонажа (HP, Energy, Location, Exp).
        Используется для бэкапа состояния из Redis в БД.

        Args:
            character_id: ID персонажа.
            state_data: Словарь с данными.
        """
        log.debug(f"CharactersRepoORM | action=update_dynamic_state char_id={character_id}")

        # Фильтруем только разрешенные поля, чтобы не затереть лишнее
        allowed_fields = {"hp_current", "energy_current", "location", "experience"}
        values_to_update = {k: v for k, v in state_data.items() if k in allowed_fields}

        if not values_to_update:
            return

        stmt = update(Character).where(Character.character_id == character_id).values(**values_to_update)
        try:
            await self.session.execute(stmt)
            log.info(f"CharactersRepoORM | action=update_dynamic_state status=success char_id={character_id}")
        except SQLAlchemyError as e:
            log.exception(
                f"CharactersRepoORM | action=update_dynamic_state status=failed char_id={character_id} error={e}"
            )
            raise


class CharacterAttributesRepoORM(ICharacterAttributesRepo):
    """
    Реализация репозитория атрибутов.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        log.debug(f"CharacterAttributesRepoORM | status=initialized session={session}")

    async def get_attributes(self, character_id: int) -> CharacterAttributesReadDTO | None:
        """
        Получает атрибуты персонажа.

        Args:
            character_id: ID персонажа.

        Returns:
            CharacterAttributesReadDTO | None: Атрибуты или None.
        """
        log.debug(f"CharacterAttributesRepoORM | action=get_attributes char_id={character_id}")
        stmt = select(CharacterAttributes).where(CharacterAttributes.character_id == character_id)
        try:
            result = await self.session.execute(stmt)
            orm_attributes = result.scalar_one_or_none()
            if orm_attributes:
                log.debug(f"CharacterAttributesRepoORM | action=get_attributes status=found char_id={character_id}")
                return CharacterAttributesReadDTO.model_validate(orm_attributes)
            log.debug(f"CharacterAttributesRepoORM | action=get_attributes status=not_found char_id={character_id}")
            return None
        except SQLAlchemyError as e:
            log.exception(
                f"CharacterAttributesRepoORM | action=get_attributes status=failed char_id={character_id} error={e}"
            )
            raise

    async def get_attributes_batch(self, character_ids: list[int]) -> list[CharacterAttributesReadDTO]:
        """
        Получает атрибуты для списка персонажей.

        Args:
            character_ids: Список ID персонажей.

        Returns:
            list[CharacterAttributesReadDTO]: Список атрибутов.
        """
        log.debug(f"CharacterAttributesRepoORM | action=get_attributes_batch count={len(character_ids)}")
        if not character_ids:
            return []
        stmt = select(CharacterAttributes).where(CharacterAttributes.character_id.in_(character_ids))
        try:
            result = await self.session.execute(stmt)
            orm_attributes_list = result.scalars().all()
            log.debug(
                f"CharacterAttributesRepoORM | action=get_attributes_batch status=success count={len(orm_attributes_list)}"
            )
            return [CharacterAttributesReadDTO.model_validate(orm_attr) for orm_attr in orm_attributes_list]
        except SQLAlchemyError as e:
            log.exception(f"CharacterAttributesRepoORM | action=get_attributes_batch status=failed error={e}")
            raise

    async def update_attributes(self, character_id: int, attributes_data: CharacterAttributesUpdateDTO) -> None:
        """
        Обновляет атрибуты персонажа.

        Args:
            character_id: ID персонажа.
            attributes_data: Новые значения атрибутов.
        """
        log.debug(f"CharacterAttributesRepoORM | action=update_attributes char_id={character_id}")
        stmt = (
            update(CharacterAttributes)
            .where(CharacterAttributes.character_id == character_id)
            .values(**attributes_data.model_dump())
        )
        try:
            await self.session.execute(stmt)
            log.info(f"CharacterAttributesRepoORM | action=update_attributes status=success char_id={character_id}")
        except SQLAlchemyError as e:
            log.exception(
                f"CharacterAttributesRepoORM | action=update_attributes status=failed char_id={character_id} error={e}"
            )
            raise

    async def add_attributes(
        self, character_id: int, attributes_to_add: dict[str, int]
    ) -> CharacterAttributesReadDTO | None:
        """
        Добавляет значения к атрибутам персонажа.

        Args:
            character_id: ID персонажа.
            attributes_to_add: Словарь {атрибут: значение}.

        Returns:
            CharacterAttributesReadDTO | None: Обновленные атрибуты.
        """
        if not attributes_to_add:
            log.debug(
                f"CharacterAttributesRepoORM | action=add_attributes reason='Empty attributes_to_add', returning current attributes for char_id={character_id}"
            )
            return await self.get_attributes(character_id)

        log.debug(
            f"CharacterAttributesRepoORM | action=add_attributes char_id={character_id} attributes={attributes_to_add}"
        )
        allowed_attributes = {
            "strength",
            "agility",
            "endurance",
            "intelligence",
            "wisdom",
            "men",
            "perception",
            "charisma",
            "luck",
        }
        values_to_update = {}
        for attr, value in attributes_to_add.items():
            if attr in allowed_attributes:
                orm_column = getattr(CharacterAttributes, attr)
                values_to_update[attr] = orm_column + value

        if not values_to_update:
            return await self.get_attributes(character_id)

        stmt = (
            update(CharacterAttributes)
            .where(CharacterAttributes.character_id == character_id)
            .values(**values_to_update)
        )
        try:
            await self.session.execute(stmt)
            await self.session.flush()
            log.info(f"CharacterAttributesRepoORM | action=add_attributes status=success char_id={character_id}")
            updated_attributes_dto = await self.get_attributes(character_id=character_id)
            if updated_attributes_dto:
                return updated_attributes_dto
            return None
        except SQLAlchemyError as e:
            log.exception(
                f"CharacterAttributesRepoORM | action=add_attributes status=failed char_id={character_id} error={e}"
            )
            raise

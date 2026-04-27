from abc import ABC, abstractmethod

from src.shared.schemas.character import (
    CharacterAttributesReadDTO,
    CharacterAttributesUpdateDTO,
    CharacterOnboardingUpdateDTO,
    CharacterReadDTO,
    CharacterShellCreateDTO,
)


class ICharactersRepo(ABC):
    """
    Абстрактный базовый класс (интерфейс) для репозитория персонажей.

    Определяет контракт для управления основными данными персонажей,
    включая создание, обновление, получение и удаление.
    """

    @abstractmethod
    async def create_character_shell(self, character_data: CharacterShellCreateDTO) -> CharacterReadDTO:
        """
        Создает "оболочку" персонажа, содержащую только ID пользователя.

        Этот метод используется на первом шаге создания персонажа, когда
        основные данные (имя, пол) еще не известны.

        Args:
            character_data: DTO с `user_id` для создания оболочки.

        Returns:
            CharacterReadDTO с созданным персонажем (включая character_id, attributes, wallet, symbiote).
        """
        pass

    @abstractmethod
    async def update_character_onboarding(
        self, character_id: int, character_data: CharacterOnboardingUpdateDTO
    ) -> None:
        """
        Обновляет данные персонажа после этапа онбординга.

        Заполняет имя, пол и устанавливает начальную игровую стадию
        для ранее созданной "оболочки".

        Args:
            character_id: Идентификатор персонажа для обновления.
            character_data: DTO с данными (name, gender, game_stage).
        """
        pass

    @abstractmethod
    async def get_character(self, character_id: int) -> CharacterReadDTO | None:
        """
        Находит и возвращает одного персонажа по его `character_id`.

        Args:
            character_id: Уникальный идентификатор персонажа.

        Returns:
            DTO `CharacterReadDTO` с данными персонажа, если он найден,
            иначе - None.
        """
        pass

    @abstractmethod
    async def get_characters(self, user_id: int) -> list[CharacterReadDTO]:
        """
        Возвращает список всех персонажей, принадлежащих одному пользователю.

        Args:
            user_id: Идентификатор пользователя, чьих персонажей нужно найти.

        Returns:
            Список DTO `CharacterReadDTO` персонажей.
            Если персонажей нет, возвращает пустой список.
        """
        pass

    @abstractmethod
    async def get_characters_batch(self, character_ids: list[int]) -> list[CharacterReadDTO]:
        """
        Возвращает список персонажей по списку их ID.

        Args:
            character_ids: Список идентификаторов персонажей.

        Returns:
            Список DTO `CharacterReadDTO` персонажей.
        """
        pass

    @abstractmethod
    async def delete_characters(self, character_id: int) -> None:
        """
        Удаляет персонажа и все связанные с ним данные.

        Args:
            character_id: Идентификатор персонажа для удаления.
        """
        pass

    @abstractmethod
    async def update_character_game_stage(self, character_id: int, character_game_stage: str) -> None:
        """
        Обновляет поле `game_stage` у конкретного персонажа.

        Args:
            character_id: Идентификатор персонажа для обновления.
            character_game_stage: Новое значение игровой стадии.
        """
        pass


class ICharacterAttributesRepo(ABC):
    """
    Абстрактный базовый класс (интерфейс) для репозитория атрибутов персонажа.
    (Ранее ICharacterStatsRepo)

    Определяет контракт для получения, обновления и модификации
    атрибутов персонажа.
    """

    @abstractmethod
    async def get_attributes(self, character_id: int) -> CharacterAttributesReadDTO | None:
        """
        Возвращает атрибуты персонажа.

        Args:
            character_id: Идентификатор персонажа, чьи атрибуты нужны.

        Returns:
            DTO `CharacterAttributesReadDTO` с атрибутами, если они найдены,
            иначе - None.
        """
        pass

    @abstractmethod
    async def get_attributes_batch(self, character_ids: list[int]) -> list[CharacterAttributesReadDTO]:
        """
        Возвращает атрибуты для списка персонажей.

        Args:
            character_ids: Список идентификаторов персонажей.

        Returns:
            Список DTO `CharacterAttributesReadDTO`.
        """
        pass

    @abstractmethod
    async def update_attributes(self, character_id: int, attributes_data: CharacterAttributesUpdateDTO) -> None:
        """
        Полностью перезаписывает все атрибуты персонажа.

        Args:
            character_id: Идентификатор персонажа для обновления.
            attributes_data: DTO с полным набором новых атрибутов.
        """
        pass

    @abstractmethod
    async def add_attributes(
        self, character_id: int, attributes_to_add: dict[str, int]
    ) -> CharacterAttributesReadDTO | None:
        """
        Атомарно добавляет значения к существующим атрибутам.

        Реализация должна инкрементально обновлять только переданные
        атрибуты и возвращать их новое полное состояние.

        Args:
            character_id: Идентификатор персонажа.
            attributes_to_add: Словарь, где ключ - название атрибута,
                          а значение - число для добавления (может быть отрицательным).

        Returns:
            DTO `CharacterAttributesReadDTO` с обновленными атрибутами
            персонажа или None, если персонаж не найден.
        """
        pass


# Alias for backward compatibility
ICharacterStatsRepo = ICharacterAttributesRepo

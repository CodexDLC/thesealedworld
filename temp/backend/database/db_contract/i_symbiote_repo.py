from abc import ABC, abstractmethod

from src.backend.database.postgres.models.symbiote import CharacterSymbiote


class ISymbioteRepo(ABC):
    """
    Интерфейс репозитория для управления сущностью Симбиота (`CharacterSymbiote`).

    Определяет контракт для получения, обновления имени, установки Дара
    и обновления прогресса Симбиота.
    """

    @abstractmethod
    async def get_symbiote(self, character_id: int) -> CharacterSymbiote | None:
        """
        Получает запись Симбиота по идентификатору персонажа.

        Args:
            character_id: Идентификатор персонажа.

        Returns:
            Объект `CharacterSymbiote`, если найден, иначе None.
        """
        pass

    @abstractmethod
    async def get_symbiotes_batch(self, character_ids: list[int]) -> list[CharacterSymbiote]:
        """
        Получает список Симбиотов для списка персонажей.

        Args:
            character_ids: Список идентификаторов персонажей.

        Returns:
            Список объектов `CharacterSymbiote`.
        """
        pass

    @abstractmethod
    async def update_name(self, character_id: int, new_name: str) -> None:
        """
        Обновляет имя Симбиота для указанного персонажа.

        Args:
            character_id: Идентификатор персонажа.
            new_name: Новое имя для Симбиота.
        """
        pass

    @abstractmethod
    async def set_gift(self, character_id: int, gift_id: str) -> None:
        """
        Устанавливает выбранный Дар (Gift) для Симбиота персонажа.

        Args:
            character_id: Идентификатор персонажа.
            gift_id: Идентификатор Дара.
        """
        pass

    @abstractmethod
    async def update_progress(self, character_id: int, new_xp: int, new_rank: int) -> None:
        """
        Обновляет опыт и ранг Симбиота.

        Используется после того, как сервис рассчитал новый опыт и проверил
        повышение ранга.

        Args:
            character_id: Идентификатор персонажа.
            new_xp: Новое значение опыта Симбиота.
            new_rank: Новый ранг Симбиота.
        """
        pass

    @abstractmethod
    async def update_elements_resonance(self, character_id: int, new_resonance: dict) -> None:
        """
        Обновляет поле резонанса элементов (JSON).

        Полностью перезаписывает поле `elements_resonance` переданным словарем.

        Args:
            character_id: Идентификатор персонажа.
            new_resonance: Словарь с новыми значениями резонанса.
        """
        pass

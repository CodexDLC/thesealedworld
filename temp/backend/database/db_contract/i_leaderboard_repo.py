from abc import ABC, abstractmethod


class ILeaderboardRepo(ABC):
    """
    Интерфейс репозитория для управления записями в таблице лидеров (`Leaderboard`).

    Определяет контракт для создания и обновления агрегированных показателей
    персонажей, таких как Gear Score, опыт и PvP-рейтинг.
    """

    @abstractmethod
    async def update_score(
        self, character_id: int, gear_score: int | None = None, xp: int | None = None, rating: int | None = None
    ) -> None:
        """
        Создает новую запись или обновляет существующие показатели персонажа в таблице лидеров.

        Args:
            character_id: Идентификатор персонажа.
            gear_score: Опциональное новое значение Gear Score.
            xp: Опциональное новое значение общего опыта.
            rating: Опциональное новое значение PvP-рейтинга.
        """
        pass

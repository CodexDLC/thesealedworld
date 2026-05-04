from abc import ABC, abstractmethod

from src.shared.enums.skill_enums import SkillProgressState
from src.shared.schemas.skill import SkillProgressDTO


class ISkillProgressRepo(ABC):
    """
    Интерфейс репозитория для прогресса навыков персонажа.
    """

    @abstractmethod
    async def initialize_all_base_skills(self, character_id: int) -> None:
        """
        Инициализирует записи для всех базовых навыков для нового персонажа.
        """
        pass

    @abstractmethod
    async def add_skill_xp(self, character_id: int, skill_key: str, xp_to_add: float) -> SkillProgressDTO | None:
        """
        Атомарно добавляет опыт к указанному навыку персонажа.
        xp_to_add: Float (может быть дробным).
        """
        pass

    @abstractmethod
    async def update_skill_state(self, character_id: int, skill_key: str, state: SkillProgressState) -> None:
        """
        Обновляет состояние развития навыка (PLUS, PAUSE, MINUS).
        """
        pass

    @abstractmethod
    async def update_skill_unlocked_state(self, character_id: int, skill_key_list: list[str], state: bool) -> None:
        """
        Массово обновляет статус `is_unlocked`.
        """
        pass

    @abstractmethod
    async def get_all_skills_progress(self, character_id: int) -> list[SkillProgressDTO]:
        """
        Возвращает прогресс всех навыков для одного персонажа.
        """
        pass

    @abstractmethod
    async def get_all_skills_progress_batch(self, character_ids: list[int]) -> dict[int, list[SkillProgressDTO]]:
        """
        Пакетное получение прогресса навыков для списка персонажей.
        """
        pass

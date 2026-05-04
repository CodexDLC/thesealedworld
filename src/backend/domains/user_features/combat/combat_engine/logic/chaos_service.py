import json
from typing import Any

from loguru import logger as log

from src.backend.database.redis.manager.combat_manager import CombatManager
from src.backend.domains.user_features.combat.dto.combat_actor_dto import ActorMetaDTO, ActorRawDTO


class ChaosService:
    """
    Сервис Хаоса. Отвечает за спавн "Мусорщика" (Time Eater).
    """

    CLEANER_ID = -666
    CLEANER_NAME = "Мусорщик"
    CLEANER_TEAM = "chaos"

    def __init__(self, combat_manager: CombatManager):
        self.combat_manager = combat_manager

    async def spawn_cleaner(self, session_id: str) -> bool:
        """
        Призывает Мусорщика в бой.
        Возвращает True, если успешно призван.
        """
        # 1. Проверяем, есть ли он уже
        meta_raw = await self.combat_manager.get_rbc_session_meta(session_id)
        if not meta_raw:
            return False

        # Проверка через actors_info (быстрее, чем парсить teams)
        actors_info = json.loads(meta_raw.get("actors_info") or "{}")
        if str(self.CLEANER_ID) in actors_info:
            return False  # Уже здесь

        log.warning(f"Chaos Protocol | Spawning Cleaner in session {session_id}")

        # 2. Создаем данные Мусорщика (DTO)
        cleaner_data = self._create_cleaner_data()

        # 3. Вызываем универсальный метод менеджера
        await self.combat_manager.universal_hot_join(
            session_id=session_id,
            char_id=self.CLEANER_ID,
            team_name=self.CLEANER_TEAM,
            actor_data=cleaner_data,
            is_ai=True,
        )

        # 4. Лог
        await self.combat_manager.add_log(
            session_id,
            "⏳ Границы реальности истончились. В поисках утраченного времени пришел ОН.",
            tags=["chaos", "spawn"],
        )

        return True

    def _create_cleaner_data(self) -> dict[str, Any]:
        """Генерирует данные босса через DTO."""
        # Stats
        stats = {
            "strength": 1000,
            "agility": 1000,
            "endurance": 1000,
            "intelligence": 1000,
            "wisdom": 1000,
            "luck": 1000,
        }

        # State DTO (используем ActorMetaDTO вместо ActorState)
        state = ActorMetaDTO(
            id=self.CLEANER_ID,
            name=self.CLEANER_NAME,
            type="ai",
            team=self.CLEANER_TEAM,
            hp=100000,
            max_hp=100000,
            en=1000,
            max_en=1000,
            tactics=100,
            afk_level=0,
            is_dead=False,
            tokens={},
        )

        # Raw DTO
        raw = ActorRawDTO(
            attributes=stats,
            modifiers={},
        )

        # Meta (dict) - дублируем для совместимости, если нужно, или используем state
        meta_dict = {"name": self.CLEANER_NAME, "type": "ai"}

        # Loadout (dict)
        loadout_dict: dict[str, Any] = {"equipment_layout": {}, "known_abilities": []}

        return {"state": state.model_dump(), "raw": raw.model_dump(), "loadout": loadout_dict, "meta": meta_dict}

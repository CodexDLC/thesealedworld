import random
import uuid
from typing import TYPE_CHECKING, Any

from loguru import logger as log

from src.shared.enums.domain_enums import CoreDomain

from .base_handler import BaseScenarioHandler

if TYPE_CHECKING:
    from src.backend.domains.internal_systems.dispatcher.system_dispatcher import SystemDispatcher

# Список точек выхода из туториала (окрестности Хаба 52_52, радиус ~6 клеток)
TUTORIAL_EXIT_LOCATIONS = [
    "52_58",
    "52_46",
    "58_52",
    "46_52",  # Кардинальные направления
    "56_56",
    "48_56",
    "56_48",
    "48_48",  # Диагонали
    "55_57",
    "57_55",
    "49_57",
    "47_55",  # Случайные смещения
]


class TutorialScenarioHandler(BaseScenarioHandler):
    """
    Обработчик для квеста 'awakening_rift' (Туториал).
    Отвечает за подготовку контекста и выдачу финальных наград.
    """

    async def on_initialize(
        self, char_id: int, quest_master: dict[str, Any], prev_state: str | None = None, prev_loc: str | None = None
    ) -> dict[str, Any]:
        """Инициализация 'песочницы' туториала."""
        # Получаем session_id из quest_master (передан из оркестратора)
        session_id = quest_master.get("session_id")
        if not session_id:
            # Fallback если не передали (для совместимости)
            session_id = str(uuid.uuid4())

        # Получаем данные симбиота для системных сообщений
        symbiote_data = await self.manager.am.get_account_field(char_id, "symbiote")
        sys_name = "System"
        if isinstance(symbiote_data, dict):
            sys_name = symbiote_data.get("name", "System")
        elif isinstance(symbiote_data, str) and symbiote_data:
            sys_name = symbiote_data

        # Формируем стартовый контекст со всеми необходимыми ключами
        context = {
            "scenario_session_id": session_id,
            "quest_key": quest_master["quest_key"],
            "current_node_key": quest_master["start_node_id"],
            "step_counter": 0,
            "sys_actor": sys_name,
            "prev_state": prev_state,
            "prev_loc": prev_loc,
            "p_loc": prev_loc,  # <-- Добавлено для совместимости с текстом сценария
            # Веса статов (w_stats)
            "w_strength": 0,
            "w_agility": 0,
            "w_endurance": 0,
            "w_intelligence": 0,
            "w_wisdom": 0,
            "w_men": 0,
            "w_perception": 0,
            "w_charisma": 0,
            "w_luck": 0,
            # Веса стихий (t_elements)
            "t_fire": 0,
            "t_water": 0,
            "t_earth": 0,
            "t_air": 0,
            "t_dark": 0,
            "t_arcane": 0,
            "t_light": 0,
            "t_nature": 0,
            # Очереди наград
            "loot_queue": [],
            "skills_queue": [],
            # Флаги логики
            "is_two_handed": 0,
        }

        log.info(f"TutorialHandler | Start char={char_id} session={session_id}")
        return context

    async def on_finalize(
        self, char_id: int, context: dict[str, Any], router: "SystemDispatcher"
    ) -> tuple[CoreDomain, Any]:
        """Финальная выдача наград и запуск боя."""
        log.info(f"TutorialHandler | Finalizing char={char_id}")

        # 1. Расчет статов (+9...+1)
        final_stats, tokens = self._calculate_stats(context)
        await self.manager.update_rewards(char_id, final_stats, tokens)

        # 2. Выдача предметов и скиллов (через сервис)
        rewards = {"items": context.get("loot_queue", []), "skills": context.get("skills_queue", [])}
        await self.manager.grant_rewards(char_id, rewards)

        # 3. ПОДМЕНА СОСТОЯНИЯ (FIX)
        target_exit_loc = random.choice(TUTORIAL_EXIT_LOCATIONS)

        # 4. ПОДГОТОВКА БОЯ (Выбор монстра через сервис)
        monster_id = await self.manager.find_tutorial_monster_id(target_exit_loc)

        if not monster_id:
            log.error("TutorialHandler | Failed to find monster for tutorial battle")
            # Fallback: если монстра нет, возвращаем в EXPLORATION (или кидаем ошибку)
            # В данном случае, чтобы не крашить, вернем EXPLORATION
            await self.manager.am.update_account_fields(
                char_id,
                {
                    "state": CoreDomain.EXPLORATION,
                    "prev_state": CoreDomain.EXPLORATION,
                    "location_id": target_exit_loc,
                    "prev_location_id": target_exit_loc,
                },
            )
            # Возвращаем пустой payload или сообщение об ошибке
            return CoreDomain.EXPLORATION, {"message": "Tutorial completed, but no monster found."}

        # Обновляем локацию и подменяем историю (prev_state), но НЕ меняем текущий state (это сделает CombatEntry)
        await self.manager.am.update_account_fields(
            char_id,
            {
                # "state": CoreDomain.COMBAT, # Убрали, так как это ответственность CombatEntry
                "prev_state": CoreDomain.EXPLORATION,  # Подменяем историю
                "location_id": target_exit_loc,
                "prev_location_id": target_exit_loc,
            },
        )

        log.success(
            f"TutorialHandler | Finalization successful for char={char_id}. Exit loc: {target_exit_loc}. Monster ID: {monster_id}"
        )

        # 5. ПЕРЕХОД В БОЙ (Через хелпер базового класса)
        return await self._start_pve_combat(router, char_id, monster_id, target_exit_loc)

    def _calculate_stats(self, context: dict[str, Any]) -> tuple[dict, dict]:
        """Чистая функция расчета статов."""
        stat_names = [
            "strength",
            "agility",
            "endurance",
            "intelligence",
            "wisdom",
            "men",
            "perception",
            "charisma",
            "luck",
        ]
        weighted_stats = []
        for name in stat_names:
            weight = context.get(f"w_{name}", 0)
            weighted_stats.append((name, weight))
        weighted_stats.sort(key=lambda x: x[1], reverse=True)
        bonuses = [9, 8, 7, 6, 5, 4, 3, 2, 1]
        final_stats = {}
        for i, (stat_name, _) in enumerate(weighted_stats):
            if i < len(bonuses):
                final_stats[stat_name] = bonuses[i]
        element_names = ["fire", "water", "earth", "air", "dark", "arcane", "light", "nature"]
        tokens = {f"t_{name}": context.get(f"t_{name}", 0) for name in element_names}

        return final_stats, tokens

from pydantic import ValidationError

from src.backend.domains.user_features.combat.dto.combat_actor_dto import ActorSnapshot, ActorStats
from src.backend.services.calculators.stats_waterfall_calculator import StatsWaterfallCalculator
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


class StatsEngine:
    """
    Движок расчета характеристик (Stats Engine).
    Отвечает за актуализацию ActorStats на основе ActorSnapshot.raw.
    Использует StatsWaterfallCalculator для математики.
    """

    @staticmethod
    def ensure_stats(actor: ActorSnapshot) -> None:
        """
        Гарантирует, что у актера есть актуальные ActorStats.
        Если stats нет или они 'грязные' -> пересчитывает.
        """
        if actor.stats is None:
            # Полный пересчет (первый запуск)
            StatsEngine._recalculate_full(actor)
        elif actor.dirty_stats:
            # Частичный пересчет (оптимизация)
            # Пока делаем полный, так как Waterfall быстрый
            StatsEngine._recalculate_full(actor)

        # Если stats есть и dirty_stats пуст -> ничего не делаем (используем кэш)

    @staticmethod
    def _recalculate_full(actor: ActorSnapshot) -> None:
        """
        Полный цикл пересчета.
        """
        # 1. Подготовка данных для калькулятора
        raw_data = actor.raw.model_dump()

        # 2. Расчет (Waterfall)
        # Возвращает плоский словарь модификаторов и словарь формул
        calculated_mods, explanation = StatsWaterfallCalculator.calculate_waterfall(raw_data)

        # 3. Сборка ActorStats
        # Берем скиллы из Snapshot (они не считаются в Waterfall, а просто копируются)
        skills_data = actor.skills

        # Создаем DTO
        # Теперь ключи в calculated_mods (из StatsWaterfallCalculator -> stats_formulas -> StatKey)
        # должны совпадать с полями CombatModifiersDTO (которые мы синхронизировали).
        # extra='ignore' в DTO защитит от лишних полей.

        try:
            # Pydantic handles float->int conversion for HP/EN
            mods_dto = CombatModifiersDTO(**calculated_mods)  # type: ignore
        except (ValidationError, TypeError) as e:
            # Логируем ошибку, но пытаемся продолжить с частичными данными
            # В реальном проде тут нужен алерт
            print(f"StatsEngine Error: {e}")
            valid_keys = CombatModifiersDTO.model_fields.keys()
            filtered_mods = {k: v for k, v in calculated_mods.items() if k in valid_keys}
            mods_dto = CombatModifiersDTO(**filtered_mods)  # type: ignore

        skills_dto = CombatSkillsDTO(**skills_data)

        actor.stats = ActorStats(mods=mods_dto, skills=skills_dto)

        # 4. Сохраняем объяснения (для дебага/логов)
        actor.explanation = explanation

        # 5. Сбрасываем флаги
        actor.dirty_stats.clear()

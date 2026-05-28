from loguru import logger as log
from pydantic import ValidationError

from src.backend.core.calculators.stats_waterfall_calculator import StatsWaterfallCalculator
from src.backend.features.character.runtime.rules.base_power_assembler import BasePowerAssembler
from src.backend.features.combat.dto.actor import ActorSnapshot, ActorStats
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO

TRACE_MOD_KEYS = (
    "main_hand_accuracy",
    "accuracy",
    "physical_damage",
    "physical_strength_power",
    "physical_agility_power",
    "physical_endurance_power",
    "main_hand_damage_base",
    "main_hand_damage_spread",
    "main_hand_weapon_power",
    "main_hand_stat_damage_raw",
    "main_hand_stat_damage_effective",
    "main_hand_mastery_factor",
    "main_hand_damage_spread_raw",
    "main_hand_crit_chance",
    "crit_chance",
    "physical_suppression",
    "armor_penetration_pct",
    "armor_penetration_flat",
    "armor_ignore_chance",
    "magical_damage",
    "magical_penetration",
    "main_hand_crit_cap",
    "evasion",
    "dodge_cap",
    "anti_dodge_chance",
    "parry",
    "parry_cap",
    "block",
    "shield_block_cap",
    "armor",
    "physical_resistance",
    "stamina",
    "stamina_regen",
    "magic_resist",
    "poison_resistance",
    "bleed_resistance",
    "environment_bio_resistance",
    "control_resistance",
    "mental_resistance",
    "counter_attack_chance",
)

RESOURCE_INT_MOD_KEYS = frozenset({"hp", "en", "stamina"})


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
        BasePowerAssembler.apply(actor, calculated_mods)
        calculated_mods = StatsEngine._normalize_calculated_mods(calculated_mods)

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
        StatsEngine._trace_stats(actor, calculated_mods, explanation)

        # 5. Сбрасываем флаги
        actor.dirty_stats.clear()

    @staticmethod
    def _trace_stats(actor: ActorSnapshot, calculated_mods: dict[str, float], explanation: dict[str, str]) -> None:
        values = {
            key: round(float(calculated_mods.get(key, 0.0)), 4)
            for key in TRACE_MOD_KEYS
            if key in calculated_mods or calculated_mods.get(key, 0.0) != 0.0
        }
        formulas = {key: explanation.get(key) for key in values if explanation.get(key)}
        log.bind(
            actor_id=actor.char_id,
            actor_name=actor.meta.name,
            dirty_stats=sorted(actor.dirty_stats),
            values=values,
            formulas=formulas,
        ).debug("CombatStats")

    @staticmethod
    def _normalize_calculated_mods(calculated_mods: dict[str, float]) -> dict[str, float | int]:
        normalized: dict[str, float | int] = dict(calculated_mods)
        for key in RESOURCE_INT_MOD_KEYS:
            if key in normalized:
                normalized[key] = max(0, int(round(float(normalized[key] or 0.0))))
        return normalized

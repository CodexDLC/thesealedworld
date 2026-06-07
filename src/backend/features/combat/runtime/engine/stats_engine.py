from typing import Any

from loguru import logger as log
from pydantic import ValidationError

from src.backend.core.calculators.stats_waterfall_calculator import StatsWaterfallCalculator
from src.backend.features.character.runtime.rules.base_power_assembler import BasePowerAssembler
from src.backend.features.combat.dto.actor import ActorLoadoutDTO, ActorRawDTO, ActorSnapshot, ActorStats
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
    "magic_armor",
    "shield_guard_power",
    "shield_style_guard_power_raw",
    "shield_style_guard_power_bonus",
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
    def build_stats(
        *,
        raw: ActorRawDTO | dict[str, Any],
        skills: dict[str, Any],
        loadout: ActorLoadoutDTO | dict[str, Any],
    ) -> tuple[ActorStats, dict[str, str]]:
        raw_data = raw.model_dump() if isinstance(raw, ActorRawDTO) else dict(raw)
        loadout_layout = loadout.layout if isinstance(loadout, ActorLoadoutDTO) else dict(loadout.get("layout") or {})

        calculated_mods, explanation = StatsWaterfallCalculator.calculate_waterfall(raw_data)
        BasePowerAssembler.apply_to_values(
            calculated_mods,
            loadout_layout=loadout_layout,
            skills=skills,
        )
        calculated_mods = StatsEngine._normalize_calculated_mods(calculated_mods)
        mods_dto = StatsEngine._modifiers_dto(calculated_mods)
        skills_dto = CombatSkillsDTO(**skills)
        return ActorStats(mods=mods_dto, skills=skills_dto), explanation

    @staticmethod
    def _recalculate_full(actor: ActorSnapshot) -> None:
        """
        Полный цикл пересчета.
        """
        actor.stats, actor.explanation = StatsEngine.build_stats(
            raw=actor.raw,
            skills=actor.skills,
            loadout=actor.loadout,
        )

        # 4. Сохраняем объяснения (для дебага/логов)
        calculated_mods = actor.stats.mods.model_dump()
        StatsEngine._trace_stats(actor, calculated_mods, actor.explanation)

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
        ).trace("CombatStats")

    @staticmethod
    def _normalize_calculated_mods(calculated_mods: dict[str, float]) -> dict[str, float | int]:
        normalized: dict[str, float | int] = dict(calculated_mods)
        for key in RESOURCE_INT_MOD_KEYS:
            if key in normalized:
                normalized[key] = max(0, int(round(float(normalized[key] or 0.0))))
        return normalized

    @staticmethod
    def _modifiers_dto(calculated_mods: dict[str, float | int]) -> CombatModifiersDTO:
        # Теперь ключи в calculated_mods (из StatsWaterfallCalculator -> stats_formulas -> StatKey)
        # должны совпадать с полями CombatModifiersDTO. extra='ignore' в DTO защитит от лишних полей.
        try:
            # Pydantic handles float->int conversion for HP/EN
            return CombatModifiersDTO(**calculated_mods)  # type: ignore
        except (ValidationError, TypeError) as e:
            # Логируем ошибку, но пытаемся продолжить с частичными данными
            # В реальном проде тут нужен алерт
            print(f"StatsEngine Error: {e}")
            valid_keys = CombatModifiersDTO.model_fields.keys()
            filtered_mods = {k: v for k, v in calculated_mods.items() if k in valid_keys}
            return CombatModifiersDTO(**filtered_mods)  # type: ignore

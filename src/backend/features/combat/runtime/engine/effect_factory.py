import contextlib
import uuid
from typing import Any

from src.backend.features.combat.dto import ActiveEffectDTO, ActorIdLike, normalize_actor_id
from src.backend.features.game_catalog.combat.resources.effects.schemas import ControlInstructionDTO, EffectTechnicalDTO


class EffectFactory:
    """
    Фабрика для создания и кастомизации ActiveEffectDTO.
    Инкапсулирует логику скалирования и сборки эффектов.
    """

    @staticmethod
    def create_effect(
        config: EffectTechnicalDTO,
        params: dict[str, Any],
        source_id: ActorIdLike,
        current_exchange: int,
        damage_ref: int = 0,
    ) -> ActiveEffectDTO:
        """
        Главный метод-оркестратор.
        Собирает финальный импакт, мутации и создает DTO.

        Args:
            config: Конфиг эффекта из GameData.
            params: Параметры наложения (из абилки/триггера).
            source_id: ID того, кто наложил.
            current_exchange: Текущий ход (для расчета expire).
            damage_ref: Ссылка на нанесенный урон (для эффектов типа Bleed).

        Returns:
            Готовый DTO эффекта. Numeric modifier applications apply later through
            ModifierApplicationService using this effect uid.
        """
        # 1. [BASE DATA]
        duration = params.get("duration", config.duration)
        power = params.get("power", 1.0)

        # 2. [IMPACT CALCULATION]
        final_impact = {}

        # A. Special Logic: Bleed (Кровотечение)
        # Если эффект имеет тег "bleed" и передан damage_ref, считаем от урона.
        if "bleed" in config.tags and damage_ref > 0:
            base_tick = abs(int(config.resource_impact.get("hp", 0))) if config.resource_impact else 0
            # Логика: 30% от урона (или как настроим).
            # Можно вынести коэффициент в константы или конфиг, но пока хардкод для MVP.
            # Если в params передан power, он может влиять на этот процент (например, 0.3 * power).
            bleed_ratio = 0.3 * power
            bleed_val = max(base_tick, int(damage_ref * bleed_ratio))
            if bleed_val < 1:
                bleed_val = 1

            final_impact["hp"] = -bleed_val

        # B. Standard Logic (Power Scaling)
        else:
            # Берем базу из конфига
            base_impact = config.resource_impact or {}

            # Если есть база, умножаем на power
            if base_impact:
                for res, val in base_impact.items():
                    final_impact[res] = int(val * power)

        # 3. [CONTROL LOGIC]
        # Приоритет: Params > Config.
        final_control = config.control_logic

        if "control" in params:
            # Если передан кастомный контроль, создаем DTO из dict.
            # Важно: params["control"] должен соответствовать структуре ControlInstructionDTO.
            with contextlib.suppress(Exception):
                final_control = ControlInstructionDTO(**params["control"])

        # 4. [CREATE DTO]
        effect_uid = str(uuid.uuid4())

        active_effect = ActiveEffectDTO(
            uid=effect_uid,
            effect_id=config.effect_id,
            source_id=normalize_actor_id(source_id),
            expire_at_exchange=current_exchange + duration,
            # Calculated State
            impact=final_impact,
            control=final_control,
            # Source Data (для наследования)
            power=power,
            params=params,  # Сохраняем исходные параметры
        )

        return active_effect

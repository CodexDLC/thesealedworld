import contextlib
import uuid
from typing import Any

from src.backend.domains.user_features.combat.dto import ActiveEffectDTO
from src.backend.resources.game_data.effects.schemas import ControlInstructionDTO, EffectDTO


class EffectFactory:
    """
    Фабрика для создания и кастомизации ActiveEffectDTO.
    Инкапсулирует логику скалирования и сборки эффектов.
    """

    @staticmethod
    def create_effect(
        config: EffectDTO,
        params: dict[str, Any],
        source_id: int,
        current_exchange: int,
        damage_ref: int = 0,
    ) -> tuple[ActiveEffectDTO, dict[str, Any]]:
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
            tuple[ActiveEffectDTO, dict[str, Any]]:
            1. Готовый DTO эффекта.
            2. Словарь мутаций (raw_modifiers), которые нужно применить к актору.
        """
        # 1. [BASE DATA]
        duration = params.get("duration", config.duration)
        power = params.get("power", 1.0)

        # 2. [IMPACT CALCULATION]
        final_impact = {}

        # A. Special Logic: Bleed (Кровотечение)
        # Если эффект имеет тег "bleed" и передан damage_ref, считаем от урона.
        if "bleed" in config.tags and damage_ref > 0:
            # Логика: 30% от урона (или как настроим).
            # Можно вынести коэффициент в константы или конфиг, но пока хардкод для MVP.
            # Если в params передан power, он может влиять на этот процент (например, 0.3 * power).
            bleed_ratio = 0.3 * power
            bleed_val = int(damage_ref * bleed_ratio)
            # Минимальный урон кровотока = 1
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

        # 3. [MUTATIONS CALCULATION]
        final_mutations = {}

        # A. Из конфига
        if config.raw_modifiers:
            final_mutations.update(config.raw_modifiers)

        # B. Из параметров (динамические)
        if "mutations" in params:
            final_mutations.update(params["mutations"])

        # 4. [CONTROL LOGIC]
        # Приоритет: Params > Config.
        final_control = config.control_logic

        if "control" in params:
            # Если передан кастомный контроль, создаем DTO из dict.
            # Важно: params["control"] должен соответствовать структуре ControlInstructionDTO.
            with contextlib.suppress(Exception):
                final_control = ControlInstructionDTO(**params["control"])

        # 5. [CREATE DTO]
        effect_uid = str(uuid.uuid4())

        active_effect = ActiveEffectDTO(
            uid=effect_uid,
            effect_id=config.effect_id,
            source_id=source_id,
            expire_at_exchange=current_exchange + duration,
            # Calculated State
            impact=final_impact,
            control=final_control,
            # Source Data (для наследования)
            power=power,
            params=params,  # Сохраняем исходные параметры
            # Memory (ключи, которые мы изменим)
            modified_keys=list(final_mutations.keys()),
        )

        return active_effect, final_mutations

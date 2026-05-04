from typing import Any, Literal

from loguru import logger as log

from src.backend.domains.user_features.combat.combat_engine.logic.math_core import MathCore
from src.backend.domains.user_features.combat.dto import (
    ActorSnapshot,
    CombatMoveDTO,
    PipelineContextDTO,
    PipelineFlagsDTO,
    PipelineModsDTO,
    PipelinePhasesDTO,
    PipelineStagesDTO,
)
from src.backend.domains.user_features.combat.dto.trigger_rules_flags_dto import TriggerRulesFlagsDTO


class ContextBuilder:
    """
    Фабрика контекста боя (Context Builder).
    Создает 'пульт управления' (PipelineContextDTO) для конкретного взаимодействия.
    """

    @staticmethod
    def build_context(
        actor: ActorSnapshot,
        target: ActorSnapshot | None,
        move: CombatMoveDTO,
        external_mods: dict[str, Any] | None = None,
    ) -> PipelineContextDTO:
        """
        Сборка контекста.
        НЕ сохраняет actor/target в DTO, только настраивает флаги.
        """
        # 1. Базовая инициализация (Чистый DTO)
        # result создается автоматически через default_factory
        ctx = PipelineContextDTO(
            phases=PipelinePhasesDTO(),
            flags=PipelineFlagsDTO(),
            mods=PipelineModsDTO(),
            stages=PipelineStagesDTO(),
            triggers=TriggerRulesFlagsDTO(),
        )

        # 2. Применение внешних модификаторов (Interference)
        if external_mods:
            ContextBuilder._apply_external_mods(ctx, external_mods)

        # 3. Анализ Интента (Move Analysis) - Атакующий
        ContextBuilder._analyze_intent(ctx, actor, move, external_mods)

        # 4. Анализ Защиты (Defense Analysis) - Защитник
        if target:
            ContextBuilder._analyze_defense(ctx, target)

        # 5. Инициализация Результата (Context Info)
        if ctx.result:
            ctx.result.source_id = int(actor.char_id)
            ctx.result.target_id = int(target.char_id) if target else None
            ctx.result.hand = ctx.flags.meta.source_type

            # 6. Проверка Dual Wield (Chain Reaction)
            # Если это Main Hand атака и у нас есть второе оружие -> ставим триггер
            if ctx.flags.meta.source_type == "main_hand" and ContextBuilder._check_dual_wield(actor):
                ctx.result.chain_events.trigger_offhand_attack = True
                log.info(f"ContextBuilder | Chain Event: Dual Wield triggered for {actor.char_id}")

        return ctx

    @staticmethod
    def _check_dual_wield(actor: ActorSnapshot) -> bool:
        """Проверяет возможность и шанс удара второй рукой."""
        off_hand_skill = actor.loadout.layout.get("off_hand")
        if not off_hand_skill or "shield" in off_hand_skill:
            return False

        skill_val = actor.skills.get("skill_dual_wield", 0.0)
        chance = 0.25 + (skill_val * 0.01)

        return MathCore.check_chance(chance)

    @staticmethod
    def _apply_external_mods(ctx: PipelineContextDTO, mods: dict[str, Any]) -> None:
        """
        Применяет модификаторы от InterferenceService.
        """
        if mods.get("disable_attack"):
            ctx.phases.run_calculator = False

        # Парсинг action_mode
        if "action_mode" in mods:
            mode = mods["action_mode"]
            if mode in ["exchange", "unidirectional"]:
                ctx.flags.meta.action_mode = mode

    @staticmethod
    def _analyze_intent(
        ctx: PipelineContextDTO, actor: ActorSnapshot, move: CombatMoveDTO, external_mods: dict[str, Any] | None
    ) -> None:
        """
        Настраивает мета-флаги Атаки (Source Type, Weapon Class).
        """
        strategy = move.strategy

        # 1. MAGIC / SKILL
        if strategy == "instant":
            ctx.flags.meta.source_type = "magic"
            return

        # 2. ITEM
        if strategy == "item":
            ctx.flags.meta.source_type = "item"
            return

        # 3. EXCHANGE (Melee/Ranged Attack)
        # Определяем Source Type (main_hand / off_hand)
        source_type: Literal["main_hand", "off_hand", "magic", "item"] = "main_hand"
        if external_mods:
            # Поддержка обоих ключей для совместимости
            if "hand" in external_mods:
                hand_val = external_mods["hand"]
                if hand_val == "off":
                    source_type = "off_hand"
                elif hand_val == "main":
                    source_type = "main_hand"
            elif "source_type" in external_mods:
                source_type = external_mods["source_type"]

        # Ensure source_type is one of the allowed literals
        if source_type not in ["main_hand", "off_hand", "magic", "item"]:
            source_type = "main_hand"  # Fallback default

        ctx.flags.meta.source_type = source_type

        # Определяем Weapon Class (для скиллов и триггеров)
        if source_type in ["main_hand", "off_hand"]:
            weapon_skill_key = actor.loadout.layout.get(source_type)
            # Пример: "skill_swords" -> "swords"
            if weapon_skill_key and weapon_skill_key.startswith("skill_"):
                ctx.flags.meta.weapon_class = weapon_skill_key.replace("skill_", "")

            # --- NEW: Weapon Trigger Activation ---
            # Берем триггер из layout (ключ с суффиксом _trigger)
            trigger_key = f"{source_type}_trigger"
            trigger_id = actor.loadout.layout.get(trigger_key)

            if trigger_id:
                ContextBuilder._activate_trigger_flag(ctx, trigger_id)

    @staticmethod
    def _activate_trigger_flag(ctx: PipelineContextDTO, trigger_id: str) -> None:
        """
        Активирует флаг триггера по ID.
        Поддерживает:
        1. Путь через точку: "accuracy.true_strike"
        2. Простое имя: "true_strike" (ищет во всех секциях)
        """
        # 1. Если это путь (section.field)
        if "." in trigger_id:
            parts = trigger_id.split(".")
            if len(parts) == 2:
                section_name, field_name = parts
                if hasattr(ctx.triggers, section_name):
                    section = getattr(ctx.triggers, section_name)
                    if hasattr(section, field_name):
                        setattr(section, field_name, True)
                        return

        # 2. Если это просто имя (ищем везде)
        for _section_name, section_model in ctx.triggers:
            if hasattr(section_model, trigger_id):
                setattr(section_model, trigger_id, True)
                return

    @staticmethod
    def _analyze_defense(ctx: PipelineContextDTO, target: ActorSnapshot) -> None:
        """
        Настраивает флаги Защиты (Armor Type, Shield).
        """
        layout = target.loadout.layout

        # 1. Armor Type (Body)
        body_skill = layout.get("body")
        if body_skill == "skill_light_armor":
            ctx.flags.mastery.light_armor = True
        elif body_skill == "skill_medium_armor":
            ctx.flags.mastery.medium_armor = True

        # 2. Shield (Off-hand)
        off_hand_skill = layout.get("off_hand")
        if off_hand_skill == "skill_shield":
            ctx.flags.mastery.shield_reflect = True

from typing import Any, Literal

from src.backend.features.combat.dto import (
    ActorSnapshot,
    CombatMoveDTO,
    PipelineContextDTO,
    PipelineFlagsDTO,
    PipelineModsDTO,
    PipelinePhasesDTO,
    PipelineStagesDTO,
)
from src.backend.features.combat.dto.trigger_rules import TriggerRulesFlagsDTO
from src.backend.features.combat.runtime.engine.trigger_activation import activate_trigger


class ContextBuilder:
    """Build the mutable pipeline control context for one interaction.

    ``ContextBuilder`` converts actor equipment, move strategy, external branch
    modifiers, and defensive posture into the normalized flag/mod/stage DTOs
    consumed by the rest of the combat pipeline.
    """

    @staticmethod
    def build_context(
        actor: ActorSnapshot,
        target: ActorSnapshot | None,
        move: CombatMoveDTO,
        external_mods: dict[str, Any] | None = None,
    ) -> PipelineContextDTO:
        """Construct a fresh pipeline context for one source-target interaction.

        Args:
            actor: Acting snapshot.
            target: Target snapshot when present.
            move: Runtime move being resolved.
            external_mods: Executor-injected branch modifiers such as counters.

        Returns:
            A fresh ``PipelineContextDTO`` with phases, flags, mods, stages,
            trigger flags, and result metadata initialized.
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
            ctx.result.source_id = actor.char_id
            ctx.result.target_id = target.char_id if target else None
            ctx.result.hand = ctx.flags.meta.source_type

        return ctx

    @staticmethod
    def _apply_external_mods(ctx: PipelineContextDTO, mods: dict[str, Any]) -> None:
        """Apply executor-level branch modifiers before semantic analysis."""
        if mods.get("disable_attack"):
            ctx.phases.run_calculator = False

        # Парсинг action_mode
        if "action_mode" in mods:
            mode = mods["action_mode"]
            if mode in ["exchange", "unidirectional"]:
                ctx.flags.meta.action_mode = mode
                ctx.flags.meta.grant_exchange_gift = mode == "exchange"

        if mods.get("is_counter_attack") or mods.get("feint_role") == "secondary" or mods.get("hand") == "off":
            ctx.flags.meta.grant_exchange_gift = False

        if "pay_cost" in mods:
            ctx.flags.mechanics.pay_cost = bool(mods["pay_cost"])

        if "generate_feints" in mods:
            ctx.flags.mechanics.generate_feints = bool(mods["generate_feints"])

        if "damage_mult" in mods:
            ctx.mods.damage_mult = float(mods["damage_mult"])

        if mods.get("is_counter_attack"):
            ctx.result.is_counter = True

    @staticmethod
    def _analyze_intent(
        ctx: PipelineContextDTO, actor: ActorSnapshot, move: CombatMoveDTO, external_mods: dict[str, Any] | None
    ) -> None:
        """Infer source-type, weapon-class, and trigger context from the move."""
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
            ctx.flags.meta.tactical_style_skill = actor.loadout.layout.get("tactical_style")
            weapon_skill_key = actor.loadout.layout.get(source_type)
            if source_type == "main_hand" and weapon_skill_key == "skill_archery":
                ctx.flags.restriction.ignore_parry = True
                if actor.loadout.ammo_charges.get(source_type, 0) > 0 and ctx.flags.mechanics.pay_cost:
                    ContextBuilder._attach_ammo_effect_payload(ctx, actor, source_type)
            # Пример: "skill_swords" -> "swords"
            if weapon_skill_key and weapon_skill_key.startswith("skill_"):
                ctx.flags.meta.weapon_class = weapon_skill_key.replace("skill_", "")

            # --- NEW: Weapon Trigger Activation ---
            # Берем триггер из layout (ключ с суффиксом _trigger)
            trigger_key = f"{source_type}_trigger"
            trigger_id = actor.loadout.layout.get(trigger_key)

            if trigger_id:
                activate_trigger(ctx, trigger_id, source="weapon", source_slot=source_type)

            style_trigger = actor.loadout.layout.get("tactical_style_trigger")
            if (
                source_type == "main_hand"
                and style_trigger
                and actor.loadout.layout.get("tactical_style") != "skill_shield_mastery"
            ):
                activate_trigger(
                    ctx,
                    style_trigger,
                    source="style",
                    source_id=actor.loadout.layout.get("tactical_style"),
                )

    @staticmethod
    def _activate_trigger_flag(ctx: PipelineContextDTO, trigger_id: str) -> None:
        """Activate one trigger into the pipeline trigger-flag surface."""
        activate_trigger(ctx, trigger_id, source="system")

    @staticmethod
    def _attach_ammo_effect_payload(ctx: PipelineContextDTO, actor: ActorSnapshot, source_slot: str) -> None:
        payload = actor.loadout.ammo_effects.get(source_slot)
        if not isinstance(payload, dict):
            return
        effects = payload.get("effects")
        if isinstance(effects, list):
            for effect in effects:
                if isinstance(effect, dict) and isinstance(effect.get("id") or effect.get("effect_id"), str):
                    ctx.trigger_effect_payloads.setdefault(source_slot, []).append(dict(effect))
            return
        if isinstance(payload.get("id") or payload.get("effect_id"), str):
            ctx.trigger_effect_payloads.setdefault(source_slot, []).append(dict(payload))

    @staticmethod
    def _analyze_defense(ctx: PipelineContextDTO, target: ActorSnapshot) -> None:
        """Infer defensive mastery flags and style triggers from target loadout."""
        layout = target.loadout.layout

        # 1. Armor Type (Body)
        body_skill = layout.get("body")
        if body_skill == "skill_light_armor":
            ctx.flags.mastery.light_armor = True
        elif body_skill == "skill_medium_armor":
            ctx.flags.mastery.medium_armor = True

        if (
            layout.get("main_hand") == "skill_archery"
            or layout.get("off_hand") == "skill_archery"
            or layout.get("tactical_style") == "skill_ranged_combat"
        ):
            ctx.flags.restriction.disable_passive_counter = True

        # 2. Shield (Off-hand)
        off_hand_skill = layout.get("off_hand")
        if off_hand_skill == "skill_shield_mastery":
            ctx.flags.mastery.shield_reflect = True
            style_trigger = layout.get("tactical_style_trigger")
            if layout.get("tactical_style") == "skill_shield_mastery" and style_trigger:
                activate_trigger(ctx, style_trigger, source="style", source_id=layout.get("tactical_style"))

        if layout.get("tactical_style") == "skill_ranged_combat":
            style_trigger = layout.get("tactical_style_trigger")
            if style_trigger:
                activate_trigger(ctx, style_trigger, source="style", source_id=layout.get("tactical_style"))

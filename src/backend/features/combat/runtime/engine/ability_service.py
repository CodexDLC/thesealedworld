from __future__ import annotations

import math
import uuid
from typing import TYPE_CHECKING, Any, Literal

from loguru import logger as log

from src.backend.features.combat.dto import (
    ActiveAbilityDTO,
    ActorSnapshot,
    CombatEffectFactDTO,
    CombatEventDTO,
    CombatMoveDTO,
    CombatResourceFactDTO,
    ExchangePayload,
    InstantPayload,
    PipelineContextDTO,
)
from src.backend.features.combat.integrations import CombatCatalogIntegrator as GameData
from src.backend.features.combat.runtime.engine.effect_factory import EffectFactory
from src.backend.features.combat.runtime.engine.feint_service import FeintService
from src.backend.features.combat.runtime.engine.modifier_application_service import ModifierApplicationService
from src.backend.features.combat.runtime.engine.pipeline_mutation_service import PipelineMutationService
from src.backend.features.combat.runtime.engine.stats_engine import StatsEngine
from src.backend.features.combat.runtime.engine.trigger_activation import activate_trigger
from src.backend.features.game_catalog.combat.resources.common.modifier_applications import ModifierApplicationDTO

if TYPE_CHECKING:
    from src.backend.features.game_catalog.combat.resources.abilities.schemas import AbilityCostDTO, AbilityTechnicalDTO
    from src.backend.features.game_catalog.combat.resources.feints.schemas import FeintTechnicalDTO


class AbilityService:
    """Apply ability, feint, and effect semantics around resolver execution.

    ``AbilityService`` owns the pre/post-calculation semantic layer of the inner
    combat pipeline. It inspects source and target statuses, spends ability or
    feint costs, injects pipeline mutations and triggers, queues effect payloads,
    consumes prepared reactions, and converts queued effect descriptions into
    concrete runtime effects.

    The resolver stays focused on hit/damage math. This service is where combat
    actions and statuses change the meaning of that math.
    """

    # ==============================================================================
    # PUBLIC INTERFACE (ORCHESTRATOR)
    # ==============================================================================

    def pre_process(
        self,
        ctx: PipelineContextDTO,
        move: CombatMoveDTO,
        source: ActorSnapshot,
        target: ActorSnapshot | None = None,
    ) -> None:
        """Prepare the pipeline context before resolver math runs.

        Args:
            ctx: Mutable pipeline context for the current interaction.
            move: Runtime move being resolved.
            source: Acting snapshot.
            target: Defending snapshot when the interaction has one.

        Side Effects:
            - Cleans up expired status effects.
            - Applies control/status mutations to pipeline flags and phases.
            - Spends ability or feint costs.
            - Registers triggers, temporary modifiers, and override damage rules.
        """
        # 1. [CLEANUP EXPIRED EFFECTS]
        AbilityService._cleanup_expired_effects_pre_calc(source)
        if target:
            AbilityService._cleanup_expired_effects_pre_calc(target)

        # 2. [SOURCE STATUS CHECK]
        self._apply_status_effects(ctx, source, mode="source")

        # 3. [TARGET STATUS CHECK]
        if target:
            self._apply_status_effects(ctx, target, mode="target")

        # 4. [ROUTING & LOGIC]
        if ctx.phases.run_calculator:
            # Строгая типизация извлечения ID
            ability_id = self._extract_action_id(move, mode="ability")
            feint_id = self._extract_action_id(move, mode="feint")

            if ability_id:
                self._process_action_logic(ctx, move, source, target, mode="ability")
            elif feint_id:
                self._process_action_logic(ctx, move, source, target, mode="feint")
            else:
                # Basic Attack (No CAST event needed? Or maybe "ATTACK"?)
                pass
        else:
            pass

    def post_process(
        self,
        ctx: PipelineContextDTO,
        source: ActorSnapshot,
        target: ActorSnapshot | None,
        move: CombatMoveDTO,
    ) -> None:
        """Finalize ability/effect consequences after resolver math completes.

        Args:
            ctx: Mutable pipeline context containing the interaction result.
            source: Acting snapshot.
            target: Defending snapshot when present.
            move: Runtime move that produced the interaction result.

        Side Effects:
            - Removes expired temporary ability modifiers.
            - Consumes prepared reactions tied to the current outcome.
            - Materializes queued effects and passive combat regeneration.
        """
        if not ctx.result:
            return

        # 1. [CLEANUP TEMP ABILITIES & COLLECT EFFECTS]
        self._process_temp_abilities_post_calc(ctx, source, target)

        # 2. [CONSUME PREPARED REACTIONS]
        self._process_prepared_reactions_post_calc(ctx, source, target)

        # 3. [EXECUTE EFFECTS]
        self._apply_queued_effects(ctx, source, target)

        # 4. [PASSIVE COMBAT REGEN]
        self._register_combat_regen(ctx, source)

    # ==============================================================================
    # ATOMIC STEPS: STATUS EFFECTS (FLAGS & MODS)
    # ==============================================================================

    @staticmethod
    def _apply_status_effects(ctx: PipelineContextDTO, actor: ActorSnapshot, mode: Literal["source", "target"]) -> None:
        """Apply active status effects into pipeline flags, phases, and mods."""
        for effect in actor.statuses.effects:
            effect_entry = GameData.get_effect_catalog_entry(effect.effect_id)
            effect_config = effect_entry.technical if effect_entry else None
            if effect_config and effect_config.pipeline_mutations:
                role = effect_config.pipeline_mutation_role
                if role == "both" or role == mode:
                    PipelineMutationService.apply(
                        applications=effect_config.pipeline_mutations,
                        ctx=ctx,
                        source="effect",
                    )

            if effect.control:
                behavior = effect.control.source_behavior if mode == "source" else effect.control.target_behavior
                if behavior:
                    if mode == "source" and behavior.get("can_act") is False:
                        ctx.phases.run_calculator = False
                        ctx.result.skip_reason = "CONTROLLED"

                    for path, value in behavior.items():
                        if path == "can_act":
                            continue
                        AbilityService._set_nested_flag(ctx, path, value)
            pass

    @staticmethod
    def _set_nested_flag(root_obj: Any, path: str, value: Any) -> None:
        parts = path.split(".")
        obj = root_obj
        try:
            if parts and not hasattr(obj, parts[0]) and hasattr(obj, "flags") and hasattr(obj.flags, parts[0]):
                obj = obj.flags
            for part in parts[:-1]:
                obj = getattr(obj, part)
            setattr(obj, parts[-1], value)
        except (AttributeError, ValueError):
            log.warning(f"AbilityService | Invalid flag path: {path}")

    # ==============================================================================
    # UNIVERSAL LOGIC HANDLER (PRE-CALC)
    # ==============================================================================

    @staticmethod
    def _extract_action_id(move: CombatMoveDTO, mode: Literal["ability", "feint"]) -> str | None:
        """Extract the relevant ability or feint id from a normalized move payload."""
        payload = move.payload

        # 1. Fallback для словарей (если Pydantic не сработал или legacy)
        if isinstance(payload, dict):
            if mode == "ability":
                return payload.get("ability_id")
            if mode == "feint":
                return payload.get("feint_id")
            return None

        # 2. Строгая проверка DTO
        if mode == "ability":
            # Ability ID есть только в InstantPayload
            if isinstance(payload, InstantPayload):
                return payload.ability_id
            return None

        if mode == "feint":
            # Feint ID есть и в ExchangePayload, и в InstantPayload
            if isinstance(payload, (ExchangePayload, InstantPayload)):
                return payload.feint_id
            return None

        return None

    @staticmethod
    def _process_action_logic(
        ctx: PipelineContextDTO,
        move: CombatMoveDTO,
        actor: ActorSnapshot,
        target: ActorSnapshot | None,
        mode: Literal["ability", "feint"],
    ) -> None:
        """Apply one ability or feint contract into the current pipeline context."""
        config: AbilityTechnicalDTO | FeintTechnicalDTO | None = None
        cost_ok = False
        action_id: str | None = None

        if mode == "ability":
            action_id = AbilityService._extract_action_id(move, mode="ability")
            if not action_id:
                return

            ability_entry = GameData.get_ability_catalog_entry(action_id)
            if ability_entry:
                config = ability_entry.technical
                cost_ok = AbilityService._check_ability_cost(actor, config.cost)
                if cost_ok:
                    AbilityService._register_ability_cost(ctx, config.cost)
                else:
                    ctx.phases.run_calculator = False
                    ctx.result.skip_reason = "NO_RESOURCE"
                    log.info(f"AbilityService | Not enough resources for ability {config.ability_id}")

        elif mode == "feint":
            action_id = AbilityService._extract_action_id(move, mode="feint")
            if not action_id:
                return

            feint_entry = GameData.get_feint_catalog_entry(action_id)
            if feint_entry:
                config = feint_entry.technical
                stamina_cost = FeintService.activation_stamina_cost(config.cost.tactics)
                cost_ok = actor.meta.stamina >= stamina_cost
                if cost_ok:
                    AbilityService._register_feint_activation_cost(ctx, stamina_cost)
                else:
                    ctx.phases.run_calculator = False
                    ctx.result.skip_reason = "NO_RESOURCE"
                    ctx.result.chain_events.preserve_feint = True
                    log.info(f"AbilityService | Not enough stamina for feint {config.feint_id}")

        if not config or not cost_ok:
            return

        ctx.result.action_facts.update(
            {
                "id": action_id,
                "role": mode,
                "cost": getattr(getattr(config, "cost", None), "model_dump", lambda **_: {})(),
                "target_count": 1 if target is not None else 0,
            }
        )

        # [EVENT] CAST
        ctx.result.events.append(
            CombatEventDTO(
                type="CAST", source_id=actor.char_id, target_id=target.char_id if target else None, action_id=action_id
            )
        )

        ability_uid = str(uuid.uuid4())
        modified_keys: list[str] = []
        modified_sources: dict[str, list[str]] = {}

        if config.modifier_applications:
            applied_modifiers = ModifierApplicationService.apply(
                applications=config.modifier_applications,
                owner=mode,
                owner_uid=ability_uid,
                owner_id=action_id,
                source=actor,
                target=target,
            )
            modified_keys = sorted(set(modified_keys) | applied_modifiers.modified_keys)
            AbilityService._merge_modified_sources(modified_sources, applied_modifiers.modified_sources)

        bonus_per_tier = float(getattr(config, "hit_damage_bonus_per_tier", 0.0))
        if mode == "feint" and bonus_per_tier > 0:
            weapon_tier = AbilityService._source_weapon_tier(actor, move)
            bonus_damage = bonus_per_tier * weapon_tier
            ctx.mods.weapon_technique_bonus_damage = bonus_damage
            applied_modifiers = ModifierApplicationService.apply(
                applications=[
                    ModifierApplicationDTO(
                        modifier_id="physical_damage_bonus_add",
                        value_override=bonus_damage,
                        tags=["weapon_technique", action_id or ""],
                    )
                ],
                owner=mode,
                owner_uid=ability_uid,
                owner_id=action_id or "",
                source=actor,
                target=target,
            )
            modified_keys = sorted(set(modified_keys) | applied_modifiers.modified_keys)
            AbilityService._merge_modified_sources(modified_sources, applied_modifiers.modified_sources)

        payload_effects: dict[str, Any] = {}
        prep_effects = getattr(config, "preparation_effects", None)
        if prep_effects:
            payload_effects["always"] = prep_effects

        effects = getattr(config, "effects", None)
        if effects:
            payload_effects["is_hit"] = effects

        # Determine ID for ActiveAbilityDTO
        active_id = action_id
        if mode == "ability":
            active_id = getattr(config, "ability_id", action_id)
        elif mode == "feint":
            active_id = getattr(config, "feint_id", action_id)

        active_ability = ActiveAbilityDTO(
            uid=ability_uid,
            ability_id=active_id,  # type: ignore # Pydantic validator handles this usually
            source_id=actor.char_id,
            expire_at_exchange=AbilityService._ability_expire_exchange(actor.meta.exchange_counter, config),
            modified_keys=modified_keys,
            modified_sources=modified_sources,
            payload={"effects": payload_effects},
        )
        actor.statuses.abilities.append(active_ability)

        if config.pipeline_mutations:
            if hasattr(config.pipeline_mutations, "preset") and config.pipeline_mutations.preset:
                PipelineMutationService.apply(
                    applications=GameData.get_pipeline_preset(config.pipeline_mutations.preset),
                    ctx=ctx,
                    source=mode,
                    source_id=action_id,
                )

            mutation_applications = (
                config.pipeline_mutations.applications
                if hasattr(config.pipeline_mutations, "applications")
                else config.pipeline_mutations
            )
            if mutation_applications:
                PipelineMutationService.apply(
                    applications=mutation_applications,
                    ctx=ctx,
                    source=mode,
                    source_id=action_id,
                )

        if config.triggers:
            for trigger in config.triggers:
                activate_trigger(ctx, trigger, source=mode, source_id=action_id)

        if config.override_damage:
            ctx.override_damage = config.override_damage

    # ==============================================================================
    # UNIVERSAL LOGIC HANDLER (POST-CALC)
    # ==============================================================================

    @staticmethod
    def _process_temp_abilities_post_calc(
        ctx: PipelineContextDTO, source: ActorSnapshot, target: ActorSnapshot | None
    ) -> None:
        """Expire temporary abilities and queue their deferred effect payloads."""
        current_exchange = source.meta.exchange_counter
        to_remove = []

        for ability in source.statuses.abilities:
            if ability.expire_at_exchange <= current_exchange:
                if ability.modified_sources:
                    ModifierApplicationService.remove_temp_sources(source, ability.modified_sources)
                    if target:
                        ModifierApplicationService.remove_temp_sources(target, ability.modified_sources)

                effects_map = ability.payload.get("effects", {})
                if effects_map:
                    conditions = {
                        "always": True,
                        "is_hit": ctx.result.is_hit,
                        "is_crit": ctx.result.is_crit,
                        "is_blocked": ctx.result.is_blocked,
                        "is_parried": ctx.result.is_parried,
                        "is_dodged": ctx.result.is_dodged,
                        "is_miss": ctx.result.is_miss,
                    }

                    for cond_key, effects_list in effects_map.items():
                        if conditions.get(cond_key):
                            for effect_data in effects_list:
                                AbilityService._queue_effect(ctx, effect_data, source, target)

                to_remove.append(ability)

        for ability in to_remove:
            source.statuses.abilities.remove(ability)

    @staticmethod
    def _process_prepared_reactions_post_calc(
        ctx: PipelineContextDTO, source: ActorSnapshot, target: ActorSnapshot | None
    ) -> None:
        outcome = AbilityService._result_outcome(ctx)
        if not outcome:
            return

        AbilityService._process_actor_prepared_reactions(ctx, source, actor_role="source", outcome=outcome)
        if target:
            AbilityService._process_actor_prepared_reactions(ctx, target, actor_role="target", outcome=outcome)

    @staticmethod
    def _process_actor_prepared_reactions(
        ctx: PipelineContextDTO,
        actor: ActorSnapshot,
        *,
        actor_role: Literal["source", "target"],
        outcome: str,
    ) -> None:
        to_remove = []
        for effect in actor.statuses.effects:
            effect_entry = GameData.get_effect_catalog_entry(effect.effect_id)
            if not effect_entry:
                continue
            config = effect_entry.technical
            if outcome not in config.react_on_outcomes:
                continue
            if config.pipeline_mutation_role not in {actor_role, "both"}:
                continue

            AbilityService._apply_prepared_reaction_result(ctx, actor, effect.effect_id, effect.params)
            ctx.result.effect_facts.append(
                CombatEffectFactDTO(
                    actor_id=actor.char_id,
                    owner=actor_role,
                    effect_id=effect.effect_id,
                    action="expire" if config.consume_on_reaction else "tick",
                    source_effect_id=effect.effect_id,
                    tags=["prepared_reaction", outcome],
                )
            )
            if config.consume_on_reaction:
                if effect.modified_sources:
                    ModifierApplicationService.remove_temp_sources(actor, effect.modified_sources)
                to_remove.append(effect)

        for effect in to_remove:
            actor.statuses.effects.remove(effect)

    @staticmethod
    def _apply_prepared_reaction_result(
        ctx: PipelineContextDTO, actor: ActorSnapshot, effect_id: str, params: dict[str, Any]
    ) -> None:
        if effect_id != "spiked_guard":
            return
        reflected_damage = AbilityService._int_param(params, "reflect_damage", default=5)
        if reflected_damage <= 0:
            return
        ctx.result.reflected_damage += reflected_damage
        ctx.result.resource_facts.append(
            CombatResourceFactDTO(
                actor_id=ctx.result.source_id,
                owner="source",
                resource="hp",
                reason="prepared_reflect",
                delta=-reflected_damage,
                source_effect_id=effect_id,
                tags=["prepared_reaction", "block", "reflect", f"defender:{actor.char_id}"],
            )
        )

    @staticmethod
    def _queue_effect(
        ctx: PipelineContextDTO, effect_data: dict, source: ActorSnapshot, target: ActorSnapshot | None
    ) -> None:
        """Append one effect payload to the post-calculation application queue."""
        if "target_id" not in effect_data:
            target_actor = effect_data.get("target_actor")
            if target_actor == "source":
                real_target = source
            elif target_actor == "target":
                real_target = target if target else source
            else:
                real_target = target if target else source
            effect_data["target_id"] = real_target.char_id

        ctx.result.applied_effects.append(effect_data)

    @staticmethod
    def _source_weapon_tier(actor: ActorSnapshot, move: CombatMoveDTO) -> int:
        payload = move.payload
        hand = getattr(payload, "hand", None)
        source_type = "off_hand" if hand == "off" else "main_hand"
        tiers = getattr(actor.loadout, "weapon_tiers", {}) or {}
        try:
            return max(1, int(tiers.get(source_type, 1)))
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _merge_modified_sources(target: dict[str, list[str]], source: dict[str, list[str]]) -> None:
        for key, source_ids in source.items():
            target.setdefault(key, []).extend(source_ids)

    @staticmethod
    def _apply_queued_effects(ctx: PipelineContextDTO, source: ActorSnapshot, target: ActorSnapshot | None) -> None:
        """Convert queued effect payloads into concrete runtime state mutations."""
        for effect_data in ctx.result.applied_effects:
            if not AbilityService._effect_conditions_met(ctx, effect_data):
                continue

            target_char_id = effect_data.get("target_id")
            effect_target = source if target_char_id == source.char_id else target
            if not effect_target:
                continue

            effect_id = effect_data.get("id") or effect_data.get("effect_id")

            # 2. Instant Actions (Heal/Cleanse)
            if effect_id == "restore_hp":
                val = effect_data.get("params", {}).get("value", 0)
                if "hp" not in ctx.result.resource_changes:
                    ctx.result.resource_changes["hp"] = {}
                ctx.result.resource_changes["hp"]["heal"] = f"+{val}"
                ctx.result.effect_facts.append(
                    CombatEffectFactDTO(
                        actor_id=effect_target.char_id,
                        owner=AbilityService._fact_owner(ctx, effect_target.char_id),
                        effect_id="restore_hp",
                        action="apply",
                        value=val,
                        resource="hp",
                        source_trigger_id=effect_data.get("source_trigger_id"),
                    )
                )

                # [EVENT] HEAL
                ctx.result.events.append(
                    CombatEventDTO(
                        type="HEAL",
                        source_id=source.char_id,
                        target_id=effect_target.char_id,
                        value=val,
                        resource="hp",
                        action_id="restore_hp",
                    )
                )
                continue

            # 3. Create Active Effect (Factory)
            if not isinstance(effect_id, str):
                continue

            catalog_entry = GameData.get_effect_catalog_entry(effect_id)
            if not catalog_entry:
                continue
            config = catalog_entry.technical

            params = effect_data.get("params", {})

            # ВАЖНО: Передаем damage_final как damage_ref для скалирования (например, Bleed)
            damage_ref = ctx.result.damage_final if ctx.result.damage_final > 0 else 0

            active_effect = EffectFactory.create_effect(
                config=config,
                params=params,
                source_id=source.char_id,
                current_exchange=source.meta.exchange_counter,
                damage_ref=damage_ref,  # Передаем урон
            )

            if config.modifier_applications:
                applied_modifiers = ModifierApplicationService.apply(
                    applications=config.modifier_applications,
                    owner="effect",
                    owner_uid=active_effect.uid,
                    owner_id=active_effect.effect_id,
                    source=source,
                    target=effect_target,
                )
                active_effect.modified_keys = sorted(set(active_effect.modified_keys) | applied_modifiers.modified_keys)
                active_effect.modified_sources = applied_modifiers.modified_sources

            effect_target.statuses.effects.append(active_effect)
            ctx.result.effect_facts.append(
                CombatEffectFactDTO(
                    actor_id=effect_target.char_id,
                    owner=AbilityService._fact_owner(ctx, effect_target.char_id),
                    effect_id=active_effect.effect_id,
                    action="apply",
                    duration=max(0, active_effect.expire_at_exchange - source.meta.exchange_counter),
                    source_trigger_id=effect_data.get("source_trigger_id"),
                )
            )

            # [EVENT] APPLY_EFFECT
            ctx.result.events.append(
                CombatEventDTO(
                    type="APPLY_EFFECT", source_id=source.char_id, target_id=effect_target.char_id, action_id=effect_id
                )
            )

    @staticmethod
    def _register_combat_regen(ctx: PipelineContextDTO, source: ActorSnapshot) -> None:
        if not source.is_alive:
            return

        StatsEngine.ensure_stats(source)
        if not source.stats:
            return

        regen_sources = (
            ("hp", source.stats.mods.hp_regen),
            ("en", source.stats.mods.en_regen),
            ("stamina", source.stats.mods.stamina_regen),
        )
        for resource, regen_value in regen_sources:
            delta = AbilityService._combat_regen_delta(regen_value)
            if delta <= 0:
                continue
            ctx.result.resource_changes.setdefault(resource, {})["combat_regen"] = f"+{delta}"

    @staticmethod
    def _combat_regen_delta(value: float) -> int:
        numeric = max(0.0, float(value or 0.0))
        if numeric <= 0:
            return 0
        return max(1, int(math.floor(numeric)))

    @staticmethod
    def _effect_conditions_met(ctx: PipelineContextDTO, effect_data: dict[str, Any]) -> bool:
        conditions = effect_data.get("conditions")
        if not isinstance(conditions, dict):
            return True

        result = ctx.result
        flags = {
            "always": True,
            "is_hit": result.is_hit,
            "is_crit": result.is_crit,
            "is_blocked": result.is_blocked,
            "is_parried": result.is_parried,
            "is_dodged": result.is_dodged,
            "is_miss": result.is_miss,
        }
        return all(flags.get(str(key)) is bool(value) for key, value in conditions.items())

    @staticmethod
    def _result_outcome(ctx: PipelineContextDTO) -> str:
        result = ctx.result
        if result.is_miss:
            return "miss"
        if result.is_dodged:
            return "dodge"
        if result.is_parried:
            return "parry"
        if result.is_blocked:
            return "block"
        if result.is_hit:
            return "crit" if result.is_crit else "hit"
        if result.healing_final > 0:
            return "heal"
        return ""

    @staticmethod
    def _int_param(params: dict[str, Any], key: str, *, default: int) -> int:
        try:
            return int(params.get(key, default))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _fact_owner(
        ctx: PipelineContextDTO, actor_id: int | str | None
    ) -> Literal["source", "target", "self", "other"]:
        if actor_id is None:
            return "other"
        actor_key = str(actor_id)
        if ctx.result.source_id is not None and actor_key == str(ctx.result.source_id):
            return "source"
        if ctx.result.target_id is not None and actor_key == str(ctx.result.target_id):
            return "target"
        return "other"

    @staticmethod
    def _cleanup_expired_effects_pre_calc(actor: ActorSnapshot) -> None:
        """Remove effects that expired before the current exchange starts."""
        current_exchange = actor.meta.exchange_counter
        to_remove = []

        for effect in actor.statuses.effects:
            if effect.expire_at_exchange < current_exchange:
                if effect.modified_sources:
                    ModifierApplicationService.remove_temp_sources(actor, effect.modified_sources)

                to_remove.append(effect)

        for effect in to_remove:
            actor.statuses.effects.remove(effect)

    # ==============================================================================
    # HELPERS
    # ==============================================================================

    @staticmethod
    def _check_ability_cost(actor: ActorSnapshot, cost: AbilityCostDTO) -> bool:
        return (
            actor.meta.en >= cost.energy
            and actor.meta.hp >= cost.hp
            and actor.meta.tokens.get("gift", 0) >= cost.gift_tokens
        )

    @staticmethod
    def _register_ability_cost(ctx: PipelineContextDTO, cost: AbilityCostDTO) -> None:
        if cost.energy > 0:
            if "en" not in ctx.result.resource_changes:
                ctx.result.resource_changes["en"] = {}
            ctx.result.resource_changes["en"]["cost"] = f"-{cost.energy}"
        if cost.hp > 0:
            if "hp" not in ctx.result.resource_changes:
                ctx.result.resource_changes["hp"] = {}
            ctx.result.resource_changes["hp"]["cost"] = f"-{cost.hp}"
        if cost.gift_tokens > 0:
            if "gift" not in ctx.result.resource_changes:
                ctx.result.resource_changes["gift"] = {}
            ctx.result.resource_changes["gift"]["cost"] = f"-{cost.gift_tokens}"

    @staticmethod
    def _register_feint_activation_cost(ctx: PipelineContextDTO, stamina_cost: int) -> None:
        if stamina_cost <= 0:
            return
        if "stamina" not in ctx.result.resource_changes:
            ctx.result.resource_changes["stamina"] = {}
        ctx.result.resource_changes["stamina"]["cost"] = f"-{stamina_cost}"

    @staticmethod
    def _ability_expire_exchange(current_exchange: int, config: AbilityTechnicalDTO | FeintTechnicalDTO) -> int:
        expire_at_exchange = current_exchange
        for application in config.modifier_applications:
            if application.scope == "duration":
                duration = application.duration_exchanges or 1
                expire_at_exchange = max(expire_at_exchange, current_exchange + duration)
        return expire_at_exchange

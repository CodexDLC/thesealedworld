from typing import Literal

# === НОВЫЙ ИМПОРТ ===
from src.backend.core.calculators.stats_waterfall_calculator import StatsWaterfallCalculator
from src.backend.features.combat.dto import (
    ActiveEffectDTO,
    ActorSnapshot,
    CombatDeathFactDTO,
    CombatEffectFactDTO,
    CombatEventDTO,
    CombatResourceFactDTO,
    CombatStatusRemovalDTO,
    CombatTokenFactDTO,
    InteractionResultDTO,
    PipelineContextDTO,
)
from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.combat.runtime.engine.feint_service import FeintService
from src.backend.features.combat.runtime.engine.modifier_application_service import ModifierApplicationService

BLOOD_TOKEN_DAMAGE_STEP = 10
PRESSURE_TOKEN_DAMAGE_STEP = BLOOD_TOKEN_DAMAGE_STEP
GIFT_TOKEN_PER_EXCHANGE = 1
BLOOD_MARKER = "blood"
PRESSURE_MARKER = "pressure"
GIFT_MARKER = "gift"


class MechanicsService:
    """Apply resolved interaction results to mutable actor runtime state.

    ``MechanicsService`` is the state-mutation layer after resolver math and
    ability post-processing. It turns resource deltas, damage, tokens, effect
    ticks, death checks, and XP events into concrete changes on actor snapshots
    plus structured combat facts for logging and commit.
    """

    # ==============================================================================
    # PUBLIC INTERFACE
    # ==============================================================================

    def process_turn_start(self, ctx: PipelineContextDTO, actor: ActorSnapshot) -> None:
        """Apply start-of-turn periodic effects for a single actor."""
        # Проверка флага: применять ли периодические эффекты
        if ctx.flags.mechanics.apply_periodic:
            # 1. Collect Ticks
            hp_changes = []
            en_changes = []
            hp_effect_ids = []
            en_effect_ids = []

            for effect in actor.statuses.effects:
                if not effect.impact:
                    continue

                # HP Impact
                if "hp" in effect.impact:
                    val = effect.impact["hp"]
                    hp_changes.append(str(val))
                    hp_effect_ids.append(effect.effect_id)
                    self._log_effect_tick(ctx, actor, effect.effect_id, val, "hp")

                # EN Impact
                if "en" in effect.impact:
                    val = effect.impact["en"]
                    en_changes.append(str(val))
                    en_effect_ids.append(effect.effect_id)
                    self._log_effect_tick(ctx, actor, effect.effect_id, val, "en")

            # 2. Apply Changes
            if hp_changes:
                applied = self._apply_resource_delta(actor, "hp", hp_changes)
                self._record_resource_fact(
                    ctx.result,
                    actor=actor,
                    owner="self",
                    resource="hp",
                    reason="effect_tick",
                    applied=applied,
                    source_effect_id=hp_effect_ids[0] if len(hp_effect_ids) == 1 else None,
                    tags=hp_effect_ids,
                )
            if en_changes:
                applied = self._apply_resource_delta(actor, "en", en_changes)
                self._record_resource_fact(
                    ctx.result,
                    actor=actor,
                    owner="self",
                    resource="en",
                    reason="effect_tick",
                    applied=applied,
                    source_effect_id=en_effect_ids[0] if len(en_effect_ids) == 1 else None,
                    tags=en_effect_ids,
                )

            if actor.meta.hp <= 0 and not actor.meta.is_dead:
                actor.meta.is_dead = True
                ctx.result.death_facts.append(
                    CombatDeathFactDTO(actor_id=actor.char_id, owner="self", reason="effect_tick")
                )
                ctx.result.events.append(
                    CombatEventDTO(
                        type="DEATH",
                        source_id=actor.char_id,
                        target_id=actor.char_id,
                        value=0,
                    )
                )

    def apply_interaction_result(
        self, ctx: PipelineContextDTO, source: ActorSnapshot, target: ActorSnapshot | None, result: InteractionResultDTO
    ) -> None:
        """Apply one interaction result to source and target actor state.

        Args:
            ctx: Mutable pipeline context for the resolved interaction.
            source: Acting snapshot to mutate with costs, tokens, and XP.
            target: Defending snapshot to mutate with damage/tokens when present.
            result: Resolver/post-process output to materialize.
        """
        # 1. [SOURCE] Apply Costs & Tokens
        self._apply_source_changes(ctx, source, target, result)

        # 2. [TARGET] Apply Damage
        if target:
            self._apply_target_changes(ctx, source, target, result)

        # 2.5. [RESOURCES] Commit actor-specific staged resource deltas.
        self._apply_staged_resource_applications(source, target, result)

        # 3. [XP] Register Events
        self._register_xp_events(ctx, source, target, result)

        # 3.25. [SHIELD OPENING] Existing opening lasts through this exchange
        # against its source, then drops before newly staged effects are applied.
        if target:
            self._consume_shield_opening_between(source, target, result)

        # 3.5. [STATUS] Commit staged effects/removals after resource math.
        self._apply_staged_status_changes(ctx, source, target, result)

        # 4. [FEINTS] One-way actions can still refill locally. Exchange hands are
        # rerolled once in CombatExecutor after the full paired exchange resolves.
        if ctx.flags.mechanics.generate_feints and ctx.flags.meta.action_mode == "unidirectional":
            # Получаем размер руки из статов (если есть) или дефолт 3
            source_hand = source.stats.mods.hand_size if source.stats else 3
            FeintService.refill_hand(source.meta, hand_size=source_hand)

            if target:
                target_hand = target.stats.mods.hand_size if target.stats else 3
                FeintService.refill_hand(target.meta, hand_size=target_hand)

    def apply_exchange_results(
        self,
        ctx: PipelineContextDTO,
        pairs: list[tuple[ActorSnapshot, ActorSnapshot | None, InteractionResultDTO]],
    ) -> None:
        """Commit a simultaneous exchange layer after all results were calculated."""
        for source, target, result in pairs:
            self.apply_interaction_result(ctx, source, target, result)

    # ==============================================================================
    # INTERNAL LOGIC
    # ==============================================================================

    def _apply_source_changes(
        self,
        ctx: PipelineContextDTO,
        source: ActorSnapshot,
        target: ActorSnapshot | None,
        result: InteractionResultDTO,
    ) -> None:
        """Apply source-side costs, token awards, and reflected damage."""
        # A. Costs (из resource_changes)
        if ctx.flags.mechanics.pay_cost:
            hp_changes: list[tuple[str, str]] = []
            en_changes: list[tuple[str, str]] = []
            stamina_changes: list[tuple[str, str]] = []
            gift_changes: list[tuple[str, str]] = []
            token_changes: dict[str, list[tuple[str, str]]] = {}

            # Пример: {"hp": {"cost": "-10"}, "en": {"cost": "-20"}, "stamina": {"cost": "-10"}}
            if "hp" in result.resource_changes:
                hp_changes.extend(result.resource_changes["hp"].items())

            if "en" in result.resource_changes:
                en_changes.extend(result.resource_changes["en"].items())

            if "stamina" in result.resource_changes:
                stamina_changes.extend(result.resource_changes["stamina"].items())

            if "gift" in result.resource_changes:
                gift_changes.extend(result.resource_changes["gift"].items())

            resource_keys = {"hp", "en", "stamina", "gift"}
            for resource, changes in result.resource_changes.items():
                if resource in resource_keys:
                    continue
                token_changes.setdefault(resource, []).extend(changes.items())

            # Apply Costs
            if hp_changes:
                applied = self._apply_resource_delta(source, "hp", [val for _key, val in hp_changes])
                self._record_resource_fact(
                    result,
                    actor=source,
                    owner="source",
                    resource="hp",
                    reason=self._resource_change_reason(hp_changes),
                    applied=applied,
                )
            if en_changes:
                applied = self._apply_resource_delta(source, "en", [val for _key, val in en_changes])
                self._record_resource_fact(
                    result,
                    actor=source,
                    owner="source",
                    resource="en",
                    reason=self._resource_change_reason(en_changes),
                    applied=applied,
                )
            if stamina_changes:
                applied = self._apply_resource_delta(source, "stamina", [val for _key, val in stamina_changes])
                self._record_resource_fact(
                    result,
                    actor=source,
                    owner="source",
                    resource="stamina",
                    reason=self._resource_change_reason(stamina_changes),
                    applied=applied,
                )
            if gift_changes:
                self._apply_token_delta(
                    result,
                    actor=source,
                    owner="source",
                    token=GIFT_MARKER,
                    sources=[val for _key, val in gift_changes],
                    reason=self._resource_change_reason(gift_changes),
                )
            for token, token_change_list in token_changes.items():
                self._apply_token_delta(
                    result,
                    actor=source,
                    owner="source",
                    token=token,
                    sources=[val for _key, val in token_change_list],
                    reason=self._resource_change_reason(token_change_list),
                )

        self._apply_ammo_spend(source, result)

        # B. Tokens Awarded (Всегда начисляем, если не сказано иное? Пока оставим безусловно)
        if result.tokens_awarded_attacker:
            for token, amount in result.tokens_awarded_attacker.items():
                if self._token_award_already_materialized(
                    result,
                    actor_id=source.char_id,
                    owner="source",
                    token=token,
                ):
                    continue
                before = source.meta.tokens.get(token, 0)
                source.meta.tokens[token] = source.meta.tokens.get(token, 0) + amount
                result.token_facts.append(
                    CombatTokenFactDTO(
                        actor_id=source.char_id,
                        owner="source",
                        token=token,
                        amount=amount,
                        before=before,
                        after=source.meta.tokens[token],
                        reason="award",
                    )
                )

        self._grant_exchange_gift_token(ctx, source, result)

        # C. Reflected damage from defender-side block style.
        if ctx.flags.mechanics.apply_damage and result.reflected_damage > 0:
            applied = self._apply_resource_delta(source, "hp", [f"-{result.reflected_damage}"])
            self._record_resource_fact(
                result,
                actor=source,
                owner="source",
                resource="hp",
                reason="reflect",
                applied=applied,
                tags=["REFLECT"],
            )
            self._apply_damage_taken_token_progress(
                result,
                actor=source,
                owner="source",
                applied=applied,
                token_bucket=result.tokens_awarded_attacker,
            )
            if target:
                self._apply_damage_dealt_token_progress(
                    result,
                    actor=target,
                    owner="target",
                    applied=applied,
                    token_bucket=result.tokens_awarded_defender,
                )
            result.events.append(
                CombatEventDTO(
                    type="HIT",
                    source_id=result.target_id or source.char_id,
                    target_id=source.char_id,
                    value=result.reflected_damage,
                    resource="hp",
                    tags=["REFLECT"],
                )
            )

            if ctx.flags.mechanics.check_death and source.meta.hp <= 0:
                source.meta.is_dead = True
                result.death_facts.append(CombatDeathFactDTO(actor_id=source.char_id, owner="source", reason="reflect"))
                result.events.append(
                    CombatEventDTO(
                        type="DEATH",
                        source_id=source.char_id,
                        target_id=source.char_id,
                        value=0,
                    )
                )

        if ctx.flags.mechanics.apply_damage and result.shield_counter_damage > 0:
            applied = self._apply_resource_delta(source, "hp", [f"-{result.shield_counter_damage}"])
            self._record_resource_fact(
                result,
                actor=source,
                owner="source",
                resource="hp",
                reason="shield_counter",
                applied=applied,
                tags=["SHIELD_COUNTER"],
            )
            self._apply_damage_taken_token_progress(
                result,
                actor=source,
                owner="source",
                applied=applied,
                token_bucket=result.tokens_awarded_attacker,
            )
            if target:
                self._apply_damage_dealt_token_progress(
                    result,
                    actor=target,
                    owner="target",
                    applied=applied,
                    token_bucket=result.tokens_awarded_defender,
                )

            if ctx.flags.mechanics.check_death and source.meta.hp <= 0:
                source.meta.is_dead = True
                result.death_facts.append(
                    CombatDeathFactDTO(actor_id=source.char_id, owner="source", reason="shield_counter")
                )
                result.events.append(
                    CombatEventDTO(
                        type="DEATH",
                        source_id=source.char_id,
                        target_id=source.char_id,
                        value=0,
                    )
                )

        if ctx.flags.mechanics.apply_damage and result.ranged_punish_damage > 0:
            applied = self._apply_resource_delta(source, "hp", [f"-{result.ranged_punish_damage}"])
            self._record_resource_fact(
                result,
                actor=source,
                owner="source",
                resource="hp",
                reason="ranged_far_punish",
                applied=applied,
                source_trigger_id="style_ranged_perfect_backstep",
                tags=["RANGED_PUNISH", "CRIT"],
            )
            self._apply_damage_taken_token_progress(
                result,
                actor=source,
                owner="source",
                applied=applied,
                token_bucket=result.tokens_awarded_attacker,
            )
            if target:
                self._apply_damage_dealt_token_progress(
                    result,
                    actor=target,
                    owner="target",
                    applied=applied,
                    token_bucket=result.tokens_awarded_defender,
                )

            if ctx.flags.mechanics.check_death and source.meta.hp <= 0:
                source.meta.is_dead = True
                result.death_facts.append(
                    CombatDeathFactDTO(actor_id=source.char_id, owner="source", reason="ranged_far_punish")
                )
                result.events.append(
                    CombatEventDTO(
                        type="DEATH",
                        source_id=source.char_id,
                        target_id=source.char_id,
                        value=0,
                    )
                )

    @staticmethod
    def _apply_ammo_spend(source: ActorSnapshot, result: InteractionResultDTO) -> None:
        for slot, raw_amount in result.ammo_spent.items():
            try:
                amount = max(0, int(raw_amount))
            except (TypeError, ValueError):
                continue
            if amount <= 0:
                continue
            before = max(0, int(source.loadout.ammo_charges.get(slot, 0) or 0))
            applied = min(before, amount)
            after = before - applied
            source.loadout.ammo_charges[slot] = after
            if applied <= 0:
                continue
            result.resource_facts.append(
                CombatResourceFactDTO(
                    actor_id=source.char_id,
                    owner="source",
                    resource="ammo",
                    reason="ammo_crit",
                    delta=-applied,
                    before=before,
                    after=after,
                    max=source.loadout.ammo_charge_caps.get(slot),
                    tags=["ammo", slot],
                )
            )

    def _apply_staged_status_changes(
        self, ctx: PipelineContextDTO, source: ActorSnapshot, target: ActorSnapshot | None, result: InteractionResultDTO
    ) -> None:
        actors = {str(source.char_id): source}
        if target:
            actors[str(target.char_id)] = target

        for removal in result.status_removals:
            actor_id = getattr(removal, "actor_id", None) if not isinstance(removal, dict) else removal.get("actor_id")
            actor = actors.get(str(actor_id)) if actor_id is not None else None
            if not actor:
                continue
            effect_uid = (
                getattr(removal, "effect_uid", None) if not isinstance(removal, dict) else removal.get("effect_uid")
            )
            effect_id = (
                getattr(removal, "effect_id", None) if not isinstance(removal, dict) else removal.get("effect_id")
            )
            kept_effects = []
            for effect in actor.statuses.effects:
                should_remove = (effect_uid and effect.uid == effect_uid) or (
                    effect_id and not effect_uid and effect.effect_id == effect_id
                )
                if should_remove:
                    if effect.modified_sources:
                        ModifierApplicationService.remove_temp_sources(actor, effect.modified_sources)
                    continue
                kept_effects.append(effect)
            actor.statuses.effects = kept_effects
            actor.statuses.abilities = [
                ability
                for ability in actor.statuses.abilities
                if not (
                    (effect_uid and ability.uid == effect_uid)
                    or (effect_id and not effect_uid and ability.ability_id == effect_id)
                )
            ]

        for application in result.status_applications:
            actor_id = (
                getattr(application, "actor_id", None)
                if not isinstance(application, dict)
                else application.get("actor_id") or application.get("target_id")
            )
            actor = actors.get(str(actor_id)) if actor_id is not None else None
            if not actor:
                continue
            active_raw = (
                getattr(application, "active_effect", None)
                if not isinstance(application, dict)
                else application.get("active_effect")
            )
            if active_raw:
                active_effect = ActiveEffectDTO.model_validate(active_raw)
            else:
                effect_id = (
                    getattr(application, "effect_id", None)
                    if not isinstance(application, dict)
                    else application.get("effect_id") or application.get("id")
                )
                if not effect_id:
                    continue
                entry = CombatCatalogIntegrator.get_effect_catalog_entry(str(effect_id))
                if not entry:
                    continue
                source_id = (
                    getattr(application, "source_id", None)
                    if not isinstance(application, dict)
                    else application.get("source_id") or source.char_id
                )
                source_id = str(source_id or source.char_id)
                active_from = actor.meta.exchange_counter + (1 if ctx.flags.meta.action_mode == "exchange" else 0)
                active_effect = ActiveEffectDTO(
                    uid=str(effect_id),
                    effect_id=str(effect_id),
                    source_id=source_id,
                    active_from_exchange=active_from,
                    expire_at_exchange=active_from + int(entry.technical.duration or 0),
                )

            if any(existing.uid == active_effect.uid for existing in actor.statuses.effects):
                continue

            entry = CombatCatalogIntegrator.get_effect_catalog_entry(active_effect.effect_id)
            if entry and entry.technical.modifier_applications:
                applied = ModifierApplicationService.apply(
                    applications=entry.technical.modifier_applications,
                    owner="effect",
                    owner_uid=active_effect.uid,
                    owner_id=active_effect.effect_id,
                    source=source,
                    target=actor,
                )
                active_effect.modified_keys = sorted(set(active_effect.modified_keys) | applied.modified_keys)
                active_effect.modified_sources = applied.modified_sources
            actor.statuses.effects.append(active_effect)

    def _apply_staged_resource_applications(
        self, source: ActorSnapshot, target: ActorSnapshot | None, result: InteractionResultDTO
    ) -> None:
        actors = {str(source.char_id): source}
        if target:
            actors[str(target.char_id)] = target

        for application in result.resource_applications:
            actor_id = (
                getattr(application, "actor_id", None)
                if not isinstance(application, dict)
                else application.get("actor_id")
            )
            actor = actors.get(str(actor_id)) if actor_id is not None else None
            if not actor:
                continue
            resource = (
                getattr(application, "resource", None)
                if not isinstance(application, dict)
                else application.get("resource")
            )
            value = (
                getattr(application, "value", None) if not isinstance(application, dict) else application.get("value")
            )
            reason = (
                getattr(application, "reason", "staged")
                if not isinstance(application, dict)
                else application.get("reason", "staged")
            )
            if not isinstance(resource, str) or not isinstance(value, str):
                continue
            applied = self._apply_resource_delta(actor, resource, [value])
            self._record_resource_fact(
                result,
                actor=actor,
                owner=(
                    getattr(application, "owner", "other")
                    if not isinstance(application, dict)
                    else application.get("owner", "other")
                ),
                resource=resource,
                reason=str(reason),
                applied=applied,
                source_effect_id=(
                    getattr(application, "source_effect_id", None)
                    if not isinstance(application, dict)
                    else application.get("source_effect_id")
                ),
                source_trigger_id=(
                    getattr(application, "source_trigger_id", None)
                    if not isinstance(application, dict)
                    else application.get("source_trigger_id")
                ),
                tags=(
                    getattr(application, "tags", [])
                    if not isinstance(application, dict)
                    else application.get("tags", [])
                ),
            )

    def _consume_shield_opening_between(
        self, source: ActorSnapshot, target: ActorSnapshot, result: InteractionResultDTO
    ) -> None:
        self._consume_actor_shield_opening(source, opposing_actor=target, result=result)
        self._consume_actor_shield_opening(target, opposing_actor=source, result=result)

    @staticmethod
    def _consume_actor_shield_opening(
        actor: ActorSnapshot, *, opposing_actor: ActorSnapshot, result: InteractionResultDTO
    ) -> None:
        kept_effects = []
        owner = "source" if str(actor.char_id) == str(result.source_id) else "target"
        for effect in actor.statuses.effects:
            if effect.effect_id == "shield_opening" and str(effect.source_id) == str(opposing_actor.char_id):
                result.status_removals.append(
                    CombatStatusRemovalDTO(
                        actor_id=actor.char_id,
                        effect_uid=effect.uid,
                        effect_id=effect.effect_id,
                        source_effect_id=effect.effect_id,
                        tags=["shield", "opening", "source_exchange"],
                    )
                )
                result.effect_facts.append(
                    CombatEffectFactDTO(
                        actor_id=actor.char_id,
                        owner=owner,  # type: ignore
                        effect_id=effect.effect_id,
                        action="expire",
                        source_effect_id=effect.effect_id,
                        tags=["shield", "opening", "source_exchange"],
                    )
                )
                continue
            kept_effects.append(effect)
        actor.statuses.effects = kept_effects

    def _apply_target_changes(
        self, ctx: PipelineContextDTO, source: ActorSnapshot, target: ActorSnapshot, result: InteractionResultDTO
    ) -> None:
        """Apply target-side damage, death checks, and defensive token awards."""
        damage_applied: tuple[int, int, int, int] | None = None

        # A. Damage Final
        if ctx.flags.mechanics.apply_damage:
            hp_sources = []
            if result.damage_final > 0:
                hp_sources.append(f"-{result.damage_final}")

            # Apply
            if hp_sources:
                damage_applied = self._apply_resource_delta(target, "hp", hp_sources)
                self._record_resource_fact(
                    result,
                    actor=target,
                    owner="target",
                    resource="hp",
                    reason="damage",
                    applied=damage_applied,
                )
                self._apply_damage_dealt_token_progress(
                    result,
                    actor=source,
                    owner="source",
                    applied=damage_applied,
                    token_bucket=result.tokens_awarded_attacker,
                )

        # B. Death Check
        if ctx.flags.mechanics.check_death and target.meta.hp <= 0:
            target.meta.is_dead = True
            result.death_facts.append(CombatDeathFactDTO(actor_id=target.char_id, owner="target", reason="damage"))

            # Log Death Event
            result.events.append(
                CombatEventDTO(
                    type="DEATH",
                    source_id=target.char_id,
                    target_id=target.char_id,
                    value=0,
                )
            )

        # C. Tokens Awarded
        if result.tokens_awarded_defender:
            for token, amount in result.tokens_awarded_defender.items():
                if self._token_award_already_materialized(
                    result,
                    actor_id=target.char_id,
                    owner="target",
                    token=token,
                ):
                    continue
                before = target.meta.tokens.get(token, 0)
                target.meta.tokens[token] = target.meta.tokens.get(token, 0) + amount
                result.token_facts.append(
                    CombatTokenFactDTO(
                        actor_id=target.char_id,
                        owner="target",
                        token=token,
                        amount=amount,
                        before=before,
                        after=target.meta.tokens[token],
                        reason="award",
                    )
                )

        self._apply_damage_taken_token_progress(
            result,
            actor=target,
            owner="target",
            applied=damage_applied,
            token_bucket=result.tokens_awarded_defender,
        )

    def _apply_resource_delta(
        self, actor: ActorSnapshot, resource: str, sources: list[str]
    ) -> tuple[int, int, int, int] | None:
        """Evaluate and clamp a resource delta against the actor snapshot."""
        before, max_value = self._resource_state(actor, resource)
        if before is None or max_value is None:
            return None

        # 1. Calculate Delta
        delta, _ = StatsWaterfallCalculator.evaluate_sources(sources, base_value=0.0)
        delta_int = int(delta)

        if delta_int == 0:
            return None

        # 2. Apply & Clamp
        if resource == "hp":
            new_val = actor.meta.hp + delta_int
            actor.meta.hp = max(0, min(new_val, actor.meta.max_hp))
        elif resource == "en":
            new_val = actor.meta.en + delta_int
            actor.meta.en = max(0, min(new_val, actor.meta.max_en))
        elif resource == "stamina":
            new_val = actor.meta.stamina + delta_int
            actor.meta.stamina = max(0, min(new_val, actor.meta.max_stamina))
        else:
            return None

        after, _max_value = self._resource_state(actor, resource)
        if after is None:
            return None
        return before, after, max_value, after - before

    @staticmethod
    def _resource_state(actor: ActorSnapshot, resource: str) -> tuple[int | None, int | None]:
        if resource == "hp":
            return actor.meta.hp, actor.meta.max_hp
        if resource == "en":
            return actor.meta.en, actor.meta.max_en
        if resource == "stamina":
            return actor.meta.stamina, actor.meta.max_stamina
        return None, None

    @staticmethod
    def _resource_change_reason(changes: list[tuple[str, str]]) -> str:
        reasons = [key for key, _value in changes]
        if len(reasons) == 1:
            return reasons[0]
        if reasons and all(reason == reasons[0] for reason in reasons):
            return reasons[0]
        return "mixed"

    @staticmethod
    def _record_resource_fact(
        result: InteractionResultDTO,
        *,
        actor: ActorSnapshot,
        owner: Literal["source", "target", "self", "other"],
        resource: str,
        reason: str,
        applied: tuple[int, int, int, int] | None,
        source_effect_id: str | None = None,
        source_trigger_id: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        if applied is None:
            return
        before, after, max_value, delta = applied
        result.resource_facts.append(
            CombatResourceFactDTO(
                actor_id=actor.char_id,
                owner=owner,
                resource=resource,
                reason=reason,
                delta=delta,
                before=before,
                after=after,
                max=max_value,
                source_effect_id=source_effect_id,
                source_trigger_id=source_trigger_id,
                tags=tags or [],
            )
        )

    def _apply_damage_taken_token_progress(
        self,
        result: InteractionResultDTO,
        *,
        actor: ActorSnapshot,
        owner: Literal["source", "target", "self", "other"],
        applied: tuple[int, int, int, int] | None,
        token_bucket: dict[str, int],
    ) -> None:
        self._apply_damage_token_progress(
            result,
            actor=actor,
            owner=owner,
            applied=applied,
            token_bucket=token_bucket,
            token=BLOOD_MARKER,
            threshold=BLOOD_TOKEN_DAMAGE_STEP,
            reason="damage_taken",
            skip_dead_recipient=True,
        )

    def _apply_damage_dealt_token_progress(
        self,
        result: InteractionResultDTO,
        *,
        actor: ActorSnapshot,
        owner: Literal["source", "target", "self", "other"],
        applied: tuple[int, int, int, int] | None,
        token_bucket: dict[str, int],
    ) -> None:
        self._apply_damage_token_progress(
            result,
            actor=actor,
            owner=owner,
            applied=applied,
            token_bucket=token_bucket,
            token=PRESSURE_MARKER,
            threshold=PRESSURE_TOKEN_DAMAGE_STEP,
            reason="damage_dealt",
            skip_dead_recipient=False,
        )

    @staticmethod
    def _apply_damage_token_progress(
        result: InteractionResultDTO,
        *,
        actor: ActorSnapshot,
        owner: Literal["source", "target", "self", "other"],
        applied: tuple[int, int, int, int] | None,
        token_bucket: dict[str, int],
        token: str,
        threshold: int,
        reason: str,
        skip_dead_recipient: bool,
    ) -> None:
        if applied is None:
            return

        before_hp, after_hp, _max_hp, delta = applied
        if delta >= 0 or (skip_dead_recipient and after_hp <= 0):
            return

        hp_lost = max(0, before_hp - after_hp)
        if hp_lost <= 0:
            return

        old_progress = MechanicsService._token_progress_value(actor, token)
        new_progress = old_progress + hp_lost
        token_gain = new_progress // threshold
        actor.meta.token_progress[token] = new_progress % threshold

        if token_gain <= 0:
            return

        before_tokens = actor.meta.tokens.get(token, 0)
        after_tokens = before_tokens + token_gain
        actor.meta.tokens[token] = after_tokens
        token_bucket[token] = token_bucket.get(token, 0) + token_gain
        result.token_facts.append(
            CombatTokenFactDTO(
                actor_id=actor.char_id,
                owner=owner,
                token=token,
                amount=token_gain,
                before=before_tokens,
                after=after_tokens,
                reason=reason,
                tags=[reason],
            )
        )

    @staticmethod
    def _token_progress_value(actor: ActorSnapshot, token: str) -> int:
        try:
            return max(0, int(actor.meta.token_progress.get(token, 0)))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _token_award_already_materialized(
        result: InteractionResultDTO,
        *,
        actor_id: str,
        owner: Literal["source", "target"],
        token: str,
    ) -> bool:
        progress_reasons = {"damage_taken", "damage_dealt"}
        return any(
            fact.actor_id == str(actor_id)
            and fact.owner == owner
            and fact.token == token
            and fact.reason in progress_reasons
            for fact in result.token_facts
        )

    def _grant_exchange_gift_token(
        self,
        ctx: PipelineContextDTO,
        actor: ActorSnapshot,
        result: InteractionResultDTO,
    ) -> None:
        if not ctx.flags.meta.grant_exchange_gift:
            return
        if ctx.flags.meta.action_mode != "exchange":
            return
        if ctx.flags.meta.source_type != "main_hand":
            return
        if result.is_counter:
            return

        before = actor.meta.tokens.get(GIFT_MARKER, 0)
        after = before + GIFT_TOKEN_PER_EXCHANGE
        actor.meta.tokens[GIFT_MARKER] = after
        result.tokens_awarded_attacker[GIFT_MARKER] = (
            result.tokens_awarded_attacker.get(GIFT_MARKER, 0) + GIFT_TOKEN_PER_EXCHANGE
        )
        result.token_facts.append(
            CombatTokenFactDTO(
                actor_id=actor.char_id,
                owner="source",
                token=GIFT_MARKER,
                amount=GIFT_TOKEN_PER_EXCHANGE,
                before=before,
                after=after,
                reason="exchange",
                tags=["exchange"],
            )
        )

    def _apply_token_delta(
        self,
        result: InteractionResultDTO,
        *,
        actor: ActorSnapshot,
        owner: Literal["source", "target", "self", "other"],
        token: str,
        sources: list[str],
        reason: str,
    ) -> None:
        delta, _ = StatsWaterfallCalculator.evaluate_sources(sources, base_value=0.0)
        delta_int = int(delta)
        if delta_int == 0:
            return

        before = actor.meta.tokens.get(token, 0)
        after = max(0, before + delta_int)
        actor.meta.tokens[token] = after
        result.token_facts.append(
            CombatTokenFactDTO(
                actor_id=actor.char_id,
                owner=owner,
                token=token,
                amount=after - before,
                before=before,
                after=after,
                reason=reason,
                tags=[reason],
            )
        )

    def _register_xp_events(
        self,
        ctx: PipelineContextDTO,
        source: ActorSnapshot,
        target: ActorSnapshot | None,
        result: InteractionResultDTO,
    ) -> None:
        """Record combat outcome XP into actor-local runtime buffers."""
        if not ctx.flags.mechanics.grant_xp:
            return

        source_prefix = "off_hand" if result.hand == "off_hand" else "main_hand"

        # 1. Generic Actions
        if result.is_hit:
            self._inc_xp(source, f"{source_prefix}_hit")
        elif result.is_miss:
            self._inc_xp(source, f"{source_prefix}_miss")

        if result.is_crit:
            self._inc_xp(source, f"{source_prefix}_crit")

        # 2. Target Reactions
        if target:
            if result.is_dodged:
                self._inc_xp(target, "defense_dodge")
            if result.is_parried:
                self._inc_xp(target, "defense_parry")
            if result.is_blocked:
                self._inc_xp(target, "defense_block")
            if self._uses_body_armor_for_xp(target, result):
                self._inc_xp(target, "defense_armor")

            # 3. Kill
            if target.meta.is_dead:
                self._inc_xp(source, "kill_generic")

    def _inc_xp(self, actor: ActorSnapshot, key: str, amount: float = 1.0) -> None:
        actor.xp_buffer[key] = actor.xp_buffer.get(key, 0) + amount

    @staticmethod
    def _uses_body_armor_for_xp(target: ActorSnapshot, result: InteractionResultDTO) -> bool:
        if not result.is_hit or result.is_dodged or result.is_parried:
            return False
        if not target.loadout.layout.get("body"):
            return False
        return result.damage_raw > 0 or result.damage_mitigated > 0 or result.damage_final > 0

    def _log_effect_tick(
        self, ctx: PipelineContextDTO, actor: ActorSnapshot, effect_id: str, value: int, resource: str
    ) -> None:
        """Append structured combat facts/events for one periodic effect tick."""
        ctx.result.effect_facts.append(
            CombatEffectFactDTO(
                actor_id=actor.char_id,
                owner="self",
                effect_id=effect_id,
                action="tick",
                value=value,
                resource=resource,
            )
        )

        # Создаем событие TICK
        event = CombatEventDTO(
            type="TICK",
            source_id=actor.char_id,  # Тот, на ком эффект
            target_id=actor.char_id,
            action_id=effect_id,
            value=value,
            resource=resource,
        )
        ctx.result.events.append(event)

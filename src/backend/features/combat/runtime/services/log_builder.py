from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.combat.integrations import CombatCatalogIntegrator

if TYPE_CHECKING:
    from src.backend.features.combat.dto.action import CombatActionDTO
    from src.backend.features.combat.dto.pipeline import CombatEventDTO, InteractionResultDTO
    from src.backend.features.combat.dto.session import BattleContext


class CombatLogBuilder:
    """Builds player-facing combat log entries from resolved combat facts."""

    @classmethod
    def build_result_entries(
        cls,
        *,
        ctx: BattleContext,
        result: InteractionResultDTO,
        action: CombatActionDTO,
        wave: int,
        timestamp: float,
    ) -> list[dict[str, Any]]:
        global_turn = ctx.meta.step_counter + 1
        common_tags = ["runtime", action.action_type, f"wave:{wave}", f"turn:{global_turn}"]
        if action.is_forced:
            common_tags.append("forced")

        entries = [
            cls._build_summary_entry(
                ctx=ctx,
                result=result,
                timestamp=timestamp,
                tags=common_tags,
                action=action,
                global_turn=global_turn,
            )
        ]
        for event in result.events:
            entries.append(
                cls._build_event_entry(
                    ctx=ctx,
                    event=event,
                    result=result,
                    action=action,
                    timestamp=timestamp,
                    tags=common_tags,
                    global_turn=global_turn,
                )
            )
        for index, entry in enumerate(entries):
            entry["id"] = f"{global_turn}:{wave}:{index}"
        return entries

    @classmethod
    def _build_summary_entry(
        cls,
        *,
        ctx: BattleContext,
        result: InteractionResultDTO,
        timestamp: float,
        tags: list[str],
        action: CombatActionDTO,
        global_turn: int,
    ) -> dict[str, Any]:
        source_name = cls._actor_name(ctx, result.source_id)
        target_name = cls._actor_name(ctx, result.target_id)
        outcome = cls._result_outcome(result)
        hp_change = cls._resource_change(ctx, actor_id=result.target_id, resource="hp", delta=cls._result_hp_delta(result))
        action_id = cls._action_id(action)

        entry = {
            "type": "RESULT",
            "kind": "result",
            "text": cls._summary_text(
                result,
                source_name=source_name,
                target_name=target_name,
                outcome=outcome,
                action=action,
                action_id=action_id,
                global_turn=global_turn,
                hp_change=hp_change,
            ),
            "timestamp": timestamp,
            "tags": [*tags, f"outcome:{outcome}"],
            "global_turn": global_turn,
            "action_mode": action.action_type,
            "action_id": action_id,
            "source_id": result.source_id,
            "target_id": result.target_id,
            "source_name": source_name,
            "target_name": target_name,
            "outcome": outcome,
            "hand": result.hand,
            "damage_final": result.damage_final,
            "healing_final": result.healing_final,
            "reflected_damage": result.reflected_damage,
            "lifesteal_amount": result.lifesteal_amount,
            "crit_mult": result.crit_mult,
            "is_crit": result.is_crit,
            "is_counter": result.is_counter,
            "skip_reason": result.skip_reason,
            "tokens_awarded_attacker": dict(result.tokens_awarded_attacker),
            "tokens_awarded_defender": dict(result.tokens_awarded_defender),
            "applied_effects": list(result.applied_effects),
            "chain_events": result.chain_events.model_dump(mode="json"),
        }
        entry.update(cls._catalog_fields(action_id=action_id, event_name=outcome))
        entry.update(
            cls._frontend_contract_fields(
                ctx=ctx,
                result=result,
                action=action,
                action_id=action_id,
                event_name=outcome,
                source_id=result.source_id,
                target_id=result.target_id,
                resources=[hp_change] if hp_change else [],
                entry=entry,
            )
        )
        if hp_change:
            entry["target_hp_before"] = hp_change["before"]
            entry["target_hp_after"] = hp_change["after"]
            entry["target_hp_max"] = hp_change["max"]
            entry["resources"] = [hp_change]
        return entry

    @classmethod
    def _build_event_entry(
        cls,
        *,
        ctx: BattleContext,
        event: CombatEventDTO,
        result: InteractionResultDTO,
        action: CombatActionDTO,
        timestamp: float,
        tags: list[str],
        global_turn: int,
    ) -> dict[str, Any]:
        entry = event.model_dump(mode="json")
        source_name = cls._actor_name(ctx, event.source_id)
        target_name = cls._actor_name(ctx, event.target_id)
        action_id = entry.get("action_id") or cls._action_id(action)
        resource_change = cls._event_resource_change(ctx, entry)
        event_name = cls._event_template_name(str(entry.get("type") or ""))
        entry["timestamp"] = timestamp
        entry["kind"] = event_name
        entry["tags"] = [*entry.get("tags", []), *tags]
        entry["global_turn"] = global_turn
        entry["action_mode"] = action.action_type
        entry["action_id"] = action_id
        entry["source_name"] = source_name
        entry["target_name"] = target_name
        entry["outcome"] = cls._result_outcome(result)
        entry.update(cls._catalog_fields(action_id=action_id, event_name=event_name))
        entry.update(
            cls._frontend_contract_fields(
                ctx=ctx,
                result=result,
                action=action,
                action_id=action_id,
                event_name=event_name,
                source_id=event.source_id,
                target_id=event.target_id,
                resources=[resource_change] if resource_change else [],
                entry=entry,
            )
        )
        if resource_change:
            entry["resource_before"] = resource_change["before"]
            entry["resource_after"] = resource_change["after"]
            entry["resource_max"] = resource_change["max"]
            entry["resources"] = [resource_change]
        entry["text"] = cls._event_text(
            entry,
            source_name=source_name,
            target_name=target_name,
            resource_change=resource_change,
        )
        return entry

    @classmethod
    def _summary_text(
        cls,
        result: InteractionResultDTO,
        *,
        source_name: str,
        target_name: str,
        outcome: str,
        action: CombatActionDTO,
        action_id: str | None,
        global_turn: int,
        hp_change: dict[str, int | str] | None,
    ) -> str:
        verb = cls._summary_verb(action, action_id, source_name=source_name, target_name=target_name)
        hp_suffix = cls._hp_suffix(hp_change)
        feint_text = cls._feint_summary_text(
            result,
            action=action,
            outcome=outcome,
            source_name=source_name,
            target_name=target_name,
        )
        templated = cls._templated_action_text(
            action_id=action_id,
            event_name=outcome,
            source_name=source_name,
            target_name=target_name,
        )
        if result.skip_reason:
            return f"{source_name} не выполняет действие: {result.skip_reason}."
        if feint_text:
            return cls._sentence(feint_text, hp_suffix)
        if templated:
            return cls._sentence(templated, hp_suffix)
        if result.healing_final > 0:
            return f"{verb}: +{result.healing_final} hp{hp_suffix}."
        if result.is_miss:
            return f"{verb}: промах."
        if result.is_dodged:
            return f"{verb}: {target_name} уклоняется."
        if result.is_parried:
            return f"{verb}: {target_name} парирует."
        if result.is_blocked:
            return f"{verb}: {target_name} блокирует."
        if result.is_hit:
            crit = " критический" if result.is_crit else ""
            return f"{verb}:{crit} удар, -{result.damage_final} hp{hp_suffix}."
        if result.applied_effects:
            return f"{verb}: эффект применен."
        return f"{verb}: {outcome}."

    @staticmethod
    def _event_text(
        entry: dict[str, Any],
        *,
        source_name: str,
        target_name: str,
        resource_change: dict[str, int | str] | None,
    ) -> str:
        event_type = str(entry.get("type") or "RESULT")
        value = entry.get("value")
        resource = entry.get("resource")
        action_id = entry.get("action_id")
        suffix = CombatLogBuilder._value_suffix(value, resource, resource_change)
        event_name = CombatLogBuilder._event_template_name(event_type)
        templated = CombatLogBuilder._templated_action_text(
            action_id=str(action_id) if action_id else None,
            event_name=event_name,
            source_name=source_name,
            target_name=target_name,
            values={
                "damage": value if resource == "hp" else 0,
                "healing": value if event_type == "HEAL" else 0,
                "resource": str(resource) if resource else "",
                "outcome": event_name,
            },
        )
        if templated:
            return CombatLogBuilder._sentence(templated, suffix)

        if event_type == "CAST":
            action = f" {action_id}" if action_id else ""
            return f"{source_name} использует{action} на {target_name}."
        if event_type == "HIT":
            reflect = " отраженным ударом" if "REFLECT" in entry.get("tags", []) else ""
            return f"{source_name}{reflect} наносит {target_name}{suffix}."
        if event_type == "HEAL":
            return f"{source_name} лечит {target_name}{suffix}."
        if event_type == "MISS":
            return f"{source_name} промахивается по {target_name}."
        if event_type == "DODGE":
            return f"{target_name} уклоняется от атаки {source_name}."
        if event_type == "PARRY":
            return f"{target_name} парирует атаку {source_name}."
        if event_type == "BLOCK":
            return f"{target_name} блокирует атаку {source_name}."
        if event_type == "TICK":
            action = f" от {action_id}" if action_id else ""
            return f"{target_name} получает{suffix}{action}."
        if event_type == "DEATH":
            return f"{target_name} погибает."
        if event_type == "COST":
            return f"{source_name} тратит{suffix}."
        if event_type == "APPLY_EFFECT":
            action = f" {action_id}" if action_id else " эффект"
            return f"{source_name} накладывает{action} на {target_name}."
        return f"{event_type}: {source_name} -> {target_name}{suffix}."

    @staticmethod
    def _value_suffix(value: Any, resource: Any, resource_change: dict[str, int | str] | None = None) -> str:
        if value is None:
            return ""
        suffix = f" {value}"
        if resource:
            suffix += f" {resource}"
        if resource_change:
            label = str(resource_change["resource"]).upper()
            suffix += f" ({label} {resource_change['after']}/{resource_change['max']})"
        return suffix

    @staticmethod
    def _sentence(text: str, suffix: str = "") -> str:
        base = text.rstrip(".")
        return f"{base}{suffix}."

    @staticmethod
    def _event_template_name(event_type: str) -> str:
        return {
            "CAST": "use",
            "HIT": "hit",
            "HEAL": "hit",
            "MISS": "miss",
            "DODGE": "dodge",
            "PARRY": "parry",
            "BLOCK": "block",
            "APPLY_EFFECT": "apply_effect",
            "TICK": "hit",
            "DEATH": "expire_effect",
        }.get(event_type, event_type.lower())

    @staticmethod
    def _catalog_fields(*, action_id: str | None, event_name: str) -> dict[str, Any]:
        if not action_id:
            return {}

        if CombatCatalogIntegrator.get_catalog_entry_by_key(f"combat.feint.{action_id}") is not None:
            return {
                "catalog": "combat_entries",
                "catalog_key": f"combat.feint.{action_id}",
                "catalog_event": event_name,
                "catalog_taxonomy": "humanoid",
                "catalog_tooltip": "description",
            }

        if CombatCatalogIntegrator.get_effect(action_id) is not None:
            return {
                "catalog": "effects",
                "catalog_key": action_id,
                "catalog_event": event_name,
                "catalog_taxonomy": "humanoid",
                "catalog_tooltip": "description",
            }

        trigger = CombatCatalogIntegrator.get_trigger_rule(action_id)
        if trigger is not None:
            return {
                "catalog": "triggers",
                "catalog_key": action_id,
                "catalog_event": event_name,
                "catalog_taxonomy": "humanoid",
                "catalog_tooltip": "description",
            }

        return {}

    @classmethod
    def _frontend_contract_fields(
        cls,
        *,
        ctx: BattleContext,
        result: InteractionResultDTO,
        action: CombatActionDTO,
        action_id: str | None,
        event_name: str,
        source_id: int | str | None,
        target_id: int | str | None,
        resources: list[dict[str, int | str] | None],
        entry: dict[str, Any],
    ) -> dict[str, Any]:
        clean_resources = [resource for resource in resources if resource]
        catalog = cls._catalog_fields(action_id=action_id, event_name=event_name)
        return {
            "severity": cls._severity(result, event_name),
            "source": cls._actor_ref(ctx, source_id),
            "target": cls._actor_ref(ctx, target_id),
            "action": {
                "mode": action.action_type,
                "id": action_id,
                "catalog": catalog.get("catalog"),
                "catalog_key": catalog.get("catalog_key"),
                "event": catalog.get("catalog_event") or event_name,
                "taxonomy": catalog.get("catalog_taxonomy") or "humanoid",
            },
            "template": {
                "key": catalog.get("catalog_key") or cls._template_key(action_id=action_id, event_name=event_name),
                "variant": 0,
            },
            "resources": clean_resources,
            "badges": cls._badges(entry=entry, resources=clean_resources),
            "effects": cls._effects(result),
            "flags": {
                "crit": result.is_crit,
                "dodged": result.is_dodged,
                "parried": result.is_parried,
                "blocked": result.is_blocked,
                "missed": result.is_miss,
                "reflected": "REFLECT" in entry.get("tags", []),
                "counter": result.is_counter,
            },
        }

    @staticmethod
    def _actor_ref(ctx: BattleContext, actor_id: int | str | None) -> dict[str, Any] | None:
        if actor_id is None:
            return None
        actor = ctx.get_actor(actor_id)
        if actor is None:
            return {"id": str(actor_id), "name": f"#{actor_id}", "team": None, "actor_type": None}
        return {
            "id": str(actor_id),
            "name": actor.meta.name or f"#{actor_id}",
            "team": actor.meta.team,
            "actor_type": actor.meta.type,
        }

    @staticmethod
    def _template_key(*, action_id: str | None, event_name: str) -> str | None:
        if not action_id:
            return None
        return f"combat.{action_id}.{event_name}"

    @staticmethod
    def _badges(*, entry: dict[str, Any], resources: list[dict[str, int | str]]) -> list[dict[str, Any]]:
        badges: list[dict[str, Any]] = []
        for resource in resources:
            delta = int(resource.get("delta") or 0)
            kind = "heal" if delta > 0 else "damage" if delta < 0 else "resource"
            badges.append(
                {
                    "kind": kind,
                    "value": abs(delta),
                    "resource": resource.get("resource"),
                    "direction": resource.get("direction"),
                }
            )
        if entry.get("type") == "COST" and entry.get("value"):
            badges.append({"kind": "cost", "value": entry.get("value"), "resource": entry.get("resource")})
        return badges

    @staticmethod
    def _effects(result: InteractionResultDTO) -> list[dict[str, Any]]:
        effects: list[dict[str, Any]] = []
        for effect in result.applied_effects:
            if isinstance(effect, dict):
                effect_id = effect.get("id") or effect.get("effect_id")
                effects.append({"id": effect_id, "data": effect})
        return effects

    @staticmethod
    def _severity(result: InteractionResultDTO, event_name: str) -> str:
        if event_name == "death":
            return "death"
        if result.is_crit or event_name == "crit":
            return "good"
        if result.is_miss or result.is_dodged or result.is_parried or result.is_blocked:
            return "warning"
        return "normal"

    @classmethod
    def _templated_action_text(
        cls,
        *,
        action_id: str | None,
        event_name: str,
        source_name: str,
        target_name: str,
        values: dict[str, Any] | None = None,
    ) -> str | None:
        if not action_id:
            return None

        feint_entry = CombatCatalogIntegrator.get_catalog_entry_by_key(f"combat.feint.{action_id}")
        if feint_entry is not None:
            variant = feint_entry.descriptive.variants.get("humanoid")
            templates = getattr(variant.event_texts, event_name, []) if variant else []
            if templates:
                return cls._format_template(
                    templates[0],
                    source_name=source_name,
                    target_name=target_name,
                    label=variant.display_name if variant else action_id,
                    label_key="feint",
                    values=values,
                )

        effect = CombatCatalogIntegrator.get_effect(action_id)
        if effect is not None:
            template = cls._effect_template(event_name)
            return cls._format_template(
                template,
                source_name=source_name,
                target_name=target_name,
                label=effect.name_ru,
                label_key="effect",
                values=values,
            )

        return None

    @classmethod
    def _feint_summary_text(
        cls,
        result: InteractionResultDTO,
        *,
        action: CombatActionDTO,
        outcome: str,
        source_name: str,
        target_name: str,
    ) -> str | None:
        feint_id = cls._feint_id(action)
        if not feint_id:
            return None

        feint_entry = CombatCatalogIntegrator.get_catalog_entry_by_key(f"combat.feint.{feint_id}")
        if feint_entry is None:
            return None

        variant = (
            feint_entry.descriptive.variants.get(feint_entry.descriptive.default_taxonomy)
            or feint_entry.descriptive.variants.get("humanoid")
        )
        if variant is None:
            return None

        use_templates = variant.event_texts.use
        outcome_templates = getattr(variant.event_texts, outcome, [])
        if not use_templates and not outcome_templates:
            return None

        values = {
            "source": source_name,
            "target": target_name,
            "feint": variant.display_name,
            "damage": result.damage_final,
            "healing": result.healing_final,
            "effect": cls._first_effect_label(result),
            "resource": "hp" if result.damage_final or result.healing_final else "",
            "outcome": outcome,
        }

        use_text = cls._format_values(use_templates[0], values) if use_templates else ""
        outcome_text = cls._format_values(outcome_templates[0], values) if outcome_templates else ""
        if use_text and outcome_text:
            return f"{use_text}, {outcome_text}"
        return use_text or outcome_text

    @staticmethod
    def _format_values(template: str, values: dict[str, Any]) -> str:
        return template.format(**values)

    @staticmethod
    def _first_effect_label(result: InteractionResultDTO) -> str:
        for effect in result.applied_effects:
            if isinstance(effect, dict):
                return str(effect.get("name") or effect.get("id") or effect.get("effect_id") or "")
        return ""

    @staticmethod
    def _effect_template(event_name: str) -> str:
        return {
            "apply_effect": "{source} накладывает {effect} на {target}",
            "expire_effect": "{effect} на {target} заканчивается",
            "hit": "{effect} действует на {target}",
            "miss": "{effect} не закрепляется на {target}",
        }.get(event_name, "{source} применяет {effect} на {target}")

    @staticmethod
    def _format_template(
        template: str,
        *,
        source_name: str,
        target_name: str,
        label: str,
        label_key: str,
        values: dict[str, Any] | None = None,
    ) -> str:
        template_values = {
            "source": source_name,
            "target": target_name,
            "ability": label,
            "feint": label,
            "effect": label,
            "trigger": label,
            "damage": 0,
            "healing": 0,
            "resource": "",
            "outcome": "",
            label_key: label,
        }
        if values:
            template_values.update(values)
        return template.format(**template_values)

    @staticmethod
    def _summary_verb(
        action: CombatActionDTO,
        action_id: str | None,
        *,
        source_name: str,
        target_name: str,
    ) -> str:
        action_text = f" {action_id}" if action_id else ""
        if action.action_type == "exchange":
            return f"{source_name} разменялся с {target_name}"
        if action.action_type == "instant":
            return f"{source_name} применяет{action_text} на {target_name}"
        if action.action_type == "item":
            return f"{source_name} использует{action_text} на {target_name}"
        return f"{source_name} действует"

    @staticmethod
    def _hp_suffix(change: dict[str, int | str] | None) -> str:
        if not change:
            return ""
        label = str(change["resource"]).upper()
        return f" ({label} {change['after']}/{change['max']})"

    @staticmethod
    def _action_id(action: CombatActionDTO) -> str | None:
        payload = action.move.payload
        for key in ("ability_id", "item_id", "feint_id"):
            value = getattr(payload, key, None)
            if value:
                return str(value)
        return None

    @staticmethod
    def _feint_id(action: CombatActionDTO) -> str | None:
        value = getattr(action.move.payload, "feint_id", None)
        return str(value) if value else None

    @staticmethod
    def _result_hp_delta(result: InteractionResultDTO) -> int:
        if result.damage_final > 0:
            return -result.damage_final
        if result.healing_final > 0:
            return result.healing_final
        return 0

    @classmethod
    def _event_resource_change(cls, ctx: BattleContext, entry: dict[str, Any]) -> dict[str, int | str] | None:
        resource = entry.get("resource")
        if resource not in {"hp", "en"}:
            return None
        value = entry.get("value")
        if not isinstance(value, int | float):
            return None
        event_type = str(entry.get("type") or "")
        if event_type in {"HIT", "COST"}:
            delta = -int(value)
        elif event_type in {"HEAL", "TICK"}:
            delta = int(value)
        else:
            return None
        return cls._resource_change(ctx, actor_id=entry.get("target_id"), resource=str(resource), delta=delta)

    @staticmethod
    def _resource_change(
        ctx: BattleContext, *, actor_id: int | str | None, resource: str, delta: int
    ) -> dict[str, int | str] | None:
        if delta == 0 or actor_id is None:
            return None
        actor = ctx.get_actor(actor_id)
        if actor is None:
            return None
        if resource == "hp":
            after = actor.meta.hp
            max_value = actor.meta.max_hp
        elif resource == "en":
            after = actor.meta.en
            max_value = actor.meta.max_en
        else:
            return None
        before = after - delta
        before = max(0, min(before, max_value))
        return {
            "actor_id": str(actor_id),
            "resource": resource,
            "before": before,
            "after": after,
            "max": max_value,
            "delta": delta,
            "direction": "gain" if delta > 0 else "loss",
        }

    @staticmethod
    def _actor_name(ctx: BattleContext, actor_id: int | str | None) -> str:
        if actor_id is None:
            return "NO_TARGET"
        actor = ctx.get_actor(actor_id)
        if actor is None:
            return f"#{actor_id}"
        return actor.meta.name or f"#{actor_id}"

    @staticmethod
    def _result_outcome(result: InteractionResultDTO) -> str:
        if result.skip_reason:
            return result.skip_reason.lower()
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
        if result.applied_effects:
            return "effect"
        return "none"

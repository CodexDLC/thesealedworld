from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.combat.integrations import CombatCatalogIntegrator

if TYPE_CHECKING:
    from src.backend.features.combat.dto.action import CombatActionDTO
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO
    from src.backend.features.combat.dto.session import BattleContext


class CombatLogBuilder:
    """Builds short player-facing combat log entries from resolved public facts."""

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
        outcome = cls._result_outcome(result)
        action_id = cls._action_id(action) or cls._result_action_id(result)
        is_area = cls._is_area_action(action)
        event_name = "area_result" if is_area else outcome
        catalog = cls._catalog_fields(action_type=action.action_type, action_id=action_id, event_name=event_name)
        source_id = result.source_id if result.source_id is not None else cls._first_event_source_id(result)
        target_id = result.target_id if result.target_id is not None else cls._first_event_target_id(result)
        source = cls._actor_ref(ctx, source_id)
        target = cls._actor_ref(ctx, target_id)
        targets = cls._target_refs(ctx, action=action, fallback_target_id=target_id)
        variables = cls._variables(result=result, source=source, target=target, targets_count=len(targets))
        cls._apply_catalog_variables(variables, catalog)
        public_result = cls._public_result(ctx, result)
        tags = ["runtime", action.action_type, f"wave:{wave}", f"turn:{global_turn}", f"outcome:{outcome}"]
        if action.is_forced:
            tags.append("forced")

        entry = {
            "id": f"{global_turn}:{wave}:0",
            "type": "LOG",
            "kind": cls._entry_kind(result, action_type=action.action_type, is_area=is_area, catalog=catalog),
            "text": cls._summary_text(
                result,
                source_name=str(variables["source"]),
                target_name=str(variables["target"]),
                outcome=event_name,
                action=action,
                action_id=action_id,
                catalog=catalog,
                targets_count=len(targets),
                exchange_id=cls._derive_exchange_id(ctx, action),
            ),
            "timestamp": timestamp,
            "tags": tags,
            "global_turn": global_turn,
            "wave": wave,
            "source": source,
            "target": target,
            "targets": targets,
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
                "event": catalog.get("catalog_event") or event_name,
                "taxonomy": catalog.get("catalog_taxonomy") or "humanoid",
                "variant": 0,
            },
            "variables": variables,
            "result": public_result,
            "presentation": {
                "player_visible": True,
                "severity": cls._severity(result, outcome),
                "render": "inline_result",
            },
            "outcome": outcome,
            # Backward-compatible surface fields used by the current frontend VM.
            "severity": cls._severity(result, outcome),
            "catalog": catalog.get("catalog"),
            "catalog_key": catalog.get("catalog_key"),
            "catalog_event": catalog.get("catalog_event") or event_name,
            "catalog_taxonomy": catalog.get("catalog_taxonomy") or "humanoid",
            "catalog_tooltip": catalog.get("catalog_tooltip"),
            "resources": public_result["resources"],
            "effects": public_result["effects"],
            "badges": [],
            "flags": cls._public_flags(result),
        }
        entries = [entry]
        for trigger_id in result.fired_triggers:
            if cls._should_merge_trigger(trigger_id):
                continue
            proc_entry = cls._build_trigger_proc_entry(
                ctx=ctx,
                result=result,
                trigger_id=trigger_id,
                outcome=outcome,
                timestamp=timestamp,
                tags=tags,
                global_turn=global_turn,
            )
            if proc_entry:
                proc_entry["id"] = f"{global_turn}:{wave}:{len(entries)}"
                entries.append(proc_entry)
        return entries

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
        catalog: dict[str, Any],
        targets_count: int,
        exchange_id: str | None = None,
    ) -> str:
        values = cls._template_values(result, source_name=source_name, target_name=target_name)
        values["targets_count"] = targets_count
        templated = cls._templated_action_text(
            action_type=action.action_type,
            action_id=action_id,
            event_name=outcome,
            source_name=source_name,
            target_name=target_name,
            values=values,
            catalog=catalog,
        )
        trigger_suffix = cls._trigger_suffix_text(
            result, outcome=outcome, source_name=source_name, target_name=target_name
        )
        if result.skip_reason:
            return cls._with_damage_sentence(templated, result) if templated else f"{source_name} не может действовать."
        if templated and trigger_suffix:
            return cls._with_damage_sentence(f"{templated}; {trigger_suffix}", result)
        if templated:
            return cls._with_damage_sentence(templated, result)
        exchange_text = cls._basic_exchange_summary_text(
            result,
            exchange_id=exchange_id,
            outcome=outcome,
            source_name=source_name,
            target_name=target_name,
        )
        if exchange_text and trigger_suffix:
            return cls._with_damage_sentence(f"{exchange_text}; {trigger_suffix}", result)
        if exchange_text:
            return cls._with_damage_sentence(exchange_text, result)
        return cls._fallback_text(
            result,
            action=action,
            action_id=action_id,
            outcome=outcome,
            source_name=source_name,
            target_name=target_name,
        )

    @classmethod
    def _fallback_text(
        cls,
        result: InteractionResultDTO,
        *,
        action: CombatActionDTO,
        action_id: str | None,
        outcome: str,
        source_name: str,
        target_name: str,
    ) -> str:
        verb = cls._summary_verb(action, action_id, source_name=source_name, target_name=target_name)
        if outcome == "death":
            return f"{target_name} падает и больше не держит строй."
        if outcome == "tick":
            effect = cls._first_effect_label(result) or "Эффект"
            return cls._with_damage_sentence(f"{effect} действует на {target_name}", result)
        if result.healing_final > 0:
            return f"{verb}, восстанавливая {result.healing_final} здоровья."
        if result.is_miss:
            return f"{verb}, но удар проходит мимо {target_name}."
        if result.is_dodged:
            return f"{verb}, но {target_name} уходит в последний миг."
        if result.is_parried:
            return f"{verb}, но {target_name} встречает удар и сбивает траекторию."
        if result.is_blocked:
            return f"{verb}, но защита {target_name} гасит удар."
        if result.is_hit:
            if result.is_crit:
                return f"{verb} и находит брешь, нанося {result.damage_final} урона."
            return f"{verb}, нанося {result.damage_final} урона."
        if result.applied_effects:
            effect = cls._first_effect_label(result) or "эффект"
            return f"{verb}; {target_name} получает {effect}."
        return f"{verb}: {outcome}."

    @staticmethod
    def _with_damage_sentence(text: str, result: InteractionResultDTO) -> str:
        base = text.rstrip(".")
        if result.damage_final > 0 and "урон" not in base and "урона" not in base:
            return f"{base}, получая {result.damage_final} урона."
        if result.healing_final > 0 and "здоров" not in base and "леч" not in base:
            return f"{base}, восстанавливая {result.healing_final} здоровья."
        return f"{base}."

    @staticmethod
    def _event_template_name(event_type: str) -> str:
        return {
            "CAST": "use",
            "HIT": "hit",
            "HEAL": "heal",
            "MISS": "miss",
            "DODGE": "dodge",
            "PARRY": "parry",
            "BLOCK": "block",
            "APPLY_EFFECT": "apply_effect",
            "TICK": "tick",
            "DEATH": "death",
            "CRIT": "crit",
        }.get(event_type, event_type.lower())

    @classmethod
    def _catalog_fields(cls, *, action_type: str, action_id: str | None, event_name: str) -> dict[str, Any]:
        if action_id:
            entry, key = cls._action_catalog_entry(action_type=action_type, action_id=action_id)
            if entry is not None:
                return {
                    "catalog": "combat_entries",
                    "catalog_key": key,
                    "catalog_event": event_name,
                    "catalog_taxonomy": "humanoid",
                    "catalog_tooltip": "description",
                    "catalog_entry": entry,
                    "resource_type": cls._catalog_resource_type(str(key)),
                }

        if (
            action_id
            and CombatCatalogIntegrator.get_feint_catalog_entry_by_key(f"combat.feint.{action_id}") is not None
        ):
            return {
                "catalog": "combat_entries",
                "catalog_key": f"combat.feint.{action_id}",
                "catalog_event": event_name,
                "catalog_taxonomy": "humanoid",
                "catalog_tooltip": "description",
                "resource_type": "feint",
            }

        if action_id and CombatCatalogIntegrator.get_effect(action_id) is not None:
            return {
                "catalog": "effects",
                "catalog_key": action_id,
                "catalog_event": event_name,
                "catalog_taxonomy": "humanoid",
                "catalog_tooltip": "description",
            }

        trigger_entry = CombatCatalogIntegrator.get_trigger_catalog_entry(action_id) if action_id else None
        if trigger_entry is not None:
            return {
                "catalog": "combat_entries",
                "catalog_key": trigger_entry.key,
                "catalog_event": event_name,
                "catalog_taxonomy": "humanoid",
                "catalog_tooltip": "description",
            }

        return {
            "catalog": "combat_entries",
            "catalog_key": "combat.exchange.basic",
            "catalog_event": event_name,
            "catalog_taxonomy": "humanoid",
            "catalog_tooltip": "description",
        }

    @classmethod
    def _public_result(cls, ctx: BattleContext, result: InteractionResultDTO) -> dict[str, list[dict[str, Any]]]:
        return {
            "resources": cls._public_resources(ctx, result),
            "tokens": cls._public_tokens(ctx, result),
            "effects": cls._public_effects(ctx, result),
        }

    @classmethod
    def _public_resources(cls, ctx: BattleContext, result: InteractionResultDTO) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        seen: set[tuple[str | None, str]] = set()
        deltas = cls._resource_deltas(result)
        for actor_id, resource, delta in deltas:
            key = (str(actor_id) if actor_id is not None else None, resource)
            if key in seen:
                continue
            seen.add(key)
            public = cls._public_resource(ctx, actor_id=actor_id, resource=resource, delta=delta)
            if public:
                resources.append(public)
        return resources

    @staticmethod
    def _resource_deltas(result: InteractionResultDTO) -> list[tuple[int | None, str, int]]:
        deltas: list[tuple[int | None, str, int]] = []
        if result.damage_final > 0:
            deltas.append((result.target_id, "hp", -result.damage_final))
        if result.healing_final > 0:
            deltas.append((result.target_id, "hp", result.healing_final))
        if result.reflected_damage > 0:
            deltas.append((result.source_id, "hp", -result.reflected_damage))
        if result.lifesteal_amount > 0:
            deltas.append((result.source_id, "hp", result.lifesteal_amount))
        for event in result.events:
            if event.resource not in {"hp", "en"} or event.value is None:
                continue
            value = int(event.value)
            if value < 0:
                deltas.append((event.target_id, event.resource, value))
                continue
            sign = 1 if event.type == "HEAL" else -1
            deltas.append((event.target_id, event.resource, sign * value))
        return deltas

    @staticmethod
    def _public_resource(
        ctx: BattleContext, *, actor_id: int | str | None, resource: str, delta: int
    ) -> dict[str, Any] | None:
        if actor_id is None:
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
        before = max(0, min(after - delta, max_value))
        label = f"{resource.upper()} {after}/{max_value}"
        return {
            "actor_id": str(actor_id),
            "resource": resource,
            "before": before,
            "after": after,
            "max": max_value,
            "delta": delta,
            "label": label,
        }

    @staticmethod
    def _public_tokens(ctx: BattleContext, result: InteractionResultDTO) -> list[dict[str, Any]]:
        tokens: list[dict[str, Any]] = []
        if result.source_id is not None:
            for token, amount in result.tokens_awarded_attacker.items():
                tokens.append(
                    {
                        "actor_id": str(result.source_id),
                        "owner": "source",
                        "token": token,
                        "amount": amount,
                        "icon": f"combat/tokens/{token}.svg",
                        "tooltip": f"+{amount} {token}",
                    }
                )
        if result.target_id is not None:
            for token, amount in result.tokens_awarded_defender.items():
                tokens.append(
                    {
                        "actor_id": str(result.target_id),
                        "owner": "target",
                        "token": token,
                        "amount": amount,
                        "icon": f"combat/tokens/{token}.svg",
                        "tooltip": f"+{amount} {token}",
                    }
                )
        return tokens

    @classmethod
    def _public_effects(cls, ctx: BattleContext, result: InteractionResultDTO) -> list[dict[str, Any]]:
        effects: list[dict[str, Any]] = []
        for effect in result.applied_effects:
            if not isinstance(effect, dict):
                continue
            effect_id = str(effect.get("id") or effect.get("effect_id") or "")
            if not effect_id:
                continue
            effect_config = CombatCatalogIntegrator.get_effect(effect_id)
            target_id = result.target_id
            duration = cls._effect_duration(effect, effect_config)
            label = getattr(effect_config, "name_ru", None) or effect_id
            effects.append(
                {
                    "actor_id": str(target_id) if target_id is not None else None,
                    "owner": "target",
                    "effect_id": effect_id,
                    "action": "apply",
                    "duration": duration,
                    "icon": f"combat/effects/{effect_id}.svg",
                    "tooltip": cls._effect_tooltip(label, duration),
                }
            )
        if cls._has_event(result, "DEATH") and result.target_id is not None:
            effects.append(
                {
                    "actor_id": str(result.target_id),
                    "owner": "target",
                    "effect_id": "death",
                    "action": "apply",
                    "duration": None,
                    "icon": "combat/effects/death.svg",
                    "tooltip": "Побежден",
                }
            )
        for event in result.events:
            if event.type != "APPLY_EFFECT" or not event.action_id:
                continue
            effect_id = str(event.action_id)
            if any(effect["effect_id"] == effect_id for effect in effects):
                continue
            effect_config = CombatCatalogIntegrator.get_effect(effect_id)
            duration = cls._effect_duration({}, effect_config)
            label = getattr(effect_config, "name_ru", None) or effect_id
            effects.append(
                {
                    "actor_id": str(event.target_id) if event.target_id is not None else None,
                    "owner": "target",
                    "effect_id": effect_id,
                    "action": "apply",
                    "duration": duration,
                    "icon": f"combat/effects/{effect_id}.svg",
                    "tooltip": cls._effect_tooltip(label, duration),
                }
            )
        return effects

    @staticmethod
    def _effect_duration(effect: dict[str, Any], effect_config: Any) -> int | None:
        raw = effect.get("duration") or effect.get("expires_at_exchange")
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None
        duration = getattr(effect_config, "duration", None)
        if duration is None:
            return None
        try:
            return int(duration)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _effect_tooltip(label: str, duration: int | None) -> str:
        if duration is None:
            return label
        if duration == 1:
            return f"{label}, 1 ход"
        return f"{label}, {duration} хода"

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
    def _actor_name(ctx: BattleContext, actor_id: int | str | None) -> str:
        actor = CombatLogBuilder._actor_ref(ctx, actor_id)
        return str((actor or {}).get("name") or "NO_TARGET")

    @staticmethod
    def _template_key(*, action_id: str | None, event_name: str) -> str:
        if action_id:
            return f"combat.{action_id}.{event_name}"
        return f"combat.exchange.basic.{event_name}"

    @staticmethod
    def _severity(result: InteractionResultDTO, event_name: str) -> str:
        if event_name == "death":
            return "death"
        if result.is_crit or event_name in {"crit", "crit_proc"}:
            return "good"
        if result.is_miss or result.is_dodged or result.is_parried or result.is_blocked:
            return "warning"
        if result.damage_final > 0:
            return "normal"
        return "normal"

    @classmethod
    def _templated_action_text(
        cls,
        *,
        action_type: str = "",
        action_id: str | None,
        event_name: str,
        source_name: str,
        target_name: str,
        values: dict[str, Any] | None = None,
        catalog: dict[str, Any] | None = None,
    ) -> str | None:
        if not action_id:
            return None

        entry = (catalog or {}).get("catalog_entry")
        if entry is None:
            entry, _key = cls._action_catalog_entry(action_type=action_type, action_id=action_id)
        if entry is not None:
            variant = entry.descriptive.variants.get("humanoid")
            resource_type = cls._catalog_resource_type(str(getattr(entry, "key", "")))
            templates = cls._templates_for_event(variant, event_name, resource_type=resource_type)
            if templates:
                return cls._format_template(
                    templates[0],
                    source_name=source_name,
                    target_name=target_name,
                    label=variant.display_name if variant else action_id,
                    label_key=resource_type,
                    values=values,
                )

        effect = CombatCatalogIntegrator.get_effect(action_id)
        if effect is not None:
            return cls._format_template(
                cls._effect_template(event_name),
                source_name=source_name,
                target_name=target_name,
                label=effect.name_ru,
                label_key="effect",
                values=values,
            )

        trigger_entry = CombatCatalogIntegrator.get_trigger_catalog_entry(action_id)
        if trigger_entry is not None:
            variant = trigger_entry.descriptive.variants.get("humanoid")
            if variant:
                resolved_event = cls._resolve_trigger_event_name(event_name)
                templates = (
                    getattr(variant.event_texts, resolved_event, [])
                    or getattr(variant.event_texts, "proc", [])
                    or getattr(variant.event_texts, event_name, [])
                )
                if templates:
                    return cls._format_template(
                        templates[0],
                        source_name=source_name,
                        target_name=target_name,
                        label=variant.display_name,
                        label_key="trigger",
                        values=values,
                    )

        return None

    @staticmethod
    def _resolve_trigger_event_name(event_name: str) -> str:
        return {
            "crit": "crit_proc",
            "hit": "hit_proc",
            "miss": "miss_proc",
            "dodge": "dodge_proc",
            "parry": "parry_proc",
            "block": "block_proc",
        }.get(event_name, "proc")

    # Triggers that generate a separate log entry (counter-attack, extra strike).
    # All others are merged into the main summary line as a suffix.
    _SEPARATE_LINE_TRIGGERS: frozenset[str] = frozenset(
        {
            "counter_on_parry",
            "counter_on_dodge",
            "style_dual_extra",
            "bash_on_block",
        }
    )

    @staticmethod
    def _should_merge_trigger(trigger_id: str) -> bool:
        return trigger_id not in CombatLogBuilder._SEPARATE_LINE_TRIGGERS

    @classmethod
    def _trigger_suffix_text(
        cls,
        result: InteractionResultDTO,
        *,
        outcome: str,
        source_name: str,
        target_name: str,
    ) -> str:
        parts: list[str] = []
        for trigger_id in result.fired_triggers:
            if not cls._should_merge_trigger(trigger_id):
                continue
            entry = CombatCatalogIntegrator.get_trigger_catalog_entry(trigger_id)
            if entry is None:
                continue
            variant = entry.descriptive.variants.get("humanoid")
            if not variant:
                continue
            proc_event = cls._resolve_trigger_event_name(outcome)
            templates = getattr(variant.event_texts, proc_event, []) or getattr(variant.event_texts, "proc", [])
            if not templates:
                continue
            effect_label = cls._first_applied_effect_label(entry, result)
            part = cls._format_values(
                templates[0],
                {
                    "source": source_name,
                    "target": target_name,
                    "trigger": variant.display_name,
                    "effect": effect_label,
                    "damage": result.damage_final,
                    "token": "",
                },
            )
            parts.append(part)
        return "; ".join(parts)

    @classmethod
    def _build_trigger_proc_entry(
        cls,
        *,
        ctx: BattleContext,
        result: InteractionResultDTO,
        trigger_id: str,
        outcome: str,
        timestamp: float,
        tags: list[str],
        global_turn: int,
    ) -> dict[str, Any] | None:
        entry = CombatCatalogIntegrator.get_trigger_catalog_entry(trigger_id)
        if entry is None:
            return None
        variant = entry.descriptive.variants.get("humanoid")
        if variant is None:
            return None

        source_name = cls._actor_name(ctx, result.source_id)
        target_name = cls._actor_name(ctx, result.target_id)
        proc_event = cls._resolve_trigger_event_name(outcome)

        templates = getattr(variant.event_texts, proc_event, []) or getattr(variant.event_texts, "proc", [])
        text = ""
        if templates:
            effect_label = cls._first_applied_effect_label(entry, result)
            try:
                text = cls._format_values(
                    templates[0],
                    {
                        "source": source_name,
                        "target": target_name,
                        "trigger": variant.display_name,
                        "effect": effect_label,
                        "damage": result.damage_final,
                        "token": "",
                    },
                )
            except KeyError:
                text = templates[0]

        return {
            "type": "TRIGGER_PROC",
            "kind": "trigger_proc",
            "text": text,
            "timestamp": timestamp,
            "tags": [*tags, "trigger_proc", f"trigger:{trigger_id}"],
            "global_turn": global_turn,
            "action_id": trigger_id,
            "source_id": result.source_id,
            "target_id": result.target_id,
            "source_name": source_name,
            "target_name": target_name,
            "outcome": outcome,
            "catalog": "combat_entries",
            "catalog_key": entry.key,
            "catalog_event": proc_event,
            "catalog_taxonomy": "humanoid",
            "template": {
                "key": entry.key,
                "event": proc_event,
                "taxonomy": "humanoid",
            },
            "source": cls._actor_ref(ctx, result.source_id),
            "target": cls._actor_ref(ctx, result.target_id),
            "variables": {
                "source": source_name,
                "target": target_name,
                "trigger": variant.display_name,
                "effect": cls._first_applied_effect_label(entry, result),
                "damage": result.damage_final,
            },
            "effects": cls._public_effects(ctx, result),
            "presentation": {
                "player_visible": True,
                "merge_with_result": False,
            },
        }

    @staticmethod
    def _first_applied_effect_label(
        trigger_entry: Any,
        result: InteractionResultDTO,
    ) -> str:
        if hasattr(trigger_entry, "technical") and trigger_entry.technical.applied_effect_ids:
            for effect_id in trigger_entry.technical.applied_effect_ids:
                effect = CombatCatalogIntegrator.get_effect(effect_id)
                if effect:
                    return effect.name_ru
        for effect in result.applied_effects:
            if isinstance(effect, dict):
                name = effect.get("name") or effect.get("id") or effect.get("effect_id") or ""
                if name:
                    return str(name)
        return ""

    @classmethod
    def _templates_for_event(cls, variant: Any, event_name: str, *, resource_type: str = "") -> list[str]:
        if variant is None:
            return []
        templates = getattr(variant.event_texts, event_name, [])
        if event_name == "area_result":
            return cls._combine_area_templates(variant.event_texts.area_use, templates)
        if resource_type == "feint" and event_name not in {"use", "no_resource"}:
            return cls._combine_area_templates(variant.event_texts.use, templates)
        return templates

    @staticmethod
    def _combine_area_templates(area_use: list[str], area_result: list[str]) -> list[str]:
        if area_use and area_result:
            return [f"{area_use[0]}, {area_result[0]}"]
        return area_use or area_result

    @classmethod
    def _action_catalog_entry(cls, *, action_type: str, action_id: str):
        candidate_keys = []
        if action_type == "item":
            candidate_keys.extend([f"combat.item.{action_id}", f"combat.ability.{action_id}"])
        elif action_type == "instant":
            candidate_keys.extend(
                [f"combat.ability.{action_id}", f"combat.gift.{action_id}", f"combat.item.{action_id}"]
            )
        elif action_type == "exchange":
            candidate_keys.append(f"combat.feint.{action_id}")
        else:
            candidate_keys.extend(
                [
                    f"combat.ability.{action_id}",
                    f"combat.gift.{action_id}",
                    f"combat.item.{action_id}",
                    f"combat.feint.{action_id}",
                ]
            )
        for key in candidate_keys:
            entry = CombatCatalogIntegrator.get_catalog_entry_by_key(key)
            if entry is not None:
                return entry, key
        return None, None

    @staticmethod
    def _catalog_resource_type(catalog_key: str) -> str:
        parts = catalog_key.split(".")
        if len(parts) >= 3:
            return parts[1]
        return "ability"

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

        feint_entry = CombatCatalogIntegrator.get_feint_catalog_entry_by_key(f"combat.feint.{feint_id}")
        if feint_entry is None:
            return None

        variant = feint_entry.descriptive.variants.get(
            feint_entry.descriptive.default_taxonomy
        ) or feint_entry.descriptive.variants.get("humanoid")
        if variant is None:
            return None

        use_templates = variant.event_texts.use
        outcome_templates = getattr(variant.event_texts, outcome, [])
        if not use_templates and not outcome_templates:
            return None

        values = cls._template_values(result, source_name=source_name, target_name=target_name)
        values["feint"] = variant.display_name
        use_text = cls._format_values(use_templates[0], values) if use_templates else ""
        outcome_text = cls._format_values(outcome_templates[0], values) if outcome_templates else ""
        if use_text and outcome_text:
            return f"{use_text}, {outcome_text}"
        return use_text or outcome_text

    @classmethod
    def _basic_exchange_summary_text(
        cls,
        result: InteractionResultDTO,
        *,
        exchange_id: str | None,
        outcome: str,
        source_name: str,
        target_name: str,
    ) -> str | None:
        if not exchange_id:
            return None

        entry = CombatCatalogIntegrator.get_basic_exchange(exchange_id)
        if entry is None:
            return None

        variant = entry.descriptive.variants.get(entry.descriptive.default_taxonomy) or entry.descriptive.variants.get(
            "humanoid"
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
            "weapon": entry.technical.weapon_class,
            "damage": result.damage_final,
            "healing": result.healing_final,
            "hand": entry.technical.hand,
            "skill": entry.technical.skill_key,
            "outcome": outcome,
        }

        use_text = cls._format_values(use_templates[0], values) if use_templates else ""
        outcome_text = cls._format_values(outcome_templates[0], values) if outcome_templates else ""
        if use_text and outcome_text:
            return f"{use_text}, {outcome_text}"
        return use_text or outcome_text

    @staticmethod
    def _derive_exchange_id(ctx: BattleContext, action: CombatActionDTO) -> str | None:
        if action.action_type != "exchange":
            return None
        actor = ctx.get_actor(action.move.char_id)
        if actor is None:
            return None
        payload = action.move.payload
        hand = getattr(payload, "hand", None)
        source_type = "off_hand" if hand == "off" else "main_hand"
        skill_key = actor.loadout.layout.get(source_type)
        if not skill_key:
            return None
        weapon_class = skill_key.replace("skill_", "")
        return f"skill_{weapon_class}.{source_type}"

    @staticmethod
    def _format_values(template: str, values: dict[str, Any]) -> str:
        return template.format(**values)

    @classmethod
    def _template_values(cls, result: InteractionResultDTO, *, source_name: str, target_name: str) -> dict[str, Any]:
        return {
            "source": source_name,
            "target": target_name,
            "ability": "",
            "feint": "",
            "gift": "",
            "item": "",
            "effect": cls._first_effect_label(result),
            "trigger": "",
            "damage": result.damage_final,
            "healing": result.healing_final,
            "resource": "hp" if result.damage_final or result.healing_final else "",
            "outcome": cls._result_outcome(result),
            "targets_count": 1,
        }

    @staticmethod
    def _first_effect_label(result: InteractionResultDTO) -> str:
        for effect in result.applied_effects:
            if not isinstance(effect, dict):
                continue
            effect_id = effect.get("id") or effect.get("effect_id")
            if not effect_id:
                continue
            effect_config = CombatCatalogIntegrator.get_effect(str(effect_id))
            return str(getattr(effect_config, "name_ru", None) or effect.get("name") or effect_id)
        for event in result.events:
            if event.type != "APPLY_EFFECT" or not event.action_id:
                continue
            effect_config = CombatCatalogIntegrator.get_effect(str(event.action_id))
            return str(getattr(effect_config, "name_ru", None) or event.action_id)
        return ""

    @staticmethod
    def _effect_template(event_name: str) -> str:
        return {
            "apply_effect": "{source} накладывает {effect} на {target}",
            "expire_effect": "{effect} на {target} заканчивается",
            "tick": "{effect} действует на {target}",
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
            "ability": "",
            "feint": "",
            "gift": "",
            "item": "",
            "effect": "",
            "trigger": "",
            "damage": 0,
            "healing": 0,
            "resource": "",
            "outcome": "",
            "targets_count": 1,
        }
        if values:
            template_values.update(values)
        for key in ("ability", "feint", "gift", "item", "effect", "trigger"):
            if not template_values.get(key):
                template_values[key] = label if key == label_key else template_values.get(key, "")
        template_values[label_key] = label
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
            return f"{source_name} атакует {target_name}"
        if action.action_type == "instant":
            return f"{source_name} применяет{action_text} на {target_name}"
        if action.action_type == "item":
            return f"{source_name} использует{action_text} на {target_name}"
        return f"{source_name} действует"

    @staticmethod
    def _action_id(action: CombatActionDTO) -> str | None:
        payload = action.move.payload
        for key in ("ability_id", "item_id", "feint_id"):
            value = getattr(payload, key, None)
            if value:
                return str(value)
        return None

    @staticmethod
    def _result_action_id(result: InteractionResultDTO) -> str | None:
        for event in result.events:
            if event.action_id:
                return str(event.action_id)
        return None

    @staticmethod
    def _first_event_source_id(result: InteractionResultDTO) -> int | None:
        for event in result.events:
            if event.source_id is not None:
                return event.source_id
        return None

    @staticmethod
    def _first_event_target_id(result: InteractionResultDTO) -> int | None:
        for event in result.events:
            if event.target_id is not None:
                return event.target_id
        return None

    @staticmethod
    def _feint_id(action: CombatActionDTO) -> str | None:
        value = getattr(action.move.payload, "feint_id", None)
        return str(value) if value else None

    @classmethod
    def _variables(
        cls,
        *,
        result: InteractionResultDTO,
        source: dict[str, Any] | None,
        target: dict[str, Any] | None,
        targets_count: int = 1,
    ) -> dict[str, str | int | float]:
        return {
            "source": str((source or {}).get("name") or "NO_SOURCE"),
            "target": str((target or {}).get("name") or "NO_TARGET"),
            "damage": result.damage_final,
            "healing": result.healing_final,
            "effect": cls._first_effect_label(result),
            "targets_count": targets_count,
        }

    @staticmethod
    def _apply_catalog_variables(variables: dict[str, str | int | float], catalog: dict[str, Any]) -> None:
        entry = catalog.get("catalog_entry")
        if entry is None:
            return
        variant = entry.descriptive.variants.get("humanoid")
        label = getattr(variant, "display_name", "")
        resource_type = str(catalog.get("resource_type") or "")
        if label and resource_type in {"ability", "gift", "item", "feint"}:
            variables[resource_type] = label

    @staticmethod
    def _entry_kind(
        result: InteractionResultDTO, *, action_type: str, is_area: bool = False, catalog: dict[str, Any] | None = None
    ) -> str:
        if is_area:
            resource_type = (catalog or {}).get("resource_type") or action_type
            if resource_type in {"ability", "gift", "item"}:
                return f"{resource_type}_area_result"
        if CombatLogBuilder._has_event(result, "DEATH"):
            return "death"
        if CombatLogBuilder._has_event(result, "TICK"):
            return "effect_tick"
        if (result.applied_effects or CombatLogBuilder._has_event(result, "APPLY_EFFECT")) and not result.is_hit:
            return "effect_apply"
        if action_type == "exchange":
            return "exchange"
        return action_type

    @staticmethod
    def _has_event(result: InteractionResultDTO, event_type: str) -> bool:
        return any(event.type == event_type for event in result.events)

    @staticmethod
    def _public_flags(result: InteractionResultDTO) -> dict[str, bool]:
        return {
            "crit": result.is_crit,
            "dodged": result.is_dodged,
            "parried": result.is_parried,
            "blocked": result.is_blocked,
            "missed": result.is_miss,
            "counter": result.is_counter,
            "death": CombatLogBuilder._has_event(result, "DEATH"),
        }

    @staticmethod
    def _result_outcome(result: InteractionResultDTO) -> str:
        if CombatLogBuilder._has_event(result, "DEATH"):
            return "death"
        if CombatLogBuilder._has_event(result, "TICK"):
            return "tick"
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
        if CombatLogBuilder._has_event(result, "APPLY_EFFECT"):
            return "apply_effect"
        if result.applied_effects:
            return "apply_effect"
        return "none"

    @staticmethod
    def _is_area_action(action: CombatActionDTO) -> bool:
        targets = action.move.targets or []
        if len(targets) > 1:
            return True
        payload_target = getattr(action.move.payload, "target_id", None)
        return isinstance(payload_target, list) and len(payload_target) > 1

    @classmethod
    def _target_refs(
        cls, ctx: BattleContext, *, action: CombatActionDTO, fallback_target_id: int | str | None
    ) -> list[dict[str, Any]]:
        ids: list[int | str] = []
        if action.move.targets:
            ids.extend(action.move.targets)
        else:
            payload_target = getattr(action.move.payload, "target_id", None)
            if isinstance(payload_target, list):
                ids.extend(payload_target)
            elif payload_target is not None:
                ids.append(payload_target)
        if not ids and fallback_target_id is not None:
            ids.append(fallback_target_id)
        refs = [cls._actor_ref(ctx, actor_id) for actor_id in ids]
        return [ref for ref in refs if ref is not None]

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
        action_id = cls._log_action_id(result, action)
        is_area = cls._is_area_action(action)
        event_name = "area_result" if is_area else outcome
        source_id = result.source_id if result.source_id is not None else cls._first_event_source_id(result)
        target_id = result.target_id if result.target_id is not None else cls._first_event_target_id(result)
        source = cls._actor_ref(ctx, source_id)
        target = cls._actor_ref(ctx, target_id)
        targets = cls._target_refs(ctx, action=action, fallback_target_id=target_id)
        variables = cls._variables(result=result, source=source, target=target, targets_count=len(targets))
        template = cls._combat_text_template(
            ctx=ctx,
            result=result,
            action=action,
            action_id=action_id,
            event_name=event_name,
            source_id=source_id,
            target_id=target_id,
        )
        cls._apply_combat_text_variables(variables, template, action_id=action_id)
        text = cls._render_combat_text(template, variables)
        text = cls._append_reflect_text(text, result=result, source=source, target=target)
        catalog = cls._combat_text_catalog_fields(template)
        public_result = cls._public_result(ctx, result)
        tags = ["runtime", action.action_type, f"wave:{wave}", f"turn:{global_turn}", f"outcome:{outcome}"]
        if action.is_forced:
            tags.append("forced")

        entry = {
            "id": f"{global_turn}:{wave}:{source_id or 'none'}:{target_id or 'none'}:0",
            "type": "LOG",
            "kind": cls._entry_kind(result, action_type=action.action_type, is_area=is_area, catalog=catalog),
            "text": text,
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
                "key": template["key"],
                "event": template["outcome"],
                "taxonomy": catalog.get("catalog_taxonomy") or "humanoid",
                "variant": 0,
                "text": template["template"],
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
        if cls._effect_fact_entries_should_replace_primary(result):
            return cls.build_effect_fact_entries(
                ctx=ctx,
                result=result,
                action=action,
                wave=wave,
                timestamp=timestamp,
            )
        entries = [entry]
        for trigger_id in result.fired_triggers:
            display_policy = cls._trigger_display_policy(result, trigger_id)
            if display_policy == "silent":
                continue
            if cls._should_merge_trigger(trigger_id) and display_policy != "separate":
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
        entries.extend(
            cls.build_effect_fact_entries(
                ctx=ctx,
                result=result,
                action=action,
                wave=wave,
                timestamp=timestamp,
                skip_effect_id=str(entry["action"].get("id") or "")
                if str(entry.get("kind") or "").startswith("effect_")
                else "",
            )
        )
        return entries

    @staticmethod
    def _effect_fact_entries_should_replace_primary(result: InteractionResultDTO) -> bool:
        if (
            result.skip_reason
            or result.is_miss
            or result.is_dodged
            or result.is_parried
            or result.is_blocked
            or result.is_hit
            or result.damage_final > 0
            or result.healing_final > 0
            or result.reflected_damage > 0
        ):
            return False
        return any(
            str(getattr(fact, "action", "") or "") in {"apply", "expire", "resist", "cleanse"}
            for fact in result.effect_facts
        )

    @classmethod
    def build_effect_fact_entries(
        cls,
        *,
        ctx: BattleContext,
        result: InteractionResultDTO,
        action: CombatActionDTO,
        wave: int,
        timestamp: float,
        skip_effect_id: str = "",
    ) -> list[dict[str, Any]]:
        global_turn = ctx.meta.step_counter + 1
        entries: list[dict[str, Any]] = []
        source_id = result.source_id if result.source_id is not None else action.move.char_id
        source = cls._actor_ref(ctx, source_id)
        for fact in result.effect_facts:
            fact_action = str(getattr(fact, "action", "") or "")
            if fact_action not in {"apply", "expire", "resist", "cleanse"}:
                continue
            effect_id = str(getattr(fact, "effect_id", "") or "")
            if not effect_id or effect_id == skip_effect_id:
                continue
            target_id = getattr(fact, "actor_id", None)
            target = cls._actor_ref(ctx, target_id)
            text = cls._effect_fact_text(ctx, effect_id=effect_id, action=fact_action, source=source, target=target)
            kind = f"effect_{fact_action}"
            entries.append(
                {
                    "id": f"{global_turn}:{wave}:effect:{target_id or 'none'}:{effect_id}:{len(entries)}",
                    "type": "LOG",
                    "kind": kind,
                    "text": text,
                    "timestamp": timestamp,
                    "tags": ["runtime", "effect", fact_action, f"turn:{global_turn}"],
                    "global_turn": global_turn,
                    "wave": wave,
                    "source": source,
                    "target": target,
                    "targets": [target] if target else [],
                    "action": {
                        "mode": action.action_type,
                        "id": effect_id,
                        "catalog": "combat_text",
                        "catalog_key": f"combat.effect.{effect_id}",
                        "event": fact_action,
                        "taxonomy": "humanoid",
                    },
                    "template": {
                        "key": f"combat.effect.{effect_id}.{fact_action}.runtime",
                        "event": fact_action,
                        "taxonomy": "humanoid",
                        "variant": 0,
                        "text": text,
                    },
                    "variables": {
                        "source": str((source or {}).get("name") or "NO_SOURCE"),
                        "target": str((target or {}).get("name") or "NO_TARGET"),
                        "effect": cls._effect_label(
                            CombatCatalogIntegrator.get_effect_catalog_entry(effect_id), effect_id
                        ),
                    },
                    "result": {
                        "resources": [],
                        "tokens": [],
                        "effects": [
                            {
                                "actor_id": str(target_id) if target_id is not None else None,
                                "owner": getattr(fact, "owner", "target"),
                                "effect_id": effect_id,
                                "action": fact_action,
                                "duration": getattr(fact, "duration", None),
                                "icon": f"combat/effects/{effect_id}.svg",
                                "tooltip": cls._effect_label(
                                    CombatCatalogIntegrator.get_effect_catalog_entry(effect_id), effect_id
                                ),
                            }
                        ],
                    },
                    "presentation": {
                        "player_visible": True,
                        "severity": "normal" if fact_action != "resist" else "warning",
                        "render": "inline_result",
                    },
                    "outcome": fact_action,
                    "severity": "normal" if fact_action != "resist" else "warning",
                    "catalog": "combat_text",
                    "catalog_key": f"combat.effect.{effect_id}.{fact_action}.runtime",
                    "catalog_event": fact_action,
                    "catalog_taxonomy": "humanoid",
                    "catalog_tooltip": "",
                    "resources": [],
                    "effects": [
                        {
                            "actor_id": str(target_id) if target_id is not None else None,
                            "owner": getattr(fact, "owner", "target"),
                            "effect_id": effect_id,
                            "action": fact_action,
                            "duration": getattr(fact, "duration", None),
                            "icon": f"combat/effects/{effect_id}.svg",
                            "tooltip": cls._effect_label(
                                CombatCatalogIntegrator.get_effect_catalog_entry(effect_id), effect_id
                            ),
                        }
                    ],
                    "badges": [],
                    "flags": {},
                }
            )
        return entries

    @classmethod
    def _effect_fact_text(
        cls,
        ctx: BattleContext,
        *,
        effect_id: str,
        action: str,
        source: dict[str, Any] | None,
        target: dict[str, Any] | None,
    ) -> str:
        effect_entry = CombatCatalogIntegrator.get_effect_catalog_entry(effect_id)
        effect = cls._effect_label(effect_entry, effect_id)
        event = {
            "apply": "apply_effect",
            "expire": "expire_effect",
            "resist": "resist",
            "cleanse": "cleanse",
        }.get(action, action)
        template_text = None
        if effect_entry is not None:
            target_body = cls._actor_body(ctx, (target or {}).get("id"))
            resolved = effect_entry.descriptive.resolve_event_template(event, [target_body])
            template_text = resolved.text if resolved else None
        if not template_text:
            template_text = {
                "apply": "{target} получает {effect}.",
                "expire": "{effect} {target} проходит.",
                "resist": "{target} сопротивляется: {effect} не закрепляется.",
                "cleanse": "{effect} {target} снят.",
            }.get(action, "{target}: {effect}.")
        return cls._render_combat_text(
            {"template": template_text},
            {
                "source": str((source or {}).get("name") or "NO_SOURCE"),
                "target": str((target or {}).get("name") or "NO_TARGET"),
                "effect": effect,
            },
        )

    @classmethod
    def _combat_text_template(
        cls,
        *,
        ctx: BattleContext,
        result: InteractionResultDTO,
        action: CombatActionDTO,
        action_id: str | None,
        event_name: str,
        source_id: int | str | None,
        target_id: int | str | None,
    ) -> dict[str, Any]:
        resource_type, resource_id, delivery, tags = cls._combat_text_request(
            ctx=ctx,
            result=result,
            action=action,
            action_id=action_id,
            event_name=event_name,
            source_id=source_id,
        )
        source_body = cls._actor_body(ctx, source_id)
        target_body = cls._actor_body(ctx, target_id)
        outcome = cls._combat_text_outcome(event_name)
        if outcome == "controlled":
            controlled_template = cls._controlled_effect_template(ctx=ctx, result=result, target_id=source_id)
            if controlled_template is not None:
                return controlled_template
        try:
            template = CombatCatalogIntegrator.get_combat_text_template(
                resource_type=resource_type,
                resource_id=resource_id,
                outcome=outcome,
                source_body=source_body,
                target_body=target_body,
                delivery=delivery,
                tags=tags,
            )
        except RuntimeError as exc:
            return cls._runtime_fallback_template(
                resource_type=resource_type,
                resource_id=resource_id,
                outcome=outcome,
                source_body=source_body,
                target_body=target_body,
                delivery=delivery,
                reason=str(exc),
            )
        if template is None:
            return cls._runtime_fallback_template(
                resource_type=resource_type,
                resource_id=resource_id,
                outcome=outcome,
                source_body=source_body,
                target_body=target_body,
                delivery=delivery,
                reason="integrator returned no template",
            )
        return dict(template)

    @classmethod
    def _controlled_effect_template(
        cls, *, ctx: BattleContext, result: InteractionResultDTO, target_id: int | str | None
    ) -> dict[str, Any] | None:
        effect_id = ""
        for fact in result.effect_facts:
            if "control" in set(getattr(fact, "tags", []) or []):
                effect_id = str(getattr(fact, "effect_id", "") or "")
                break
        if not effect_id:
            return None
        effect_entry = CombatCatalogIntegrator.get_effect_catalog_entry(effect_id)
        if effect_entry is None:
            return None
        resolved = effect_entry.descriptive.resolve_event_template(
            "control_prevent_action", [cls._actor_body(ctx, target_id)]
        )
        if resolved is None:
            return None
        return {
            "key": f"combat.effect.{effect_id}.control_prevent_action.runtime",
            "template": resolved.text,
            "variables": ["source", "target", "effect"],
            "resource_type": "effect",
            "resource_id": effect_id,
            "catalog_key": f"combat.effect.{effect_id}",
            "outcome": "controlled",
            "body_pair": "",
            "target_body": cls._actor_body(ctx, target_id),
            "delivery": "default",
            "phrase_keys": {},
            "tags": ["runtime", "effect", "control"],
        }

    @staticmethod
    def _runtime_fallback_template(
        *,
        resource_type: str,
        resource_id: str,
        outcome: str,
        source_body: str = "",
        target_body: str = "",
        delivery: str = "default",
        pattern: str = "{source} действует на {target}: {target_results}. (F)",
        variables: list[str] | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        return {
            "key": f"combat_text.runtime_fallback.{resource_type or 'unknown'}.{outcome or 'unknown'}",
            "template": pattern,
            "variables": variables or ["source", "target", "target_results"],
            "resource_type": resource_type or "unknown",
            "resource_id": resource_id or "unknown",
            "catalog_key": f"combat_text.runtime_fallback.{resource_type or 'unknown'}",
            "outcome": outcome or "none",
            "body_pair": f"{source_body}_to_{target_body}" if source_body and target_body else "",
            "target_body": target_body,
            "delivery": delivery or "default",
            "phrase_keys": {},
            "tags": ["runtime", "fallback", "missing_combat_text", *(["resolution_error"] if reason else [])],
            "resolution_error": reason,
        }

    @classmethod
    def _combat_text_request(
        cls,
        *,
        ctx: BattleContext,
        result: InteractionResultDTO,
        action: CombatActionDTO,
        action_id: str | None,
        event_name: str,
        source_id: int | str | None,
    ) -> tuple[str, str, str, tuple[str, ...]]:
        outcome = cls._combat_text_outcome(event_name)
        if outcome == "tick" and action_id:
            return "effect", action_id, cls._effect_tick_resource(result), ()
        if outcome == "apply" and action_id and CombatCatalogIntegrator.get_effect_catalog_entry(action_id) is not None:
            return "effect", action_id, "default", ()
        if outcome == "death":
            return "death", "death", "default", cls._death_tags(result)
        if action.action_type == "exchange":
            delivery, surface_tags = cls._source_delivery(ctx, source_id, action)
            feint_id = None if result.is_counter else cls._feint_id(action)
            if feint_id:
                return "feint", feint_id, delivery, surface_tags
            return (
                "basic_exchange",
                cls._basic_exchange_resource_id(ctx, source_id, action, delivery),
                delivery,
                surface_tags,
            )
        if action.action_type == "item":
            return "item", str(action_id or ""), "area" if event_name == "area_result" else "default", ()
        if action.action_type == "instant":
            resource_type = (
                "gift" if action_id and CombatCatalogIntegrator.get_gift_catalog_entry(action_id) else "ability"
            )
            delivery = "area" if event_name == "area_result" else "single" if event_name == "cast" else "default"
            return resource_type, str(action_id or ""), delivery, ()
        if action_id and CombatCatalogIntegrator.get_trigger_catalog_entry(action_id) is not None:
            return "trigger", cls._trigger_resource_id(action_id), "default", ()
        if action_id and CombatCatalogIntegrator.get_effect_catalog_entry(action_id) is not None:
            return "effect", action_id, "default", ()
        delivery = cls._source_delivery(ctx, source_id, action)[0]
        return "basic_exchange", cls._basic_exchange_resource_id(ctx, source_id, action, delivery), delivery, ()

    @staticmethod
    def _combat_text_outcome(event_name: str) -> str:
        if event_name == "apply_effect":
            return "apply"
        return event_name

    @staticmethod
    def _effect_tick_resource(result: InteractionResultDTO) -> str:
        for event in result.events:
            if event.type == "TICK" and event.resource:
                return str(event.resource)
        return "hp"

    @staticmethod
    def _death_tags(result: InteractionResultDTO) -> tuple[str, ...]:
        if result.damage_final > 0:
            return ("damage",)
        if CombatLogBuilder._has_event(result, "TICK"):
            return ("dot",)
        if CombatLogBuilder._result_action_id(result):
            return ("ability",)
        return ("unknown",)

    @staticmethod
    def _trigger_resource_id(trigger_id: str) -> str:
        return trigger_id.replace(".", "_")

    @staticmethod
    def _action_source_type(action: CombatActionDTO) -> str:
        payload = action.move.payload
        hand = getattr(payload, "hand", None)
        return "off_hand" if hand == "off" else "main_hand"

    @staticmethod
    def _actor_body(ctx: BattleContext, actor_id: int | str | None) -> str:
        actor = ctx.get_actor(actor_id) if actor_id is not None else None
        value = str(getattr(getattr(actor, "meta", None), "archetype", None) or "humanoid")
        return value if value in {"humanoid", "beast"} else "humanoid"

    @staticmethod
    def _source_delivery(
        ctx: BattleContext,
        source_id: int | str | None,
        action: CombatActionDTO,
    ) -> tuple[str, tuple[str, ...]]:
        if action.action_type == "instant":
            return "magic", ()
        if action.action_type == "item":
            return "item", ()
        actor = ctx.get_actor(source_id) if source_id is not None else None
        source_type = CombatLogBuilder._action_source_type(action)
        surface = getattr(getattr(actor, "loadout", None), "combat_surfaces", {}).get(source_type) if actor else None
        if surface is not None:
            if isinstance(surface, dict):
                delivery = str(surface.get("delivery") or "weapon")
                tags = tuple(str(tag) for tag in surface.get("tags") or [])
            else:
                delivery = str(getattr(surface, "delivery", "") or "weapon")
                tags = tuple(str(tag) for tag in getattr(surface, "tags", []) or [])
            return delivery, tags
        layout = getattr(getattr(actor, "loadout", None), "layout", {}) if actor else {}
        if layout.get(source_type) == "skill_unarmed":
            return "unarmed", ()
        meta = getattr(actor, "meta", None)
        if str(getattr(meta, "type", "") or "") == "monster" and str(getattr(meta, "archetype", "") or "") == "beast":
            return "natural", ()
        return "weapon", ()

    @staticmethod
    def _basic_exchange_resource_id(
        ctx: BattleContext,
        source_id: int | str | None,
        action: CombatActionDTO,
        delivery: str,
    ) -> str:
        actor = ctx.get_actor(source_id) if source_id is not None else None
        source_type = CombatLogBuilder._action_source_type(action)
        loadout = getattr(actor, "loadout", None)
        surface = getattr(loadout, "combat_surfaces", {}).get(source_type) if loadout else None
        if delivery == "natural":
            return CombatLogBuilder._natural_basic_exchange_resource_id(surface, source_type)

        if isinstance(surface, dict):
            skill_key = str(surface.get("skill_key") or "")
        else:
            skill_key = str(getattr(surface, "skill_key", "") or "")
        if not skill_key:
            layout = getattr(loadout, "layout", {}) if loadout else {}
            skill_key = str(layout.get(source_type) or "")
        if not skill_key and delivery == "unarmed":
            skill_key = "skill_unarmed"

        exchange_id = f"{skill_key}.{source_type}" if skill_key else ""
        if exchange_id and CombatCatalogIntegrator.get_basic_exchange(exchange_id) is not None:
            return exchange_id
        return "default"

    @staticmethod
    def _natural_basic_exchange_resource_id(surface: Any, source_type: str) -> str:
        tags: set[str] = set()
        surface_name = ""
        if isinstance(surface, dict):
            tags.update(str(tag) for tag in surface.get("tags") or [])
            surface_name = str(surface.get("surface") or surface.get("base_id") or surface.get("item_id") or "")
        elif surface is not None:
            tags.update(str(tag) for tag in getattr(surface, "tags", []) or [])
            surface_name = str(
                getattr(surface, "surface", "")
                or getattr(surface, "base_id", "")
                or getattr(surface, "item_id", "")
                or ""
            )
        tags.add(surface_name)

        if {"fangs", "teeth", "jaws", "maw"} & tags:
            weapon_class = "fangs"
        elif {"claws", "paw", "forepaws"} & tags:
            weapon_class = "claws"
        else:
            weapon_class = "default"

        exchange_id = f"natural_weapon.{weapon_class}.{source_type}"
        if CombatCatalogIntegrator.get_basic_exchange(exchange_id) is not None:
            return exchange_id
        return f"natural_weapon.default.{source_type}"

    @staticmethod
    def _combat_text_catalog_fields(template: dict[str, Any]) -> dict[str, Any]:
        return {
            "catalog": "combat_text",
            "catalog_key": template["key"],
            "catalog_event": template.get("outcome") or "",
            "catalog_taxonomy": template.get("body_pair") or template.get("target_body") or "humanoid",
            "catalog_tooltip": "",
            "resource_type": template.get("resource_type") or "",
            "resource_id": template.get("resource_id") or "",
        }

    @classmethod
    def _apply_combat_text_variables(
        cls,
        variables: dict[str, str | int | float],
        template: dict[str, Any],
        *,
        action_id: str | None = None,
    ) -> None:
        resource_type = str(template.get("resource_type") or "")
        resource_id = str(template.get("resource_id") or "")
        label = cls._resource_label(resource_type, str(action_id or resource_id))
        if label and resource_type in {"ability", "gift", "item", "feint", "effect", "trigger"}:
            variables[resource_type] = label
        if resource_type == "ability" and label and not variables.get("effect"):
            variables["effect"] = label
        variables.setdefault("resource", "hp")
        variables.setdefault("value", variables.get("damage") or variables.get("healing") or 0)
        variables.setdefault("target_results", cls._target_result_text(variables))

    @staticmethod
    def _target_result_text(variables: dict[str, str | int | float]) -> str:
        damage = int(variables.get("damage") or 0)
        healing = int(variables.get("healing") or 0)
        if damage > 0:
            return f"{variables.get('target')} получает {damage} урона"
        if healing > 0:
            return f"{variables.get('target')} восстанавливает {healing} здоровья"
        return str(variables.get("effect") or "эффект не закрепляется")

    @staticmethod
    def _resource_label(resource_type: str, resource_id: str) -> str:
        entry = None
        if resource_type == "ability":
            entry = CombatCatalogIntegrator.get_ability_catalog_entry(resource_id)
        elif resource_type == "gift":
            entry = CombatCatalogIntegrator.get_gift_catalog_entry(resource_id)
        elif resource_type == "item":
            entry = CombatCatalogIntegrator.get_combat_item_action_catalog_entry(resource_id)
        elif resource_type == "feint":
            entry = CombatCatalogIntegrator.get_feint_catalog_entry(resource_id)
        elif resource_type == "effect":
            entry = CombatCatalogIntegrator.get_effect_catalog_entry(resource_id)
        elif resource_type == "trigger":
            entry = CombatCatalogIntegrator.get_trigger_catalog_entry(resource_id)
        if entry is None:
            return resource_id
        descriptive = getattr(entry, "descriptive", None)
        if descriptive is None:
            return resource_id
        variant = descriptive.variants.get(descriptive.default_taxonomy) or descriptive.variants.get("humanoid")
        return str(getattr(variant, "display_name", None) or resource_id)

    @staticmethod
    def _render_combat_text(template: dict[str, Any], variables: dict[str, str | int | float]) -> str:
        try:
            return str(template.get("template") or "{source} действует на {target}: {target_results}. (F)").format(
                **variables
            )
        except (KeyError, ValueError, IndexError):
            source = str(variables.get("source") or "NO_SOURCE")
            target = str(variables.get("target") or "NO_TARGET")
            target_results = str(variables.get("target_results") or variables.get("effect") or "результат не описан")
            return f"{source} действует на {target}: {target_results}. (F)"

    @staticmethod
    def _append_reflect_text(
        text: str,
        *,
        result: InteractionResultDTO,
        source: dict[str, Any] | None,
        target: dict[str, Any] | None,
    ) -> str:
        if result.reflected_damage <= 0:
            return text
        source_name = str((source or {}).get("name") or "атакующему")
        target_name = str((target or {}).get("name") or "защитника")
        return f"{text} Щит {target_name} возвращает {source_name} {result.reflected_damage} урона."

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
    def _resource_deltas(result: InteractionResultDTO) -> list[tuple[int | str | None, str, int]]:
        deltas: list[tuple[int | str | None, str, int]] = []
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
    def _effect_icon_url(cls, effect_id: str) -> str:
        # Check standard icons
        if effect_id in {"dot_bleed", "bleed", "bleeding"}:
            return "/static/images/ui/combat-icons/bleeding.svg"
        if effect_id == "burn":
            return "/static/images/ui/combat-icons/burn.svg"
        if effect_id == "poison":
            return "/static/images/ui/combat-icons/poison.svg"
        if effect_id == "stun":
            return "/static/images/ui/combat-icons/stun.svg"
        if effect_id == "death":
            return "/static/images/ui/combat-icons/target.svg"
        if effect_id == "ranged_position":
            return "/static/images/ui/combat-icons/ranged_position.svg"
        if effect_id.startswith("prep_brace_guard") or "guard" in effect_id or "defense" in effect_id or "block" in effect_id:
            return "/static/images/ui/combat-icons/shield.svg"
        if "dodge" in effect_id:
            return "/static/images/ui/combat-icons/token-dodge.svg"
        if "parry" in effect_id:
            return "/static/images/ui/combat-icons/token-parry.svg"
        if "counter" in effect_id:
            return "/static/images/ui/combat-icons/token-counter.svg"
        return "/static/images/ui/combat-icons/token.svg"

    @classmethod
    def _public_effects(cls, ctx: BattleContext, result: InteractionResultDTO) -> list[dict[str, Any]]:
        effects: list[dict[str, Any]] = []
        for effect in result.applied_effects:
            if not isinstance(effect, dict):
                continue
            effect_id = str(effect.get("id") or effect.get("effect_id") or "")
            if not effect_id:
                continue
            effect_entry = CombatCatalogIntegrator.get_effect_catalog_entry(effect_id)
            target_id = effect.get("target_id", result.target_id)
            duration = cls._effect_duration(effect, effect_entry)
            label = cls._effect_label(effect_entry, effect_id)
            effects.append(
                {
                    "actor_id": str(target_id) if target_id is not None else None,
                    "owner": "target",
                    "effect_id": effect_id,
                    "action": "apply",
                    "duration": duration,
                    "label": label,
                    "icon": cls._effect_icon_url(effect_id),
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
                    "label": "Побежден",
                    "icon": "/static/images/ui/combat-icons/target.svg",
                    "tooltip": "Побежден",
                }
            )
        for event in result.events:
            if event.type != "APPLY_EFFECT" or not event.action_id:
                continue
            effect_id = str(event.action_id)
            if any(effect["effect_id"] == effect_id for effect in effects):
                continue
            effect_entry = CombatCatalogIntegrator.get_effect_catalog_entry(effect_id)
            duration = cls._effect_duration({}, effect_entry)
            label = cls._effect_label(effect_entry, effect_id)
            effects.append(
                {
                    "actor_id": str(event.target_id) if event.target_id is not None else None,
                    "owner": "target",
                    "effect_id": effect_id,
                    "action": "apply",
                    "duration": duration,
                    "label": label,
                    "icon": cls._effect_icon_url(effect_id),
                    "tooltip": cls._effect_tooltip(label, duration),
                }
            )
        return effects

    @staticmethod
    def _effect_duration(effect: dict[str, Any], effect_entry: Any) -> int | None:
        raw = effect.get("duration") or effect.get("expires_at_exchange")
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None
        technical = getattr(effect_entry, "technical", None)
        duration = getattr(technical, "duration", None)
        if duration is None:
            return None
        try:
            return int(duration)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _effect_label(effect_entry: Any, fallback: str) -> str:
        if effect_entry is None:
            return fallback
        descriptive = getattr(effect_entry, "descriptive", None)
        if descriptive is None:
            return fallback
        variant = descriptive.variants.get(descriptive.default_taxonomy) or descriptive.variants.get("humanoid")
        return str(getattr(variant, "display_name", None) or fallback)

    @staticmethod
    def _effect_tooltip(label: str, duration: int | None) -> str:
        if duration is None or duration >= 999:
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
            "counter_on_dodge",
            "style_dual_cross_cut",
            "weapon_riposte_on_parry",
            "weapon_shield_bash_on_block",
        }
    )

    @staticmethod
    def _should_merge_trigger(trigger_id: str) -> bool:
        return trigger_id not in CombatLogBuilder._SEPARATE_LINE_TRIGGERS

    @staticmethod
    def _trigger_display_policy(result: InteractionResultDTO, trigger_id: str) -> str:
        for fact in result.trigger_facts:
            if fact.trigger_id == trigger_id:
                return fact.display_policy
        return "merge"

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
        proc_event = "proc" if trigger_id == "style_dual_cross_cut" else cls._resolve_trigger_event_name(outcome)
        source = cls._actor_ref(ctx, result.source_id)
        target = cls._actor_ref(ctx, result.target_id)
        source_name = str((source or {}).get("name") or "NO_SOURCE")
        target_name = str((target or {}).get("name") or "NO_TARGET")
        resource_id = cls._trigger_resource_id(trigger_id)
        try:
            template = CombatCatalogIntegrator.get_combat_text_template(
                resource_type="trigger",
                resource_id=resource_id,
                outcome=proc_event,
                source_body=cls._actor_body(ctx, result.source_id),
                target_body=cls._actor_body(ctx, result.target_id),
                delivery="default",
                tags=(),
            )
        except RuntimeError as exc:
            template = cls._runtime_trigger_fallback_template(
                resource_id=resource_id,
                outcome=proc_event,
                target_body=cls._actor_body(ctx, result.target_id),
                reason=str(exc),
            )
        if template is None:
            template = cls._runtime_trigger_fallback_template(
                resource_id=resource_id,
                outcome=proc_event,
                target_body=cls._actor_body(ctx, result.target_id),
                reason="integrator returned no template",
            )
        template = dict(template)
        variables = {
            "source": source_name,
            "target": target_name,
            "trigger": cls._resource_label("trigger", resource_id),
            "effect": cls._first_effect_label(result),
            "damage": result.damage_final,
            "token": "",
        }
        text = cls._render_combat_text(template, variables)
        catalog = cls._combat_text_catalog_fields(template)

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
            "catalog": catalog.get("catalog"),
            "catalog_key": catalog.get("catalog_key"),
            "catalog_event": catalog.get("catalog_event"),
            "catalog_taxonomy": catalog.get("catalog_taxonomy"),
            "template": {
                "key": template["key"],
                "event": template["outcome"],
                "taxonomy": catalog.get("catalog_taxonomy") or "humanoid",
                "text": template["template"],
            },
            "source": source,
            "target": target,
            "variables": variables,
            "effects": cls._public_effects(ctx, result),
            "presentation": {
                "player_visible": True,
                "merge_with_result": False,
            },
        }

    @classmethod
    def _runtime_trigger_fallback_template(
        cls,
        *,
        resource_id: str,
        outcome: str,
        target_body: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        return cls._runtime_fallback_template(
            resource_type="trigger",
            resource_id=resource_id,
            outcome=outcome,
            target_body=target_body,
            pattern="{source} активирует {trigger}. (F)",
            variables=["source", "trigger"],
            reason=reason,
        )

    @classmethod
    def _first_effect_label(cls, result: InteractionResultDTO) -> str:
        for effect in result.applied_effects:
            if not isinstance(effect, dict):
                continue
            effect_id = effect.get("id") or effect.get("effect_id")
            if not effect_id:
                continue
            effect_entry = CombatCatalogIntegrator.get_effect_catalog_entry(str(effect_id))
            return str(cls._effect_label(effect_entry, str(effect.get("name") or effect_id)))
        for event in result.events:
            if event.type not in {"APPLY_EFFECT", "TICK"} or not event.action_id:
                continue
            effect_entry = CombatCatalogIntegrator.get_effect_catalog_entry(str(event.action_id))
            return cls._effect_label(effect_entry, str(event.action_id))
        return ""

    @staticmethod
    def _action_id(action: CombatActionDTO) -> str | None:
        payload = action.move.payload
        for key in ("ability_id", "item_id", "feint_id"):
            value = getattr(payload, key, None)
            if value:
                return str(value)
        return None

    @classmethod
    def _log_action_id(cls, result: InteractionResultDTO, action: CombatActionDTO) -> str | None:
        if cls._has_event(result, "TICK"):
            return cls._result_action_id(result)

        action_id = cls._action_id(action)
        if action_id:
            return action_id

        if cls._has_event(result, "APPLY_EFFECT") and not (result.is_hit or result.damage_final > 0):
            return cls._result_action_id(result)

        if action.action_type in {"instant", "item"}:
            return cls._result_action_id(result)

        return None

    @staticmethod
    def _result_action_id(result: InteractionResultDTO) -> str | None:
        for event in result.events:
            if event.action_id:
                return str(event.action_id)
        return None

    @staticmethod
    def _first_event_source_id(result: InteractionResultDTO) -> int | str | None:
        for event in result.events:
            if event.source_id is not None:
                return event.source_id
        return None

    @staticmethod
    def _first_event_target_id(result: InteractionResultDTO) -> int | str | None:
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
        value, resource = cls._event_value_and_resource(result)
        return {
            "source": str((source or {}).get("name") or "NO_SOURCE"),
            "target": str((target or {}).get("name") or "NO_TARGET"),
            "damage": result.damage_final,
            "healing": result.healing_final,
            "effect": cls._first_effect_label(result),
            "targets_count": targets_count,
            "bonus_damage": cls._bonus_damage(result),
            "value": value,
            "resource": resource,
        }

    @staticmethod
    def _event_value_and_resource(result: InteractionResultDTO) -> tuple[int | float, str]:
        for event in result.events:
            if event.value is None or not event.resource:
                continue
            value = abs(float(event.value))
            return (int(value) if value.is_integer() else value, str(event.resource))
        if result.damage_final:
            return result.damage_final, "hp"
        if result.healing_final:
            return result.healing_final, "hp"
        return 0, "hp"

    @staticmethod
    def _bonus_damage(result: InteractionResultDTO) -> int | float:
        details = result.damage_trace.details if result.damage_trace else {}
        raw = details.get("weapon_technique_bonus_damage", 0)
        try:
            value = float(raw or 0)
        except (TypeError, ValueError):
            return 0
        if value.is_integer():
            return int(value)
        return round(value, 2)

    @staticmethod
    def _entry_kind(
        result: InteractionResultDTO, *, action_type: str, is_area: bool = False, catalog: dict[str, Any] | None = None
    ) -> str:
        if is_area:
            resource_type = (catalog or {}).get("resource_type") or action_type
            if resource_type in {"ability", "gift", "item"}:
                return f"{resource_type}_area_result"
        if CombatLogBuilder._has_event(result, "TICK"):
            return "effect_tick"
        if CombatLogBuilder._has_event(result, "DEATH"):
            return "death"
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
            "reflect": result.reflected_damage > 0,
            "death": CombatLogBuilder._has_event(result, "DEATH"),
        }

    @staticmethod
    def _result_outcome(result: InteractionResultDTO) -> str:
        if CombatLogBuilder._has_event(result, "TICK"):
            return "tick"
        if CombatLogBuilder._has_event(result, "DEATH"):
            return "death"
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
        action_outcome = result.action_facts.get("outcome")
        if action_outcome:
            return str(action_outcome)
        if CombatLogBuilder._has_event(result, "CAST"):
            return "cast"
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

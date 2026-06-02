from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.core.calculators.stats_waterfall_calculator import COMBAT_MATH_VERSION

if TYPE_CHECKING:
    from src.backend.features.combat.dto.action import CombatActionDTO
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO
    from src.backend.features.combat.dto.session import BattleContext


ANALYTICS_SCHEMA_VERSION = 2


class CombatAnalyticsFactBuilder:
    """Build compact machine-readable combat facts. Not used for player-facing text."""

    OUTCOMES = {
        "hit": "H",
        "crit": "C",
        "miss": "M",
        "dodge": "D",
        "parry": "P",
        "block": "B",
        "effect": "E",
        "heal": "R",
        "none": "N",
    }
    STAGES = {"accuracy": "acc", "crit": "crit", "evasion": "eva", "parry": "par", "block": "blk"}
    MODES = {"exchange": "ex", "instant": "in", "item": "it", "system": "sys"}
    EVENTS = {
        "ON_ACCURACY_CHECK": "acc",
        "ON_MISS": "mis",
        "ON_CRIT": "crit",
        "ON_CRIT_FAIL": "crit0",
        "ON_DODGE": "eva",
        "ON_DODGE_FAIL": "eva0",
        "ON_PARRY": "par",
        "ON_PARRY_FAIL": "par0",
        "ON_BLOCK": "blk",
        "ON_BLOCK_FAIL": "blk0",
        "ON_CHECK_CONTROL": "ctl",
        "ON_DAMAGE": "dmg",
    }
    OWNERS = {"source": "s", "target": "d", "self": "self", "other": "o"}
    SOURCES = {
        "weapon": "w",
        "feint": "f",
        "style": "st",
        "effect": "fx",
        "ability": "ab",
        "monster": "m",
        "system": "sys",
    }
    EFFECT_ACTIONS = {"apply": "a", "tick": "t", "expire": "x", "resist": "r", "cleanse": "c"}

    @classmethod
    def build_result_fact(
        cls,
        *,
        ctx: BattleContext,
        result: InteractionResultDTO,
        action: CombatActionDTO,
        wave: int,
        seq: int,
    ) -> dict[str, Any]:
        outcome = cls._outcome(result)
        action_id = cls._action_id(action)
        return {
            "v": ANALYTICS_SCHEMA_VERSION,
            "analytics_schema_version": ANALYTICS_SCHEMA_VERSION,
            "combat_math_version": COMBAT_MATH_VERSION,
            "seq": seq,
            "t": ctx.meta.step_counter + 1,
            "w": wave,
            "s": str(result.source_id) if result.source_id is not None else None,
            "d": str(result.target_id) if result.target_id is not None else None,
            "a": action_id,
            "act": cls._action_fact(action, result),
            "m": cls.MODES.get(action.action_type, action.action_type),
            "o": cls.OUTCOMES.get(outcome, "N"),
            "h": result.hand,
            "dmg": [result.damage_raw, result.damage_mitigated, result.damage_final],
            "heal": result.healing_final,
            "res": cls._resources(result),
            "tok": cls._tokens(result),
            "fx": cls._effects(result),
            "ev": [event.type for event in result.events],
            "chk": [
                [
                    cls.STAGES.get(check.stage, check.stage),
                    round(check.chance, 6),
                    None if check.roll is None else round(check.roll, 6),
                    1 if check.passed else 0,
                    check.details,
                ]
                for check in result.checks
            ],
            "dt": result.damage_trace.model_dump(mode="json") if result.damage_trace else None,
            "trg": list(result.fired_triggers),
            "trga": cls._trigger_attempts(result),
            "tf": cls._trigger_facts(result),
            "mut": cls._mutation_facts(result),
            "chn": cls._chains(result),
            "rf": cls._resource_facts(result),
            "ef": cls._effect_facts(result),
            "df": cls._death_facts(result),
            "x": cls._extras(result),
            "st": cls._stat_slice(ctx, result),
            "eq": cls._equipment_slice_from_context(ctx, result),
        }

    @classmethod
    def build_result_fact_from_support_payload(cls, payload: Any) -> dict[str, Any]:
        from src.backend.features.combat.dto.action import CombatActionDTO
        from src.backend.features.combat.dto.pipeline import InteractionResultDTO

        result = InteractionResultDTO.model_validate(payload.result)
        action = CombatActionDTO.model_validate(payload.action)
        outcome = cls._outcome(result)
        action_id = cls._action_id(action)
        return {
            "v": ANALYTICS_SCHEMA_VERSION,
            "analytics_schema_version": ANALYTICS_SCHEMA_VERSION,
            "combat_math_version": COMBAT_MATH_VERSION,
            "seq": payload.seq,
            "t": payload.global_turn,
            "w": payload.wave,
            "s": str(result.source_id) if result.source_id is not None else None,
            "d": str(result.target_id) if result.target_id is not None else None,
            "a": action_id,
            "act": cls._action_fact(action, result),
            "m": cls.MODES.get(action.action_type, action.action_type),
            "o": cls.OUTCOMES.get(outcome, "N"),
            "h": result.hand,
            "dmg": [result.damage_raw, result.damage_mitigated, result.damage_final],
            "heal": result.healing_final,
            "res": cls._resources(result),
            "tok": cls._tokens(result),
            "fx": cls._effects(result),
            "ev": [event.type for event in result.events],
            "chk": [
                [
                    cls.STAGES.get(check.stage, check.stage),
                    round(check.chance, 6),
                    None if check.roll is None else round(check.roll, 6),
                    1 if check.passed else 0,
                    check.details,
                ]
                for check in result.checks
            ],
            "dt": result.damage_trace.model_dump(mode="json") if result.damage_trace else None,
            "trg": list(result.fired_triggers),
            "trga": cls._trigger_attempts(result),
            "tf": cls._trigger_facts(result),
            "mut": cls._mutation_facts(result),
            "chn": cls._chains(result),
            "rf": cls._resource_facts(result),
            "ef": cls._effect_facts(result),
            "df": cls._death_facts(result),
            "x": cls._extras(result),
            "st": payload.stat_slice,
            "eq": cls._equipment_slice_from_payload(payload, result),
        }

    @classmethod
    def build_session_profile(cls, *, combat_id: str, session_data: Any) -> dict[str, Any]:
        meta = getattr(session_data, "meta", {}) or {}
        actors = getattr(session_data, "actors", {}) or {}
        profile = {
            "v": ANALYTICS_SCHEMA_VERSION,
            "analytics_schema_version": ANALYTICS_SCHEMA_VERSION,
            "combat_math_version": COMBAT_MATH_VERSION,
            "combat_id": str(combat_id),
            "battle_type": meta.get("battle_type"),
            "location_id": meta.get("location_id"),
            "started_at": meta.get("start_time"),
            "actors": {},
        }
        for actor_id, actor in actors.items():
            actor_meta = actor.get("meta") if isinstance(actor, dict) else {}
            actor_raw = actor.get("raw") if isinstance(actor, dict) else {}
            loadout = actor.get("loadout") if isinstance(actor, dict) else {}
            profile["actors"][str(actor_id)] = {
                "meta": {
                    "id": str(actor_id),
                    "name": actor_meta.get("name"),
                    "type": actor_meta.get("type"),
                    "team": actor_meta.get("team"),
                    "template_id": actor_meta.get("template_id"),
                    "archetype": actor_meta.get("archetype"),
                },
                "vitals": {
                    "hp": actor_meta.get("hp"),
                    "max_hp": actor_meta.get("max_hp"),
                    "en": actor_meta.get("en"),
                    "max_en": actor_meta.get("max_en"),
                },
                "attributes": actor_raw.get("attributes", {}) if isinstance(actor_raw, dict) else {},
                "skills": actor.get("skills", {}) if isinstance(actor, dict) else {},
                "loadout": {
                    "layout": loadout.get("layout", {}) if isinstance(loadout, dict) else {},
                    "equipment_layout": loadout.get("equipment_layout", {}) if isinstance(loadout, dict) else {},
                    "weapon_tiers": loadout.get("weapon_tiers", {}) if isinstance(loadout, dict) else {},
                    "combat_surfaces": loadout.get("combat_surfaces", {}) if isinstance(loadout, dict) else {},
                    "equipment_refs": loadout.get("equipment_refs", {}) if isinstance(loadout, dict) else {},
                    "known_feints": loadout.get("known_feints", []) if isinstance(loadout, dict) else [],
                },
            }
        return {
            "v": ANALYTICS_SCHEMA_VERSION,
            "k": "profile",
            "analytics_schema_version": ANALYTICS_SCHEMA_VERSION,
            "combat_math_version": COMBAT_MATH_VERSION,
            "_profile": profile,
        }

    @staticmethod
    def _action_id(action: CombatActionDTO) -> str | None:
        payload = action.move.payload
        for key in ("ability_id", "item_id", "feint_id"):
            value = getattr(payload, key, None)
            if value:
                return str(value)
        return "basic_attack" if action.action_type == "exchange" else None

    @classmethod
    def _action_fact(cls, action: CombatActionDTO, result: InteractionResultDTO) -> dict[str, Any]:
        payload = action.move.payload
        fact = dict(result.action_facts or {})
        fact.setdefault("id", cls._action_id(action))
        for key in ("ability_id", "item_id", "feint_id", "target_id", "hand"):
            value = getattr(payload, key, None)
            if value is not None and value != "":
                fact.setdefault(key, value)
        fact.setdefault("mode", action.action_type)
        return fact

    @classmethod
    def _outcome(cls, result: InteractionResultDTO) -> str:
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

    @staticmethod
    def _resources(result: InteractionResultDTO) -> list[list[Any]]:
        resources: list[list[Any]] = []
        for event in result.events:
            if event.resource and event.value is not None:
                sign = -1 if event.type in {"HIT", "COST"} else 1
                resources.append([str(event.target_id), event.resource, sign * event.value])
        return resources

    @staticmethod
    def _tokens(result: InteractionResultDTO) -> list[list[Any]]:
        tokens: list[list[Any]] = []
        for token, amount in result.tokens_awarded_attacker.items():
            tokens.append(["s", token, amount])
        for token, amount in result.tokens_awarded_defender.items():
            tokens.append(["d", token, amount])
        return tokens

    @staticmethod
    def _effects(result: InteractionResultDTO) -> list[str]:
        effects: list[str] = []
        for effect in result.applied_effects:
            if isinstance(effect, dict):
                effect_id = effect.get("id") or effect.get("effect_id")
                if effect_id:
                    effects.append(str(effect_id))
        return effects

    @classmethod
    def _trigger_facts(cls, result: InteractionResultDTO) -> list[list[Any]]:
        return [
            [
                fact.trigger_id,
                cls.EVENTS.get(fact.event, fact.event),
                cls.SOURCES.get(fact.source, fact.source),
                fact.source_id,
                fact.source_slot,
                round(fact.chance, 6),
                fact.display_policy,
                fact.tags,
            ]
            for fact in result.trigger_facts
        ]

    @classmethod
    def _trigger_attempts(cls, result: InteractionResultDTO) -> list[list[Any]]:
        return [
            [
                fact.trigger_id,
                cls.EVENTS.get(fact.event, fact.event),
                cls.SOURCES.get(fact.source, fact.source),
                fact.source_id,
                fact.source_slot,
                round(fact.chance, 6),
                None if fact.roll is None else round(fact.roll, 6),
                1 if fact.passed else 0,
                fact.display_policy,
                fact.tags,
            ]
            for fact in result.trigger_attempts
        ]

    @classmethod
    def _mutation_facts(cls, result: InteractionResultDTO) -> list[list[Any]]:
        return [
            [
                cls.SOURCES.get(fact.source, fact.source),
                fact.source_id,
                fact.mutation_id,
                fact.path,
                fact.value,
                fact.tags,
            ]
            for fact in result.mutation_facts
        ]

    @staticmethod
    def _chains(result: InteractionResultDTO) -> list[str]:
        chains: list[str] = []
        if result.chain_events.trigger_offhand_attack:
            chains.append("oh")
        if result.chain_events.trigger_counter_attack:
            chains.append("ctr")
        if result.chain_events.trigger_extra_strike:
            chains.append("xs")
        if result.chain_events.preserve_feint:
            chains.append("pf")
        return chains

    @classmethod
    def _resource_facts(cls, result: InteractionResultDTO) -> list[list[Any]]:
        return [
            [
                None if fact.actor_id is None else str(fact.actor_id),
                cls.OWNERS.get(fact.owner, fact.owner),
                fact.resource,
                fact.reason,
                fact.delta,
                fact.before,
                fact.after,
                fact.max,
                fact.tags,
            ]
            for fact in result.resource_facts
        ]

    @classmethod
    def _effect_facts(cls, result: InteractionResultDTO) -> list[list[Any]]:
        return [
            [
                None if fact.actor_id is None else str(fact.actor_id),
                cls.OWNERS.get(fact.owner, fact.owner),
                fact.effect_id,
                cls.EFFECT_ACTIONS.get(fact.action, fact.action),
                fact.value,
                fact.resource,
                fact.duration,
                fact.tags,
            ]
            for fact in result.effect_facts
        ]

    @classmethod
    def _death_facts(cls, result: InteractionResultDTO) -> list[list[Any]]:
        return [
            [
                None if fact.actor_id is None else str(fact.actor_id),
                cls.OWNERS.get(fact.owner, fact.owner),
                fact.reason,
                fact.tags,
            ]
            for fact in result.death_facts
        ]

    @staticmethod
    def _extras(result: InteractionResultDTO) -> dict[str, int]:
        extras: dict[str, int] = {}
        if result.reflected_damage > 0:
            extras["ref"] = result.reflected_damage
        if result.lifesteal_amount > 0:
            extras["ls"] = result.lifesteal_amount
        return extras

    @staticmethod
    def _stat_slice(ctx: BattleContext, result: InteractionResultDTO) -> dict[str, dict[str, float | str]]:
        source = ctx.get_actor(result.source_id) if result.source_id is not None else None
        target = ctx.get_actor(result.target_id) if result.target_id is not None else None
        return {
            "s": CombatAnalyticsFactBuilder._actor_stats(source),
            "d": CombatAnalyticsFactBuilder._actor_stats(target),
        }

    @staticmethod
    def _actor_stats(actor: Any) -> dict[str, float | str]:
        if actor is None or actor.stats is None:
            return {}
        mods = actor.stats.mods
        skills = actor.stats.skills
        evasion = min(float(mods.evasion), float(mods.dodge_cap))
        return {
            "acc": mods.accuracy,
            "crit": mods.crit_chance,
            "eva": evasion,
            "par": mods.parry,
            "blk": mods.block,
            "arm": mods.armor,
            "sup": mods.physical_suppression,
            "ap": mods.armor_penetration_pct,
            "sp": skills.skill_parrying,
        }

    @staticmethod
    def _equipment_slice_from_context(ctx: BattleContext, result: InteractionResultDTO) -> dict[str, Any]:
        source = ctx.get_actor(result.source_id) if result.source_id is not None else None
        target = ctx.get_actor(result.target_id) if result.target_id is not None else None
        return CombatAnalyticsFactBuilder._equipment_slice(
            getattr(getattr(source, "loadout", None), "equipment_refs", {}) if source else {},
            getattr(getattr(target, "loadout", None), "equipment_refs", {}) if target else {},
            result.hand,
        )

    @staticmethod
    def _equipment_slice_from_payload(payload: Any, result: InteractionResultDTO) -> dict[str, Any]:
        source = payload.actors.get(str(result.source_id)) if result.source_id is not None else None
        target = payload.actors.get(str(result.target_id)) if result.target_id is not None else None
        source_refs = getattr(source, "loadout", {}).get("equipment_refs", {}) if source else {}
        target_refs = getattr(target, "loadout", {}).get("equipment_refs", {}) if target else {}
        return CombatAnalyticsFactBuilder._equipment_slice(source_refs, target_refs, result.hand)

    @staticmethod
    def _equipment_slice(source_refs: Any, target_refs: Any, hand: str) -> dict[str, Any]:
        source_refs = source_refs or {}
        target_refs = target_refs or {}
        source_slot = "off_hand" if hand in {"off", "off_hand"} else "main_hand"
        source_weapon = CombatAnalyticsFactBuilder._dump_equipment_ref(source_refs.get(source_slot))
        target_armor = CombatAnalyticsFactBuilder._dump_equipment_ref(
            target_refs.get("body") or target_refs.get("chest_armor")
        )
        return {
            "s": {"weapon": source_weapon},
            "d": {"armor": target_armor},
        }

    @staticmethod
    def _dump_equipment_ref(value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="json")
        if not isinstance(value, dict):
            return {}
        return {
            "item_id": value.get("item_id"),
            "base_id": value.get("base_id"),
            "item_type": value.get("item_type"),
            "tier": value.get("combat_tier", value.get("tier")),
            "power": value.get("power"),
            "armor_class": value.get("armor_class"),
            "skill_key": value.get("skill_key"),
            "triggers": value.get("triggers", []),
            "tags": value.get("tags", []),
        }

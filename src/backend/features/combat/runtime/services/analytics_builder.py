from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.features.combat.dto.action import CombatActionDTO
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO
    from src.backend.features.combat.dto.session import BattleContext


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
            "v": 1,
            "seq": seq,
            "t": ctx.meta.step_counter + 1,
            "w": wave,
            "s": str(result.source_id) if result.source_id is not None else None,
            "d": str(result.target_id) if result.target_id is not None else None,
            "a": action_id,
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
            "st": cls._stat_slice(ctx, result),
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
        return {
            "acc": mods.accuracy,
            "crit": mods.crit_chance,
            "eva": mods.evasion,
            "par": mods.parry,
            "blk": mods.block,
            "arm": mods.armor,
            "pen": mods.armor_penetration,
            "sp": skills.skill_parrying,
        }

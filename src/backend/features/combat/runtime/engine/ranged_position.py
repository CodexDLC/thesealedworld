from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.backend.features.combat.dto.actor import ActiveEffectDTO, ActorSnapshot, ActorStats
from src.backend.features.combat.dto.pipeline import CombatEffectFactDTO, InteractionResultDTO, PipelineContextDTO
from src.backend.features.combat.runtime.engine.math_core import MathCore
from src.backend.features.combat.runtime.engine.tunables import current_tunables

RANGED_POSITION_EFFECT_ID = "ranged_position"
RangedPosition = Literal["far", "mid", "close"]
RANGED_POSITIONS: tuple[RangedPosition, ...] = ("far", "mid", "close")
POSITION_RANK: dict[RangedPosition, int] = {"close": 0, "mid": 1, "far": 2}
POSITION_BY_RANK: dict[int, RangedPosition] = {rank: position for position, rank in POSITION_RANK.items()}

OUTGOING_DAMAGE_MULT: dict[RangedPosition, float] = {"far": 1.08, "mid": 1.0, "close": 0.70}
OUTGOING_ACCURACY_MULT: dict[RangedPosition, float] = {"far": 1.05, "mid": 1.0, "close": 0.85}
INCOMING_MELEE_DAMAGE_MULT: dict[RangedPosition, float] = {"far": 0.70, "mid": 1.05, "close": 1.30}
DAMAGE_PRESSURE_THREAT_MULT: dict[RangedPosition, float] = {"far": 3.0, "mid": 1.25, "close": 1.0}

AVOID_CAP_BASE: dict[RangedPosition, float] = {"far": 0.65, "mid": 0.50, "close": 0.35}
AVOID_CAP_SKILL: dict[RangedPosition, float] = {"far": 0.30, "mid": 0.20, "close": 0.15}
AVOID_EVASION_WEIGHT: dict[RangedPosition, float] = {"far": 0.75, "mid": 0.60, "close": 0.45}
AVOID_LINE_WEIGHT: dict[RangedPosition, float] = {"far": 0.25, "mid": 0.35, "close": 0.30}

INITIATIVE_DIVISOR = 50.0
DAMAGE_PRESSURE_DIVISOR = 0.35
MELEE_CONTACT_PRESSURE_DIVISOR = 1.0


@dataclass(frozen=True, slots=True)
class PositionWeights:
    far: float
    mid: float
    close: float


class RangedPositionService:
    """Runtime helpers for the archer distance-state combat style."""

    @staticmethod
    def is_ranged_actor(actor: ActorSnapshot | None) -> bool:
        if actor is None:
            return False
        return actor.loadout.layout.get("tactical_style") == "skill_ranged_combat"

    @staticmethod
    def current_position(actor: ActorSnapshot) -> RangedPosition:
        current_exchange = actor.meta.exchange_counter
        for effect in actor.statuses.effects:
            if effect.effect_id != RANGED_POSITION_EFFECT_ID:
                continue
            if current_exchange < int(effect.active_from_exchange or 0):
                continue
            if current_exchange >= int(effect.expire_at_exchange or 0):
                continue
            return RangedPositionService.normalize_position(effect.params.get("position"))
        return "far"

    @staticmethod
    def normalize_position(value: object) -> RangedPosition:
        return value if value in RANGED_POSITIONS else "far"  # type: ignore[return-value]

    @staticmethod
    def improve_position(position: RangedPosition, steps: int) -> RangedPosition:
        rank = POSITION_RANK[position]
        return POSITION_BY_RANK[max(0, min(2, rank + int(steps)))]

    @staticmethod
    def at_least_position(position: RangedPosition, minimum: RangedPosition) -> RangedPosition:
        if POSITION_RANK[position] >= POSITION_RANK[minimum]:
            return position
        return minimum

    @staticmethod
    def apply_source_context(ctx: PipelineContextDTO, source: ActorSnapshot) -> None:
        if not RangedPositionService.is_ranged_actor(source):
            return
        position = RangedPositionService.current_position(source)
        ctx.flags.meta.source_ranged_position = position
        if ctx.flags.meta.source_type == "main_hand" and ctx.flags.meta.weapon_class == "archery":
            ctx.mods.accuracy_mult *= OUTGOING_ACCURACY_MULT[position]

    @staticmethod
    def apply_target_context(ctx: PipelineContextDTO, target: ActorSnapshot) -> None:
        if not RangedPositionService.is_ranged_actor(target):
            return
        ctx.flags.meta.target_tactical_style_skill = "skill_ranged_combat"
        ctx.flags.meta.target_ranged_position = RangedPositionService.current_position(target)
        ctx.stages.check_evasion = False
        ctx.stages.check_parry = False
        ctx.stages.check_block = False
        ctx.stages.check_ranged_position_defense = True
        ctx.flags.restriction.disable_passive_counter = True

    @staticmethod
    def apply_action_position_context(ctx: PipelineContextDTO) -> None:
        if not RangedPositionService.archer_bow_attack_applies(ctx):
            return

        position = RangedPositionService.normalize_position(ctx.flags.meta.source_ranged_position)
        original = position
        step = ctx.result.action_facts.get("ranged_current_position_step")
        if step is not None:
            position = RangedPositionService.improve_position(position, int(step))

        minimum = ctx.result.action_facts.get("ranged_current_position_min")
        if minimum is not None:
            position = RangedPositionService.at_least_position(
                position, RangedPositionService.normalize_position(minimum)
            )

        if position != original:
            ctx.mods.accuracy_mult *= OUTGOING_ACCURACY_MULT[position] / OUTGOING_ACCURACY_MULT[original]
            ctx.flags.meta.source_ranged_position = position
            ctx.result.action_facts["ranged_current_position_applied"] = position

        accuracy_bonus = float(ctx.result.action_facts.get("ranged_outgoing_accuracy_bonus_mult", 1.0) or 1.0)
        ctx.mods.accuracy_mult *= max(0.0, accuracy_bonus)

    @staticmethod
    def is_physical_melee_attack(ctx: PipelineContextDTO) -> bool:
        return (
            ctx.flags.damage.physical
            and ctx.flags.meta.source_type in {"main_hand", "off_hand"}
            and ctx.flags.meta.weapon_class != "archery"
        )

    @staticmethod
    def archer_bow_attack_applies(ctx: PipelineContextDTO) -> bool:
        return (
            ctx.flags.damage.physical
            and ctx.flags.meta.source_type == "main_hand"
            and ctx.flags.meta.weapon_class == "archery"
            and ctx.flags.meta.tactical_style_skill == "skill_ranged_combat"
        )

    @staticmethod
    def target_defense_applies(ctx: PipelineContextDTO) -> bool:
        return (
            ctx.flags.meta.target_tactical_style_skill == "skill_ranged_combat"
            and RangedPositionService.is_physical_melee_attack(ctx)
        )

    @staticmethod
    def source_counter_reachable(ctx: PipelineContextDTO) -> bool:
        if ctx.flags.meta.tactical_style_skill != "skill_ranged_combat":
            return True
        return RangedPositionService.normalize_position(ctx.flags.meta.source_ranged_position) == "close"

    @staticmethod
    def ranged_avoid_chance(
        atk: ActorStats, def_: ActorStats, ctx: PipelineContextDTO
    ) -> tuple[float, dict[str, float]]:
        position = RangedPositionService.normalize_position(ctx.flags.meta.target_ranged_position)
        ranged_skill = max(0.0, min(1.0, float(def_.skills.skill_ranged_combat or 0.0)))
        evasion = max(0.0, float(def_.mods.evasion or 0.0) - max(0.0, float(atk.mods.anti_dodge_chance or 0.0)))
        parry_skill_mult = 1.0 + (current_tunables().parry_skill_mult_per_point * def_.skills.skill_parrying)
        line_control = max(0.0, float(def_.mods.parry or 0.0) * parry_skill_mult)
        cap = AVOID_CAP_BASE[position] + (AVOID_CAP_SKILL[position] * ranged_skill)
        raw = (
            evasion * AVOID_EVASION_WEIGHT[position] + line_control * AVOID_LINE_WEIGHT[position] + ranged_skill * 0.20
        )
        chance = max(0.0, min(cap, raw))
        return chance, {
            "position": position,
            "evasion": evasion,
            "line_control": line_control,
            "skill_ranged_combat": ranged_skill,
            "cap": cap,
        }

    @staticmethod
    def update_after_exchange(
        pairs: list[tuple[ActorSnapshot, ActorSnapshot | None, InteractionResultDTO]],
    ) -> None:
        by_actor: dict[str, tuple[ActorSnapshot, ActorSnapshot | None, InteractionResultDTO]] = {}
        incoming_damage: dict[str, int] = {}
        incoming_melee_pressure: dict[str, int] = {}
        for source, target, result in pairs:
            if RangedPositionService.is_ranged_actor(source):
                by_actor[str(source.char_id)] = (source, target, result)
            if target and RangedPositionService.is_ranged_actor(target):
                target_key = str(target.char_id)
                incoming_damage[target_key] = incoming_damage.get(target_key, 0) + max(0, int(result.damage_final or 0))
                if RangedPositionService._has_ranged_position_melee_contact(result):
                    incoming_melee_pressure[target_key] = incoming_melee_pressure.get(target_key, 0) + 1

        for actor_key, (archer, enemy, result) in by_actor.items():
            if not enemy:
                continue
            override = result.action_facts.get("next_ranged_position_override")
            position = (
                RangedPositionService.normalize_position(override)
                if override
                else RangedPositionService.roll_next_position(
                    archer=archer,
                    enemy=enemy,
                    damage_taken=incoming_damage.get(actor_key, 0),
                    melee_pressure=incoming_melee_pressure.get(actor_key, 0),
                    action_facts=result.action_facts,
                )
            )
            minimum = result.action_facts.get("next_ranged_position_min")
            if minimum:
                position = RangedPositionService.at_least_position(
                    position, RangedPositionService.normalize_position(minimum)
                )
            RangedPositionService.set_next_position(archer, position, result)

    @staticmethod
    def roll_next_position(
        *,
        archer: ActorSnapshot,
        enemy: ActorSnapshot,
        damage_taken: int,
        melee_pressure: int = 0,
        action_facts: dict[str, object] | None = None,
    ) -> RangedPosition:
        weights = RangedPositionService.position_weights(
            archer=archer,
            enemy=enemy,
            damage_taken=damage_taken,
            melee_pressure=melee_pressure,
            action_facts=action_facts,
        )
        total = max(0.0, weights.far) + max(0.0, weights.mid) + max(0.0, weights.close)
        if total <= 0:
            return "mid"
        roll = MathCore.random_range(0.0, total)
        if roll <= max(0.0, weights.far):
            return "far"
        roll -= max(0.0, weights.far)
        if roll <= max(0.0, weights.mid):
            return "mid"
        return "close"

    @staticmethod
    def position_weights(
        *,
        archer: ActorSnapshot,
        enemy: ActorSnapshot,
        damage_taken: int,
        melee_pressure: int = 0,
        action_facts: dict[str, object] | None = None,
    ) -> PositionWeights:
        action_facts = action_facts or {}
        archer_stats = archer.stats or ActorStats()
        enemy_stats = enemy.stats or ActorStats()
        current = RangedPositionService.current_position(archer)
        ranged_skill = max(0.0, min(1.0, float(archer_stats.skills.skill_ranged_combat or 0.0)))
        evasion = max(0.0, float(archer_stats.mods.evasion or 0.0))
        parry_skill_mult = 1.0 + (current_tunables().parry_skill_mult_per_point * archer_stats.skills.skill_parrying)
        line_control = max(0.0, float(archer_stats.mods.parry or 0.0) * parry_skill_mult)
        tempo = RangedPositionService._clamp(
            (float(archer_stats.mods.initiative or 0.0) - float(enemy_stats.mods.initiative or 0.0))
            / INITIATIVE_DIVISOR,
            -1.0,
            1.0,
        )
        max_hp = max(1, int(archer.meta.max_hp or 1))
        damage_pressure = RangedPositionService._clamp(
            (max(0, int(damage_taken)) / max_hp) / DAMAGE_PRESSURE_DIVISOR,
            0.0,
            1.0,
        )
        damage_pressure *= DAMAGE_PRESSURE_THREAT_MULT[current]
        damage_pressure *= max(0.0, float(action_facts.get("ranged_damage_pressure_mult", 1.0) or 1.0))
        melee_contact_pressure = RangedPositionService._clamp(
            max(0, int(melee_pressure)) / MELEE_CONTACT_PRESSURE_DIVISOR,
            0.0,
            1.0,
        )
        melee_contact_pressure *= max(0.0, float(action_facts.get("ranged_melee_pressure_mult", 1.0) or 1.0))
        melee_contact_resistance = max(0.25, 1.0 - (0.65 * ranged_skill))
        enemy_pressure = max(0.0, float(enemy_stats.mods.anti_dodge_chance or 0.0))
        enemy_pressure *= max(0.0, float(action_facts.get("ranged_enemy_pressure_mult", 1.0) or 1.0))

        far = 0.05 + (0.40 * ranged_skill) + (0.15 * evasion) + (0.18 * max(tempo, 0.0))
        far -= (0.45 * damage_pressure) + (0.18 * max(-tempo, 0.0)) + (0.20 * enemy_pressure)
        far -= 0.55 * melee_contact_pressure * melee_contact_resistance
        mid = 0.62 + (0.06 * ranged_skill) + (0.30 * line_control) + (0.12 * damage_pressure)
        mid += 0.22 * melee_contact_pressure
        close = 0.45 + (0.25 * max(-tempo, 0.0)) + (0.42 * damage_pressure) + (0.20 * enemy_pressure)
        close += 0.45 * melee_contact_pressure * melee_contact_resistance
        close -= (0.22 * ranged_skill) + (0.10 * evasion)

        if current == "far":
            far += 0.04 + (0.10 * ranged_skill)
            mid += 0.10
            close -= 0.05 * ranged_skill
        elif current == "mid":
            mid += 0.15
        else:
            close += 0.18
            mid += 0.15
            far -= 0.16 * (1.0 - (0.50 * ranged_skill))

        far += float(action_facts.get("ranged_far_weight_bonus", 0.0) or 0.0)
        mid += float(action_facts.get("ranged_mid_weight_bonus", 0.0) or 0.0)
        close += float(action_facts.get("ranged_close_weight_bonus", 0.0) or 0.0)
        if melee_contact_pressure > 0.0:
            close = max(close, 0.10 * melee_contact_pressure)

        return PositionWeights(far=max(0.01, far), mid=max(0.01, mid), close=max(0.01, close))

    @staticmethod
    def set_next_position(archer: ActorSnapshot, position: RangedPosition, result: InteractionResultDTO) -> None:
        active_from = archer.meta.exchange_counter + 1
        expire_at = active_from + 1
        archer.statuses.effects = [
            effect for effect in archer.statuses.effects if effect.effect_id != RANGED_POSITION_EFFECT_ID
        ]
        effect = ActiveEffectDTO(
            uid=f"{RANGED_POSITION_EFFECT_ID}:{archer.char_id}:{active_from}",
            effect_id=RANGED_POSITION_EFFECT_ID,
            source_id=archer.char_id,
            active_from_exchange=active_from,
            expire_at_exchange=expire_at,
            params={"position": position},
        )
        archer.statuses.effects.append(effect)
        result.effect_facts.append(
            CombatEffectFactDTO(
                actor_id=archer.char_id,
                owner="source" if str(result.source_id) == str(archer.char_id) else "target",
                effect_id=RANGED_POSITION_EFFECT_ID,
                action="apply",
                duration=1,
                source_effect_id=RANGED_POSITION_EFFECT_ID,
                tags=["ranged_combat", "position", position],
            )
        )

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    @staticmethod
    def _has_ranged_position_melee_contact(result: InteractionResultDTO) -> bool:
        for check in result.checks:
            stage = check.get("stage") if isinstance(check, dict) else getattr(check, "stage", None)
            if str(stage or "") == "ranged_position_defense":
                return True
        if result.damage_trace is None:
            return False
        details = result.damage_trace.details
        return details.get("ranged_position_target") in RANGED_POSITIONS

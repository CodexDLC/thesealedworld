"""In-memory combat telemetry for simulation and training runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.features.combat.dto.action import CombatMoveDTO
    from src.backend.features.combat.dto.session import BattleContext


@dataclass
class CombatTelemetry:
    """Aggregate facts collected from simulated moves and executor output."""

    action_count: int = 0
    failed_action_count: int = 0
    feint_pick_count: dict[str, int] = field(default_factory=dict)
    damage_by_actor: dict[str, int] = field(default_factory=dict)
    damage_taken_by_actor: dict[str, int] = field(default_factory=dict)
    armor_absorbed_by_actor: dict[str, int] = field(default_factory=dict)
    armor_absorb_events_by_actor: dict[str, int] = field(default_factory=dict)
    healing_by_actor: dict[str, int] = field(default_factory=dict)
    resource_spent_by_actor: dict[str, int] = field(default_factory=dict)
    action_count_by_actor: dict[str, int] = field(default_factory=dict)
    target_count_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    targeted_by_actor: dict[str, int] = field(default_factory=dict)
    damage_events_by_actor: dict[str, int] = field(default_factory=dict)
    incoming_events_by_actor: dict[str, int] = field(default_factory=dict)
    hit_by_actor: dict[str, int] = field(default_factory=dict)
    miss_by_actor: dict[str, int] = field(default_factory=dict)
    dodge_by_actor: dict[str, int] = field(default_factory=dict)
    parry_by_actor: dict[str, int] = field(default_factory=dict)
    block_by_actor: dict[str, int] = field(default_factory=dict)
    crit_by_actor: dict[str, int] = field(default_factory=dict)
    failed_by_actor: dict[str, int] = field(default_factory=dict)
    overkill_by_actor: dict[str, int] = field(default_factory=dict)
    overkill_taken_by_actor: dict[str, int] = field(default_factory=dict)
    tactical_trigger_attempts_by_id: dict[str, int] = field(default_factory=dict)
    tactical_trigger_success_by_id: dict[str, int] = field(default_factory=dict)
    tactical_trigger_attempts_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    tactical_trigger_success_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    tactical_damage_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    tactical_reflected_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    tactical_prevented_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    tactical_chain_attempts_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    tactical_chain_hits_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    tactical_shield_branch_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    tactical_shield_damage_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    tactical_shield_absorbed_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    tactical_shield_reflected_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    ranged_position_outgoing_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    ranged_position_incoming_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    ranged_position_defense_attempts_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    ranged_position_defense_success_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    ranged_position_outgoing_damage_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    ranged_position_incoming_damage_by_actor: dict[str, dict[str, int]] = field(default_factory=dict)
    hit_count: int = 0
    miss_count: int = 0
    dodge_count: int = 0
    parry_count: int = 0
    block_count: int = 0
    crit_count: int = 0
    deaths: list[str] = field(default_factory=list)
    round_events: list[dict[str, Any]] = field(default_factory=list)
    control_applied: int = 0
    buff_applied: int = 0
    log_count: int = 0

    def record_moves(self, moves: list[CombatMoveDTO]) -> None:
        self.action_count += len(moves)
        for move in moves:
            actor_id = str(move.char_id)
            self.action_count_by_actor[actor_id] = self.action_count_by_actor.get(actor_id, 0) + 1
            target_id = getattr(move.payload, "target_id", None)
            if target_id is not None:
                target_key = str(target_id)
                target_counts = self.target_count_by_actor.setdefault(actor_id, {})
                target_counts[target_key] = target_counts.get(target_key, 0) + 1
                self.targeted_by_actor[target_key] = self.targeted_by_actor.get(target_key, 0) + 1
            feint_id = getattr(move.payload, "feint_id", None)
            if feint_id:
                self.feint_pick_count[str(feint_id)] = self.feint_pick_count.get(str(feint_id), 0) + 1

    def record_executor_context(self, ctx: BattleContext, *, round_index: int | None = None) -> None:
        self.log_count += len(ctx.pending_logs)
        for payload in ctx.pending_result_support_tasks:
            result = payload.get("result") if isinstance(payload, dict) else None
            actors = payload.get("actors") if isinstance(payload, dict) else None
            if isinstance(result, dict):
                self._record_result(result, actors=self._dict(actors), round_index=round_index)
        for actor_id in ctx.pending_dead_actors:
            self._record_death(str(actor_id))

    def _record_result(
        self,
        result: dict[str, Any],
        *,
        actors: dict[str, Any] | None = None,
        round_index: int | None = None,
    ) -> None:
        source_id = self._string_or_none(result.get("source_id"))
        target_id = self._string_or_none(result.get("target_id"))
        damage = self._int(result.get("damage_final"))
        if source_id and damage > 0:
            self.damage_by_actor[source_id] = self.damage_by_actor.get(source_id, 0) + damage
            self.damage_events_by_actor[source_id] = self.damage_events_by_actor.get(source_id, 0) + 1
        if target_id and damage > 0:
            self.damage_taken_by_actor[target_id] = self.damage_taken_by_actor.get(target_id, 0) + damage
        if target_id and source_id:
            self.incoming_events_by_actor[target_id] = self.incoming_events_by_actor.get(target_id, 0) + 1
        armor_absorbed = self._armor_absorbed(result)
        if target_id and armor_absorbed > 0:
            self.armor_absorbed_by_actor[target_id] = self.armor_absorbed_by_actor.get(target_id, 0) + armor_absorbed
            self.armor_absorb_events_by_actor[target_id] = self.armor_absorb_events_by_actor.get(target_id, 0) + 1

        healing = self._int(result.get("healing_final"))
        if source_id and healing > 0:
            self.healing_by_actor[source_id] = self.healing_by_actor.get(source_id, 0) + healing

        if result.get("skip_reason"):
            self.failed_action_count += 1
            if source_id:
                self.failed_by_actor[source_id] = self.failed_by_actor.get(source_id, 0) + 1
        if result.get("is_hit"):
            self.hit_count += 1
            if source_id:
                self.hit_by_actor[source_id] = self.hit_by_actor.get(source_id, 0) + 1
        if result.get("is_miss"):
            self.miss_count += 1
            if source_id:
                self.miss_by_actor[source_id] = self.miss_by_actor.get(source_id, 0) + 1
        ranged_position_dodged = self._has_successful_ranged_position_defense(result)
        if result.get("is_dodged") or ranged_position_dodged:
            self.dodge_count += 1
            if target_id:
                self.dodge_by_actor[target_id] = self.dodge_by_actor.get(target_id, 0) + 1
        if result.get("is_parried"):
            self.parry_count += 1
            if target_id:
                self.parry_by_actor[target_id] = self.parry_by_actor.get(target_id, 0) + 1
        if result.get("is_blocked"):
            self.block_count += 1
            if target_id:
                self.block_by_actor[target_id] = self.block_by_actor.get(target_id, 0) + 1
        if result.get("is_crit"):
            self.crit_count += 1
            if source_id:
                self.crit_by_actor[source_id] = self.crit_by_actor.get(source_id, 0) + 1

        self._record_tactical_result(
            result, actors=actors or {}, source_id=source_id, target_id=target_id, damage=damage
        )
        self._record_ranged_position_result(result, source_id=source_id, target_id=target_id, damage=damage)

        for fact in self._list_of_dicts(result.get("resource_facts")):
            self._record_overkill_fact(fact, source_id=source_id, target_id=target_id, damage=damage)
            self._record_resource_fact(fact)
        for fact in self._list_of_dicts(result.get("effect_facts")):
            self._record_effect_fact(fact)
        deaths: list[str] = []
        for fact in self._list_of_dicts(result.get("death_facts")):
            actor_id = self._string_or_none(fact.get("actor_id"))
            if actor_id:
                self._record_death(actor_id)
                deaths.append(actor_id)

        if source_id or target_id or damage or armor_absorbed or healing or result.get("skip_reason"):
            self.round_events.append(
                {
                    "round": round_index,
                    "source_id": source_id,
                    "target_id": target_id,
                    "damage": damage,
                    "armor_absorbed": armor_absorbed,
                    "healing": healing,
                    "is_hit": bool(result.get("is_hit")),
                    "is_miss": bool(result.get("is_miss")),
                    "is_dodged": bool(result.get("is_dodged")),
                    "is_parried": bool(result.get("is_parried")),
                    "is_blocked": bool(result.get("is_blocked")),
                    "is_crit": bool(result.get("is_crit")),
                    "skip_reason": self._string_or_none(result.get("skip_reason")),
                    "deaths": deaths,
                }
            )

    def _record_ranged_position_result(
        self,
        result: dict[str, Any],
        *,
        source_id: str | None,
        target_id: str | None,
        damage: int,
    ) -> None:
        for check in self._list_of_dicts(result.get("checks")):
            if str(check.get("stage") or "") != "ranged_position_defense" or not target_id:
                continue
            position = self._ranged_position_or_none(self._dict(check.get("details")).get("position"))
            if position is None:
                continue
            self._increment_nested(self.ranged_position_defense_attempts_by_actor, target_id, position)
            if bool(check.get("passed")):
                self._increment_nested(self.ranged_position_defense_success_by_actor, target_id, position)

        details = self._damage_trace_details(result)
        source_position = self._ranged_position_or_none(details.get("ranged_position_source"))
        if source_id and source_position:
            self._increment_nested(self.ranged_position_outgoing_by_actor, source_id, source_position)
            if damage > 0:
                self._increment_nested(
                    self.ranged_position_outgoing_damage_by_actor, source_id, source_position, damage
                )

        target_position = self._ranged_position_or_none(details.get("ranged_position_target"))
        if target_id and target_position:
            self._increment_nested(self.ranged_position_incoming_by_actor, target_id, target_position)
            if damage > 0:
                self._increment_nested(
                    self.ranged_position_incoming_damage_by_actor, target_id, target_position, damage
                )

    def _has_successful_ranged_position_defense(self, result: dict[str, Any]) -> bool:
        for check in self._list_of_dicts(result.get("checks")):
            if str(check.get("stage") or "") == "ranged_position_defense" and bool(check.get("passed")):
                return True
        return False

    def _record_resource_fact(self, fact: dict[str, Any]) -> None:
        actor_id = self._string_or_none(fact.get("actor_id"))
        delta = self._int(fact.get("delta"))
        resource = str(fact.get("resource") or "")
        if not actor_id or delta >= 0 or resource == "hp":
            return
        self.resource_spent_by_actor[actor_id] = self.resource_spent_by_actor.get(actor_id, 0) + abs(delta)

    def _record_overkill_fact(
        self,
        fact: dict[str, Any],
        *,
        source_id: str | None,
        target_id: str | None,
        damage: int,
    ) -> None:
        if not source_id or not target_id or damage <= 0:
            return
        actor_id = self._string_or_none(fact.get("actor_id"))
        resource = str(fact.get("resource") or "")
        reason = str(fact.get("reason") or "")
        owner = str(fact.get("owner") or "")
        if actor_id != target_id or resource != "hp" or reason != "damage" or owner != "target":
            return
        applied_damage = abs(self._int(fact.get("delta")))
        overkill = max(0, damage - applied_damage)
        if overkill <= 0:
            return
        self.overkill_by_actor[source_id] = self.overkill_by_actor.get(source_id, 0) + overkill
        self.overkill_taken_by_actor[target_id] = self.overkill_taken_by_actor.get(target_id, 0) + overkill

    def _record_effect_fact(self, fact: dict[str, Any]) -> None:
        if fact.get("action") != "apply":
            return
        tags = {str(tag) for tag in fact.get("tags") or []}
        effect_id = str(fact.get("effect_id") or "")
        if "control" in tags or "stun" in effect_id or "control" in effect_id:
            self.control_applied += 1
        elif "buff" in tags or effect_id.startswith(("buff_", "prep_")):
            self.buff_applied += 1

    def _record_tactical_result(
        self,
        result: dict[str, Any],
        *,
        actors: dict[str, Any],
        source_id: str | None,
        target_id: str | None,
        damage: int,
    ) -> None:
        for attempt in self._list_of_dicts(result.get("trigger_attempts")):
            trigger_id = self._string_or_none(attempt.get("trigger_id"))
            if not trigger_id or not self._is_tactical_trigger(trigger_id):
                continue
            owner_id = self._tactical_owner_id(trigger_id, source_id=source_id, target_id=target_id)
            self._increment(self.tactical_trigger_attempts_by_id, trigger_id)
            if owner_id:
                self._increment_nested(self.tactical_trigger_attempts_by_actor, owner_id, trigger_id)
            if bool(attempt.get("passed")):
                self._increment(self.tactical_trigger_success_by_id, trigger_id)
                if owner_id:
                    self._increment_nested(self.tactical_trigger_success_by_actor, owner_id, trigger_id)
                    if damage > 0 and trigger_id == "style_2h_ignore":
                        self._increment_nested(self.tactical_damage_by_actor, owner_id, trigger_id, damage)
                    if damage > 0 and trigger_id == "style_dual_cross_cut":
                        self._increment_nested(self.tactical_damage_by_actor, owner_id, trigger_id, damage)
                    if trigger_id == "style_ranged_perfect_backstep":
                        ranged_punish_damage = self._int(result.get("ranged_punish_damage"))
                        if ranged_punish_damage > 0:
                            self._increment_nested(
                                self.tactical_damage_by_actor,
                                owner_id,
                                trigger_id,
                                ranged_punish_damage,
                            )
                        prevented = self._prevented_damage_estimate(
                            result,
                            source_actor=actors.get(str(source_id)) if source_id else None,
                        )
                        if prevented > 0:
                            self._increment_nested(self.tactical_prevented_by_actor, owner_id, trigger_id, prevented)

        shield_branch = self._shield_branch(result)
        if result.get("is_blocked") and target_id and shield_branch:
            self._increment_nested(self.tactical_shield_branch_by_actor, target_id, shield_branch)

        reflected_damage = self._int(result.get("reflected_damage"))
        if reflected_damage > 0 and target_id:
            self._increment_nested(
                self.tactical_reflected_by_actor, target_id, "style_shield_reflect", reflected_damage
            )
            self._increment_nested(
                self.tactical_shield_reflected_by_actor,
                target_id,
                "style_shield_reflect",
                reflected_damage,
            )

        shield_absorb = self._shield_absorbed(result)
        if shield_absorb > 0 and target_id:
            self._increment_nested(self.tactical_prevented_by_actor, target_id, "style_shield_reflect", shield_absorb)
            self._increment_nested(
                self.tactical_shield_absorbed_by_actor,
                target_id,
                "style_shield_reflect",
                shield_absorb,
            )

        if result.get("is_counter") and source_id:
            self._increment_nested(self.tactical_chain_attempts_by_actor, source_id, "counter_attack")
            if damage > 0:
                self._increment_nested(self.tactical_damage_by_actor, source_id, "counter_attack", damage)
                self._increment_nested(self.tactical_chain_hits_by_actor, source_id, "counter_attack")

        if str(result.get("hand") or "") in {"off", "off_hand"} and source_id:
            tactical_id = self._offhand_tactical_id(actors.get(source_id))
            self._increment_nested(self.tactical_chain_attempts_by_actor, source_id, tactical_id)
            if damage > 0:
                self._increment_nested(self.tactical_damage_by_actor, source_id, tactical_id, damage)
                self._increment_nested(self.tactical_chain_hits_by_actor, source_id, tactical_id)
                if tactical_id == "weapon_shield_bash_on_block":
                    self._increment_nested(self.tactical_shield_damage_by_actor, source_id, tactical_id, damage)

        if self._is_shield_damage_feint(result) and source_id and damage > 0:
            self._increment_nested(
                self.tactical_damage_by_actor,
                source_id,
                "weapon_shield_bash_on_block",
                damage,
            )
            self._increment_nested(
                self.tactical_shield_damage_by_actor,
                source_id,
                "weapon_shield_bash_on_block",
                damage,
            )

    @staticmethod
    def _is_tactical_trigger(trigger_id: str) -> bool:
        return trigger_id in {
            "style_2h_ignore",
            "style_shield_reflect",
            "style_ranged_perfect_backstep",
            "style_dual_cross_cut",
            "weapon_shield_bash_on_block",
            "weapon_riposte_on_parry",
        }

    @staticmethod
    def _tactical_owner_id(trigger_id: str, *, source_id: str | None, target_id: str | None) -> str | None:
        if trigger_id in {
            "style_shield_reflect",
            "style_ranged_perfect_backstep",
            "weapon_shield_bash_on_block",
            "weapon_riposte_on_parry",
        }:
            return target_id
        return source_id

    @classmethod
    def _offhand_tactical_id(cls, actor: Any) -> str:
        actor_data = cls._dict(actor)
        loadout = cls._dict(actor_data.get("loadout"))
        layout = cls._dict(loadout.get("layout"))
        if layout.get("off_hand") == "skill_shield_mastery":
            return "weapon_shield_bash_on_block"
        return "offhand_attack"

    def _record_death(self, actor_id: str) -> None:
        if actor_id not in self.deaths:
            self.deaths.append(actor_id)

    @classmethod
    def _armor_absorbed(cls, result: dict[str, Any]) -> int:
        damage_trace = result.get("damage_trace")
        if not isinstance(damage_trace, dict):
            return 0
        details = damage_trace.get("details")
        if not isinstance(details, dict):
            return 0
        armor = details.get("arm")
        if isinstance(armor, dict):
            effective = cls._float(armor.get("effective"))
            if effective > 0:
                after_resist = cls._float(details.get("after_resist"))
                absorbed = min(effective, after_resist) if after_resist > 0 else effective
                return int(round(absorbed))
        after_resist = cls._float(details.get("after_resist"))
        after_armor = cls._float(details.get("after_armor"))
        return max(0, int(round(after_resist - after_armor)))

    @classmethod
    def _shield_absorbed(cls, result: dict[str, Any]) -> int:
        details = cls._damage_trace_details(result)
        return max(0, int(round(cls._float(details.get("shield_absorb")))))

    @classmethod
    def _shield_branch(cls, result: dict[str, Any]) -> str | None:
        branch = result.get("shield_block_branch")
        if branch is None:
            branch = cls._damage_trace_details(result).get("shield_block_branch")
        branch_text = str(branch or "")
        return branch_text if branch_text in {"defense", "counter"} else None

    @classmethod
    def _is_shield_damage_feint(cls, result: dict[str, Any]) -> bool:
        action_facts = cls._dict(result.get("action_facts"))
        action_id = str(action_facts.get("id") or "")
        role = str(action_facts.get("role") or "")
        return role == "feint" and action_id in {"concussion", "shield_line_bash"}

    @classmethod
    def _prevented_damage_estimate(cls, result: dict[str, Any], *, source_actor: Any = None) -> int:
        details = cls._damage_trace_details(result)
        for key in ("after_resist", "raw"):
            value = cls._float(details.get(key))
            if value > 0:
                return int(round(value))
        damage_trace = result.get("damage_trace")
        if isinstance(damage_trace, dict):
            value = cls._float(damage_trace.get("raw"))
            if value > 0:
                return int(round(value))
        return cls._expected_source_damage(source_actor)

    @classmethod
    def _expected_source_damage(cls, actor: Any) -> int:
        actor_data = cls._dict(actor)
        stats = cls._dict(actor_data.get("stats"))
        mods = cls._dict(stats.get("mods"))
        base = cls._float(mods.get("main_hand_damage_base") or mods.get("physical_damage"))
        if base <= 0:
            return 0
        base += cls._float(mods.get("physical_damage_bonus"))
        spread = max(0.0, min(1.0, cls._float(mods.get("main_hand_damage_spread"))))
        expected = base * (1.0 - (spread / 2.0))
        expected *= max(0.0, cls._float(mods.get("damage_mult") or 1.0))
        return max(0, int(round(expected)))

    @staticmethod
    def _damage_trace_details(result: dict[str, Any]) -> dict[str, Any]:
        damage_trace = result.get("damage_trace")
        if not isinstance(damage_trace, dict):
            return {}
        details = damage_trace.get("details")
        return dict(details) if isinstance(details, dict) else {}

    @staticmethod
    def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    @staticmethod
    def _dict(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    @staticmethod
    def _increment(bucket: dict[str, int], key: str, amount: int = 1) -> None:
        bucket[key] = bucket.get(key, 0) + amount

    @staticmethod
    def _increment_nested(bucket: dict[str, dict[str, int]], outer: str, inner: str, amount: int = 1) -> None:
        values = bucket.setdefault(outer, {})
        values[inner] = values.get(inner, 0) + amount

    @staticmethod
    def _string_or_none(value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _ranged_position_or_none(value: Any) -> str | None:
        text = str(value or "")
        return text if text in {"far", "mid", "close"} else None

    @staticmethod
    def _int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _float(value: Any) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

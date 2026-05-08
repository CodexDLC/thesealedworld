from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from loguru import logger as log

from src.backend.core.calculators.skill_progression_calculator import (
    SkillProgressionBatchInput,
    SkillProgressionCalculator,
    SkillProgressionEntry,
)
from src.backend.features.game_catalog.skills.services import SkillCatalogService

if TYPE_CHECKING:
    from src.backend.features.combat.runtime.services.data_service import CombatDataService

ACTION_POWER_MULTIPLIERS: dict[str, float] = {
    "hit": 1.0,
    "miss": 0.25,
    "crit": 0.75,
    "dodge": 1.0,
    "parry": 1.0,
    "block": 1.0,
    "kill": 1.0,
}


@dataclass(frozen=True)
class CombatActorExperienceResult:
    actor_id: str
    char_id: int | None
    xp_buffer: dict[str, float] = field(default_factory=dict)
    rewards: dict[str, float] = field(default_factory=dict)


class CombatExperienceFinalizer:
    """
    Boundary for end-of-combat XP projection.

    Converts flat combat xp_buffer counters into skill/free XP rewards.
    """

    def __init__(self, *, catalog: SkillCatalogService | None = None) -> None:
        self.catalog = catalog or SkillCatalogService()

    async def finalize(
        self,
        data_service: CombatDataService,
        session_id: str,
        winner: str,
        *,
        character_sessions: Any | None = None,
    ) -> dict[str, CombatActorExperienceResult]:
        meta = await data_service.get_meta(session_id)
        if not isinstance(meta, dict):
            log.warning("CombatXPFinalizer | status=skipped reason=missing_meta session_id={}", session_id)
            return {}

        actor_ids = data_service.actor_ids_from_meta(meta)
        actors = await data_service.get_actors_batch(session_id, actor_ids)
        results: dict[str, CombatActorExperienceResult] = {}

        for actor_id, actor in actors.items():
            if not isinstance(actor, dict) or not str(actor_id).isdigit():
                continue

            char_id = int(actor_id)
            rewards = self.calculate_actor_rewards(actor)
            result = CombatActorExperienceResult(
                actor_id=str(actor_id),
                char_id=char_id,
                xp_buffer=self._float_mapping(actor.get("xp_buffer")),
                rewards=rewards,
            )
            results[str(actor_id)] = result

            if rewards and character_sessions is not None and hasattr(character_sessions, "apply_skill_progress"):
                await character_sessions.apply_skill_progress(char_id, rewards)

        log.info(
            "CombatXPFinalizer | status=success session_id={} winner={} actors={} rewarded={}",
            session_id,
            winner,
            len(results),
            len([result for result in results.values() if result.rewards]),
        )
        return results

    def calculate_actor_rewards(self, actor: dict[str, Any]) -> dict[str, float]:
        xp_buffer = self._float_mapping(actor.get("xp_buffer"))
        if not xp_buffer:
            return {}

        loadout = self._dict(actor.get("loadout"))
        layout = self._dict(loadout.get("layout"))
        attributes = self._flat_attributes(actor)
        current_skills = self._flat_skills(actor.get("skills"))

        action_power_by_skill: dict[str, float] = {}
        free_power = 0.0

        free_power += self._add_weapon_power(action_power_by_skill, xp_buffer, layout, "main_hand")
        free_power += self._add_weapon_power(action_power_by_skill, xp_buffer, layout, "off_hand")
        free_power += self._add_skill_power(
            action_power_by_skill, "skill_parrying", xp_buffer.get("defense_parry", 0.0)
        )
        free_power += self._add_skill_power(
            action_power_by_skill,
            "skill_shield_mastery",
            xp_buffer.get("defense_block", 0.0),
        )

        dodge_power = xp_buffer.get("defense_dodge", 0.0) * ACTION_POWER_MULTIPLIERS["dodge"]
        body_skill = layout.get("body")
        if isinstance(body_skill, str) and self.catalog.get(body_skill) is not None:
            action_power_by_skill[body_skill] = action_power_by_skill.get(body_skill, 0.0) + dodge_power
        else:
            free_power += dodge_power

        free_power += xp_buffer.get("kill_generic", 0.0) * ACTION_POWER_MULTIPLIERS["kill"]
        free_power += xp_buffer.get("free_xp", 0.0)

        entries: dict[str, SkillProgressionEntry] = {}
        for skill_key, action_power in action_power_by_skill.items():
            skill = self.catalog.get(skill_key)
            if skill is None or action_power <= 0:
                free_power += action_power
                continue
            entries[skill_key] = SkillProgressionEntry(
                skill=skill,
                attributes=attributes,
                current_skill=current_skills.get(skill_key, 0.0),
                action_power=action_power,
            )

        if free_power > 0:
            entries["free_xp"] = SkillProgressionEntry(
                attributes=attributes,
                current_skill=0.0,
                action_power=free_power,
                base_power=self._free_base_power(attributes),
                rate_mod=1.0,
                wall_mod=0.0,
            )

        return SkillProgressionCalculator.calculate(SkillProgressionBatchInput(entries=entries))

    def _add_weapon_power(
        self,
        action_power_by_skill: dict[str, float],
        xp_buffer: dict[str, float],
        layout: dict[str, Any],
        source_type: str,
    ) -> float:
        action_power = (
            xp_buffer.get(f"{source_type}_hit", 0.0) * ACTION_POWER_MULTIPLIERS["hit"]
            + xp_buffer.get(f"{source_type}_miss", 0.0) * ACTION_POWER_MULTIPLIERS["miss"]
            + xp_buffer.get(f"{source_type}_crit", 0.0) * ACTION_POWER_MULTIPLIERS["crit"]
        )
        skill_key = layout.get(source_type)
        if isinstance(skill_key, str) and self.catalog.get(skill_key) is not None:
            action_power_by_skill[skill_key] = action_power_by_skill.get(skill_key, 0.0) + action_power
            return 0.0
        return action_power

    def _add_skill_power(
        self,
        action_power_by_skill: dict[str, float],
        skill_key: str,
        count: float,
    ) -> float:
        action_power = count
        if action_power <= 0:
            return 0.0
        if self.catalog.get(skill_key) is None:
            return action_power
        action_power_by_skill[skill_key] = action_power_by_skill.get(skill_key, 0.0) + action_power
        return 0.0

    def _flat_attributes(self, actor: dict[str, Any]) -> dict[str, float]:
        raw = self._dict(actor.get("raw"))
        attributes = self._dict(raw.get("attributes"))
        flat: dict[str, float] = {}
        for key, value in attributes.items():
            if isinstance(value, dict):
                base = self._number(value.get("base"))
                source = sum(self._number(item) for item in self._dict(value.get("source")).values())
                temp = sum(self._number(item) for item in self._dict(value.get("temp")).values())
                flat[str(key)] = base + source + temp
            else:
                flat[str(key)] = self._number(value)
        return flat

    def _free_base_power(self, attributes: dict[str, float]) -> float:
        known_skills = [skill for skill in self.catalog.skills if skill.category.value == "combat"]
        if not known_skills:
            return 1.0
        total = 0.0
        for skill in known_skills:
            total += sum(
                float(attributes.get(stat_key, 0.0)) * float(weight) for stat_key, weight in skill.stat_weights.items()
            )
        return total / len(known_skills)

    @staticmethod
    def _flat_skills(raw_skills: Any) -> dict[str, float]:
        skills = raw_skills if isinstance(raw_skills, dict) else {}
        flat: dict[str, float] = {}
        for key, value in skills.items():
            if isinstance(value, dict):
                value = value.get("value", value.get("level", value.get("total_xp", value.get("xp", 0.0))))
            flat[str(key)] = CombatExperienceFinalizer._number(value)
        return flat

    @staticmethod
    def _float_mapping(value: Any) -> dict[str, float]:
        if not isinstance(value, dict):
            return {}
        return {str(key): CombatExperienceFinalizer._number(raw) for key, raw in value.items()}

    @staticmethod
    def _dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

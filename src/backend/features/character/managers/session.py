from __future__ import annotations

import builtins
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from src.backend.features.character.runtime.vitals import CharacterVitalsCalculator
from src.backend.features.character.schemas.session import (
    CharacterSessionAttributesDTO,
    CharacterSessionVitalsDTO,
)
from src.backend.infrastructure.redis.keys import PlayerCoreKey
from src.shared.enums import CoreDomain
from src.shared.enums.skill_enums import SkillProgressState

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class CharacterSessionError(RuntimeError):
    """Base error for player core session Redis operations."""


class SessionAlreadyExistsError(CharacterSessionError):
    """Raised when a player core session key already exists."""


class SessionNotFoundError(CharacterSessionError):
    """Raised when a player core session is required but absent."""


class StateTransitionError(CharacterSessionError):
    """Raised when a guarded state transition sees an unexpected current state."""


class CharacterSessionManager:
    """RedisJSON access layer for long-lived online character state."""

    DEFAULT_TTL_SECONDS = 6 * 60 * 60

    def __init__(self, redis: RedisService, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self.redis = redis
        self.key = PlayerCoreKey()
        self.ttl_seconds = ttl_seconds

    def build_key(self, char_id: int) -> str:
        return self.key.build(char_id=char_id)

    def _redis_client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    async def create_session(self, char_id: int, initial_data: dict[str, Any]) -> None:
        result = await self.redis.json_module.set(self.build_key(char_id), "$", initial_data, nx=True)
        if not result:
            raise SessionAlreadyExistsError(f"Character session already exists: char_id={char_id}")
        await self.touch(char_id)

    async def replace_session(self, char_id: int, data: dict[str, Any]) -> None:
        """Replace runtime AC from cold persistent state."""
        await self.redis.json_module.set(self.build_key(char_id), "$", data)
        await self.touch(char_id)

    async def update_session(self, char_id: int, data: dict[str, Any]) -> None:
        """Overwrite entire session document."""
        payload = await self._preserve_sync_dirty(char_id, data)
        await self.redis.json_module.set(self.build_key(char_id), "$", payload)
        await self.touch(char_id)

    async def get_session(self, char_id: int) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(self.build_key(char_id), "$")
        doc = self._first(result)
        if not isinstance(doc, dict):
            return None
        normalized = self._normalize_session_contract(doc)
        if normalized:
            await self.update_session(char_id, doc)
        return doc

    async def _preserve_sync_dirty(self, char_id: int, data: dict[str, Any]) -> dict[str, Any]:
        if "sync_dirty" in data:
            return data

        dirty_marker = await self.get_section(char_id, "sync_dirty")
        if not isinstance(dirty_marker, dict) or dirty_marker.get("dirty") is not True:
            return data

        payload = dict(data)
        payload["sync_dirty"] = dirty_marker
        return payload

    async def get_sessions_batch(self, char_ids: list[int]) -> dict[int, dict[str, Any] | None]:
        keys = [self.build_key(char_id) for char_id in char_ids]
        try:
            async with self._redis_client().pipeline(transaction=False) as pipe:
                for key in keys:
                    pipe.json().get(key, "$")
                results = await pipe.execute(raise_on_error=False)
        except Exception:
            return {char_id: None for char_id in char_ids}

        sessions: dict[int, dict[str, Any] | None] = {}
        for char_id, result in zip(char_ids, results, strict=False):
            doc = self._first(result)
            sessions[char_id] = doc if isinstance(doc, dict) else None
        return sessions

    async def get_section(self, char_id: int, section: str) -> Any:
        if section == "attributes":
            document = await self.get_session(char_id)
            return document.get("attributes") if isinstance(document, dict) else None

        result = await self.redis.json_module.get(self.build_key(char_id), f"$.{section}")
        return self._first(result)

    async def patch_fields(self, char_id: int, updates: dict[str, Any]) -> None:
        if not updates:
            return

        key = self.build_key(char_id)
        async with self._redis_client().pipeline(transaction=False) as pipe:
            for path, value in updates.items():
                pipe.json().set(key, path, value)
            pipe.expire(key, self.ttl_seconds)
            await pipe.execute()

    async def mark_dirty(
        self, char_id: int, *, reason: str, paths: list[str], targets: list[str] | None = None
    ) -> None:
        existing = await self.get_section(char_id, "sync_dirty")
        merged_paths: set[str] = set(paths)
        merged_targets: set[str] = set(targets or self._dirty_targets_from_paths(paths))
        reasons: list[str] = [reason]

        if isinstance(existing, dict) and existing.get("dirty") is True:
            raw_paths = existing.get("paths")
            if isinstance(raw_paths, list):
                merged_paths.update(str(path) for path in raw_paths)
            raw_targets = existing.get("targets")
            if isinstance(raw_targets, dict):
                merged_targets.update(str(key) for key, value in raw_targets.items() if value is True)
            previous_reason = existing.get("reason")
            if isinstance(previous_reason, str) and previous_reason and previous_reason != reason:
                reasons.insert(0, previous_reason)

        await self.patch_fields(
            char_id,
            {
                "$.sync_dirty": {
                    "dirty": True,
                    "reason": "+".join(dict.fromkeys(reasons)),
                    "paths": sorted(merged_paths),
                    "targets": {target: True for target in sorted(merged_targets)},
                    "generation": time.time(),
                }
            },
        )

    async def is_dirty(self, char_id: int) -> bool:
        dirty_marker = await self.get_section(char_id, "sync_dirty")
        return isinstance(dirty_marker, dict) and dirty_marker.get("dirty") is True

    async def clear_dirty(self, char_id: int, *, generation: float | None = None) -> None:
        if generation is not None:
            current = await self.get_section(char_id, "sync_dirty")
            if not isinstance(current, dict) or current.get("generation") != generation:
                return
        await self.patch_fields(char_id, {"$.sync_dirty": None})

    async def set_state(
        self,
        char_id: int,
        state: CoreDomain | str,
        *,
        prev_state: CoreDomain | str | None = None,
    ) -> None:
        """Set state and best-effort prev_state.

        This intentionally reads the current state before a non-atomic pipeline,
        so concurrent updates may race. Call sites in v1 are controlled; a guarded
        transition API can replace this later.
        """
        current_state = await self.get_section(char_id, "state")
        if current_state is None:
            raise SessionNotFoundError(f"Character session not found: char_id={char_id}")

        next_state = self._state_value(state)
        previous_state = self._state_value(prev_state) if prev_state is not None else current_state
        await self.patch_fields(
            char_id,
            {
                "$.prev_state": previous_state,
                "$.state": next_state,
            },
        )
        await self.mark_dirty(char_id, reason="state_changed", paths=["$.prev_state", "$.state"])

    async def delete_session(self, char_id: int) -> None:
        await self.redis.string.delete(self.build_key(char_id))

    async def exists(self, char_id: int) -> bool:
        return bool(await self.redis.string.exists(self.build_key(char_id)))

    async def transition_state(
        self,
        char_id: int,
        state: CoreDomain | str,
        *,
        expected_state: CoreDomain | str | None = None,
        prev_state: CoreDomain | str | None = None,
    ) -> None:
        current_state = await self.get_section(char_id, "state")
        if current_state is None:
            raise SessionNotFoundError(f"Character session not found: char_id={char_id}")

        expected = self._state_value(expected_state)
        if expected is not None and current_state != expected:
            raise StateTransitionError(
                f"Invalid state transition for char_id={char_id}: expected={expected} actual={current_state}"
            )

        await self.set_state(char_id, state, prev_state=prev_state)

    async def set_scenario_session(
        self,
        char_id: int,
        scenario_id: str,
        *,
        active_quest: str | None = None,
    ) -> None:
        await self.patch_fields(
            char_id,
            {
                "$.sessions.scenario_id": str(scenario_id),
                "$.active_quest": active_quest,
            },
        )
        await self.mark_dirty(
            char_id,
            reason="scenario_session_attached",
            paths=["$.sessions.scenario_id", "$.active_quest"],
        )

    async def clear_scenario_session(self, char_id: int) -> None:
        await self.patch_fields(
            char_id,
            {
                "$.sessions.scenario_id": None,
                "$.active_quest": None,
            },
        )
        await self.mark_dirty(
            char_id,
            reason="scenario_session_cleared",
            paths=["$.sessions.scenario_id", "$.active_quest"],
        )

    async def set_combat_session(self, char_id: int, combat_id: str) -> None:
        current_state = await self.get_section(char_id, "state")
        await self.patch_fields(
            char_id,
            {
                "$.prev_state": current_state or CoreDomain.EXPLORATION.value,
                "$.state": CoreDomain.COMBAT.value,
                "$.sessions.combat_id": str(combat_id),
                "$.sessions.combat_finalization_id": None,
            },
        )
        await self.mark_dirty(
            char_id,
            reason="combat_session_attached",
            paths=["$.prev_state", "$.sessions.combat_finalization_id", "$.sessions.combat_id", "$.state"],
        )

    async def clear_combat_session(self, char_id: int) -> None:
        await self.patch_fields(char_id, {"$.sessions.combat_id": None})
        await self.mark_dirty(char_id, reason="combat_session_cleared", paths=["$.sessions.combat_id"])

    async def set_encounter_session(self, char_id: int, encounter_id: str) -> None:
        await self.patch_fields(char_id, {"$.sessions.encounter_id": str(encounter_id)})
        await self.mark_dirty(
            char_id,
            reason="encounter_session_attached",
            paths=["$.sessions.encounter_id"],
        )

    async def clear_encounter_session(self, char_id: int) -> None:
        await self.patch_fields(char_id, {"$.sessions.encounter_id": None})
        await self.mark_dirty(
            char_id,
            reason="encounter_session_cleared",
            paths=["$.sessions.encounter_id"],
        )

    async def set_arena_session(self, char_id: int, arena_id: str) -> None:
        await self.patch_fields(char_id, {"$.sessions.arena_id": str(arena_id)})
        await self.mark_dirty(char_id, reason="arena_session_attached", paths=["$.sessions.arena_id"])

    async def clear_arena_session(self, char_id: int) -> None:
        await self.patch_fields(char_id, {"$.sessions.arena_id": None})
        await self.mark_dirty(char_id, reason="arena_session_cleared", paths=["$.sessions.arena_id"])

    async def reset_main_runtime_refs_to_exploration(self, char_id: int) -> None:
        updates = {
            "$.state": CoreDomain.EXPLORATION.value,
            "$.prev_state": CoreDomain.EXPLORATION.value,
            "$.sessions.scenario_id": None,
            "$.sessions.combat_id": None,
            "$.sessions.combat_finalization_id": None,
            "$.sessions.post_combat": None,
            "$.sessions.encounter_id": None,
            "$.sessions.arena_id": None,
            "$.sessions.death_run_id": None,
            "$.sessions.death_corpse_id": None,
            "$.active_quest": None,
        }
        await self.patch_fields(char_id, updates)
        await self.mark_dirty(
            char_id,
            reason="main_runtime_refs_reset",
            paths=sorted(updates),
        )

    async def set_inventory_session(self, char_id: int, inventory_id: str) -> None:
        await self.patch_fields(char_id, {"$.sessions.inventory_id": str(inventory_id)})

    async def clear_inventory_session(self, char_id: int) -> None:
        await self.patch_fields(char_id, {"$.sessions.inventory_id": None})

    async def set_items_projection(self, char_id: int, items: dict[str, Any]) -> None:
        await self.patch_fields(char_id, {"$.items": items})

    async def update_vital(
        self,
        char_id: int,
        vital: Literal["hp", "energy", "stamina"],
        *,
        cur: int | None = None,
        max: int | None = None,  # noqa: A002
    ) -> None:
        if cur is None and max is None:
            return

        document = await self.get_session(char_id)
        if not isinstance(document, dict):
            raise SessionNotFoundError(f"Character session not found: char_id={char_id}")

        now = datetime.now(UTC).timestamp()
        vitals = CharacterSessionVitalsDTO.model_validate(document.get("vitals") or {})
        vitals = CharacterVitalsCalculator.apply_regen(vitals, now=now)
        value = getattr(vitals, vital)

        if max is not None:
            value.max = builtins.max(1, int(max))
        if cur is not None:
            value.cur = builtins.max(0, min(int(cur), value.max))
        else:
            value.cur = builtins.max(0, min(int(value.cur), value.max))
        vitals.last_update = now

        payload = vitals.model_dump(mode="json")
        await self.patch_fields(char_id, {"$.vitals": payload})
        await self.mark_dirty(
            char_id,
            reason="vitals_changed",
            paths=[f"$.vitals.{vital}", "$.vitals.last_update"],
        )

    async def apply_vitals_regen(self, char_id: int) -> dict[str, Any]:
        document = await self.get_session(char_id)
        if not isinstance(document, dict):
            raise SessionNotFoundError(f"Character session not found: char_id={char_id}")

        vitals = CharacterSessionVitalsDTO.model_validate(document.get("vitals") or {})
        before = vitals.model_dump(mode="json")
        updated_vitals = CharacterVitalsCalculator.apply_regen(vitals)
        payload = updated_vitals.model_dump(mode="json")
        if payload != before:
            await self.patch_fields(char_id, {"$.vitals": payload})
            await self.mark_dirty(
                char_id,
                reason="vitals_regenerated",
                paths=["$.vitals.hp", "$.vitals.energy", "$.vitals.stamina", "$.vitals.last_update"],
            )
        return payload

    async def restore_vitals_to_max(self, char_id: int) -> dict[str, Any]:
        document = await self.get_session(char_id)
        if not isinstance(document, dict):
            raise SessionNotFoundError(f"Character session not found: char_id={char_id}")

        attributes = CharacterSessionAttributesDTO.model_validate(document.get("attributes") or {})
        restored_vitals = CharacterVitalsCalculator.restore_to_max_vitals(attributes)
        payload = restored_vitals.model_dump(mode="json")
        await self.patch_fields(char_id, {"$.vitals": payload})
        await self.mark_dirty(
            char_id,
            reason="vitals_restored",
            paths=["$.vitals.hp", "$.vitals.energy", "$.vitals.stamina", "$.vitals.last_update"],
        )
        return payload

    async def apply_attribute_bonus(self, char_id: int, bonuses: dict[str, int]) -> None:
        if not bonuses:
            return
        key = self.build_key(char_id)
        async with self._redis_client().pipeline(transaction=False) as pipe:
            for attr, delta in bonuses.items():
                pipe.json().numincrby(key, f"$.attributes.{attr}", int(delta))
            await pipe.execute()
        await self.mark_dirty(
            char_id,
            reason="attributes_changed",
            paths=[f"$.attributes.{attr}" for attr in sorted(bonuses)],
        )

    async def unlock_skills(self, char_id: int, skills: list[str], *, initial_xp: float = 0.0) -> None:
        unique_skills = list(dict.fromkeys(skill for skill in skills if skill))
        if not unique_skills:
            return

        starting_xp = min(1.0, max(0.0, float(initial_xp or 0.0)))
        document = await self.get_session(char_id)
        session_skills = document.get("skills") if isinstance(document, dict) else {}
        current_skills: dict[str, Any] = session_skills if isinstance(session_skills, dict) else {}

        key = self.build_key(char_id)
        async with self._redis_client().pipeline(transaction=False) as pipe:
            for skill_key in unique_skills:
                current = current_skills.get(skill_key)
                current_xp = 0.0
                if isinstance(current, dict):
                    try:
                        current_xp = float(current.get("xp", current.get("total_xp", 0.0)) or 0.0)
                    except (TypeError, ValueError):
                        current_xp = 0.0
                pipe.json().set(
                    key,
                    f"$.skills.{skill_key}",
                    {
                        "xp": round(max(current_xp, starting_xp), 4),
                        "unlocked": True,
                        "state": SkillProgressState.PLUS.value,
                    },
                )
            await pipe.execute()
        await self.mark_dirty(
            char_id,
            reason="skills_unlocked",
            paths=[f"$.skills.{skill_key}" for skill_key in sorted(unique_skills)],
        )

    async def apply_skill_progress(self, char_id: int, rewards: dict[str, float]) -> None:
        if not rewards:
            return

        document = await self.get_session(char_id)
        if not isinstance(document, dict):
            raise SessionNotFoundError(f"Character session not found: char_id={char_id}")

        updates: dict[str, Any] = {}
        dirty_paths: list[str] = []
        skills_raw = document.get("skills")
        skills: dict[str, Any] = skills_raw if isinstance(skills_raw, dict) else {}

        for reward_key, delta in rewards.items():
            delta = round(float(delta or 0.0), 4)
            if delta <= 0:
                continue

            if reward_key == "free_xp":
                progression = dict(document.get("progression") or {})
                progression["free_xp"] = round(float(progression.get("free_xp", 0.0) or 0.0) + delta, 4)
                updates["$.progression"] = progression
                dirty_paths.append("$.progression.free_xp")
                continue

            current = skills.get(reward_key)
            if isinstance(current, dict):
                payload = dict(current)
                payload["xp"] = round(float(payload.get("xp", payload.get("total_xp", 0.0)) or 0.0) + delta, 4)
                payload.setdefault("unlocked", True)
                payload.setdefault("state", SkillProgressState.PLUS.value)
            else:
                payload = {
                    "xp": delta,
                    "unlocked": True,
                    "state": SkillProgressState.PLUS.value,
                }
            updates[f"$.skills.{reward_key}"] = payload
            dirty_paths.append(f"$.skills.{reward_key}")

        if not updates:
            return

        await self.patch_fields(char_id, updates)
        await self.mark_dirty(char_id, reason="skill_progress_applied", paths=sorted(set(dirty_paths)))

    async def apply_pending_progress(self, char_id: int, rewards: dict[str, float]) -> dict[str, Any]:
        if not rewards:
            return {}

        document = await self.get_session(char_id)
        if not isinstance(document, dict):
            raise SessionNotFoundError(f"Character session not found: char_id={char_id}")

        pending = dict(document.get("pending_progress") or {})
        skills = dict(pending.get("skills") or {})
        free_xp = float(pending.get("free_xp", 0.0) or 0.0)
        for reward_key, delta in rewards.items():
            value = round(float(delta or 0.0), 4)
            if value <= 0:
                continue
            if reward_key == "free_xp":
                free_xp = round(free_xp + value, 4)
            else:
                skills[str(reward_key)] = round(float(skills.get(str(reward_key), 0.0) or 0.0) + value, 4)

        pending["free_xp"] = free_xp
        pending["skills"] = skills
        await self.patch_fields(char_id, {"$.pending_progress": pending})
        return pending

    async def set_pending_progress(self, char_id: int, pending: dict[str, Any]) -> None:
        await self.patch_fields(char_id, {"$.pending_progress": pending})

    async def set_risk_state(self, char_id: int, risk: dict[str, Any]) -> None:
        await self.patch_fields(char_id, {"$.risk": risk})

    async def update_bio(
        self,
        char_id: int,
        *,
        name: str | None = None,
        gender: str | None = None,
        avatar: str | None = None,
    ) -> None:
        raise NotImplementedError("Bio point-updates are planned for iteration 2.")

    async def get_location(self, char_id: int) -> dict[str, Any] | None:
        """Get current and previous location IDs."""
        result = await self.redis.json_module.get(self.build_key(char_id), "$.location")
        return self._first(result)

    async def set_location(
        self,
        char_id: int,
        current: str,
        *,
        prev: str | None = None,
    ) -> None:
        """Update current and optionally previous location."""
        updates = {"$.location.current": current}
        if prev is not None:
            updates["$.location.prev"] = prev

        await self.patch_fields(char_id, updates)
        await self.mark_dirty(char_id, reason="location_changed", paths=sorted(updates))

    async def set_world_theme(self, char_id: int, world_theme: dict[str, Any]) -> None:
        """Persist last known world theme for cross-domain screens."""
        if not await self.exists(char_id):
            return
        await self.patch_fields(char_id, {"$.world_theme": world_theme})

    async def get_world_theme(self, char_id: int) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(self.build_key(char_id), "$.world_theme")
        theme = self._first(result)
        return theme if isinstance(theme, dict) else None

    async def get_skills(self, char_id: int) -> dict[str, float] | None:
        """Get all character skills."""
        result = await self.redis.json_module.get(self.build_key(char_id), "$.skills")
        return self._first(result)

    async def touch(self, char_id: int) -> None:
        await self.redis.string.expire(self.build_key(char_id), self.ttl_seconds)

    @staticmethod
    def _first(result: Any) -> Any:
        if isinstance(result, list):
            return result[0] if result else None
        return result

    @staticmethod
    def _state_value(state: CoreDomain | str | None) -> str | None:
        if state is None:
            return None
        return state.value if isinstance(state, CoreDomain) else state

    @staticmethod
    def _normalize_session_contract(document: dict[str, Any]) -> bool:
        changed = False

        location = document.get("location")
        if isinstance(location, dict) and "previous" in location:
            if location.get("prev") is None:
                location["prev"] = location["previous"]
            del location["previous"]
            changed = True

        return changed

    @staticmethod
    def _dirty_targets_from_paths(paths: list[str]) -> list[str]:
        targets: set[str] = set()
        for path in paths:
            if path.startswith("$.attributes"):
                targets.add("attributes")
            elif path.startswith("$.skills") or path.startswith("$.progression"):
                targets.add("skills")
            elif path.startswith("$.symbiote"):
                targets.add("symbiote")
            elif (
                path.startswith("$.items")
                or path.startswith("$.metrics.gear_score")
                or path.startswith("$.world_theme")
                or path.startswith("$.sessions.inventory_id")
            ):
                continue
            else:
                targets.add("character")
        return sorted(targets)

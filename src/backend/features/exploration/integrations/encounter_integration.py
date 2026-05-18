from __future__ import annotations

import copy
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.features.exploration.runtime.experience import flat_attribute_snapshot
from src.backend.features.monsters.dto import MonsterGroupResult

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService

    from src.backend.core.bus import GameEventProducer
    from src.backend.features.character.managers import CharacterSessionManager
    from src.backend.infrastructure.world.location_store import WorldLocationStore


ENCOUNTER_SKILL_KEYS = ("skill_scouting", "skill_pathfinder", "skill_hunting", "skill_taming")
MONSTER_GROUP_PREPARE_REQUESTED = "monsters.group_prepare_requested"
COMBAT_SESSION_REQUESTED = "combat.session_requested"
ENCOUNTER_SESSION_TTL_SECONDS = 30 * 60


@dataclass(frozen=True, slots=True)
class EncounterSkillSnapshot:
    skill_scouting: float = 0.0
    skill_pathfinder: float = 0.0
    skill_hunting: float = 0.0
    skill_taming: float = 0.0
    raw: dict[str, Any] | None = None

    def value(self, skill_key: str) -> float:
        if skill_key not in ENCOUNTER_SKILL_KEYS:
            return 0.0
        return float(getattr(self, skill_key, 0.0))

    def as_dict(self) -> dict[str, float]:
        return {skill_key: self.value(skill_key) for skill_key in ENCOUNTER_SKILL_KEYS}


@dataclass(frozen=True, slots=True)
class EncounterLocationContext:
    loc_id: str
    data: dict[str, Any]
    flags: dict[str, Any]
    anchor_influence: dict[str, Any]


class EncounterIntegration:
    """Infrastructure boundary for the exploration encounter runtime.

    This class owns reads/writes against active character sessions, world cache,
    Redis cache, and stream clients. Encounter gameplay code should call these
    semantic methods instead of reaching into Redis, AC documents, monsters, or
    combat transport directly.
    """

    def __init__(
        self,
        *,
        character_sessions: CharacterSessionManager,
        world_store: WorldLocationStore | None = None,
        events: GameEventProducer | None = None,
        redis: RedisService | None = None,
    ) -> None:
        self.character_sessions = character_sessions
        self.world_store = world_store
        self.events = events
        self.redis = redis

    async def get_ac_skill_snapshot(self, char_id: int) -> EncounterSkillSnapshot:
        started_at = perf_counter()
        raw_skills = await self.character_sessions.get_skills(char_id)
        skills = raw_skills if isinstance(raw_skills, dict) else {}
        snapshot = EncounterSkillSnapshot(
            skill_scouting=_skill_value(skills.get("skill_scouting")),
            skill_pathfinder=_skill_value(skills.get("skill_pathfinder")),
            skill_hunting=_skill_value(skills.get("skill_hunting")),
            skill_taming=_skill_value(skills.get("skill_taming")),
            raw=dict(skills),
        )
        logger.debug(
            "EncounterIntegrationTiming | op=get_ac_skill_snapshot char_id={} ms={}",
            char_id,
            _elapsed_ms(started_at),
        )
        return snapshot

    async def get_ac_attribute_snapshot(self, char_id: int) -> dict[str, float]:
        started_at = perf_counter()
        raw_attributes = await self.character_sessions.get_section(char_id, "attributes")
        attributes = flat_attribute_snapshot(raw_attributes)
        logger.debug(
            "EncounterIntegrationTiming | op=get_ac_attribute_snapshot char_id={} ms={}",
            char_id,
            _elapsed_ms(started_at),
        )
        return attributes

    async def apply_skill_progress(self, char_id: int, rewards: dict[str, float]) -> None:
        clean_rewards = {
            str(skill_key): float(delta)
            for skill_key, delta in rewards.items()
            if str(skill_key).startswith("skill_") and _positive_number(delta)
        }
        if not clean_rewards:
            return
        started_at = perf_counter()
        await self.character_sessions.apply_skill_progress(char_id, clean_rewards)
        logger.debug(
            "EncounterIntegrationTiming | op=apply_skill_progress char_id={} rewards={} ms={}",
            char_id,
            sorted(clean_rewards),
            _elapsed_ms(started_at),
        )

    async def get_active_encounter_id(self, char_id: int) -> str | None:
        sessions = await self.character_sessions.get_section(char_id, "sessions")
        if not isinstance(sessions, dict):
            return None
        encounter_id = sessions.get("encounter_id")
        return str(encounter_id) if encounter_id else None

    async def attach_encounter_session(self, char_id: int, encounter_id: str) -> None:
        await self.character_sessions.set_encounter_session(char_id, encounter_id)

    async def detach_encounter_session(self, char_id: int) -> None:
        await self.character_sessions.clear_encounter_session(char_id)

    def build_encounter_key(self, encounter_id: str) -> str:
        return f"game:encounter:{encounter_id}"

    async def create_encounter_session(
        self,
        encounter_id: str,
        payload: dict[str, Any],
        *,
        ttl_seconds: int = ENCOUNTER_SESSION_TTL_SECONDS,
    ) -> dict[str, Any]:
        if self.redis is None:
            raise RuntimeError("EncounterIntegration requires redis for encounter session writes")
        session = dict(payload)
        session.setdefault("encounter_id", encounter_id)
        key = self.build_encounter_key(encounter_id)
        await self.redis.json_module.set(key, "$", copy.deepcopy(session))
        await self.redis.string.expire(key, int(ttl_seconds))
        return copy.deepcopy(session)

    async def get_encounter_session(self, encounter_id: str) -> dict[str, Any] | None:
        if self.redis is None:
            return None
        result = await self.redis.json_module.get(self.build_encounter_key(encounter_id), "$")
        payload = _first(result)
        return copy.deepcopy(payload) if isinstance(payload, dict) else None

    async def patch_encounter_session(self, encounter_id: str, updates: dict[str, Any]) -> None:
        if self.redis is None:
            raise RuntimeError("EncounterIntegration requires redis for encounter session patches")
        if not updates:
            return
        key = self.build_encounter_key(encounter_id)
        async with self._redis_client().pipeline(transaction=False) as pipe:
            for path, value in updates.items():
                json_path = path if path.startswith("$.") else f"$.{path}"
                pipe.json().set(key, json_path, value)
            await pipe.execute()

    async def clear_encounter_session(self, encounter_id: str) -> None:
        if self.redis is None:
            return
        await self.redis.string.delete(self.build_encounter_key(encounter_id))

    async def get_location_context(self, loc_id: str) -> EncounterLocationContext | None:
        if self.world_store is None:
            raise RuntimeError("EncounterIntegration requires world_store for location context")
        started_at = perf_counter()
        data = await self.world_store.get_location(loc_id)
        if not isinstance(data, dict):
            return None
        raw_flags = data.get("flags")
        flags = raw_flags if isinstance(raw_flags, dict) else {}

        raw_influence = data.get("anchor_influence")
        anchor_influence = raw_influence if isinstance(raw_influence, dict) else {}

        logger.debug(
            "EncounterIntegrationTiming | op=get_location_context loc_id={} ms={}",
            loc_id,
            _elapsed_ms(started_at),
        )
        return EncounterLocationContext(
            loc_id=loc_id,
            data=dict(data),
            flags=dict(flags),
            anchor_influence=dict(anchor_influence),
        )

    async def move_actor(self, char_id: int, from_loc: str | None, to_loc: str) -> bool:
        if self.world_store is None:
            raise RuntimeError("EncounterIntegration requires world_store for actor movement")
        started_at = perf_counter()
        if not await self.world_store.location_exists(to_loc):
            return False
        if from_loc:
            await self.world_store.remove_player(from_loc, char_id)
        await self.world_store.add_player(to_loc, char_id)
        await self.character_sessions.set_location(char_id, to_loc, prev=from_loc)
        logger.debug(
            "EncounterIntegrationTiming | op=move_actor char_id={} from={} to={} ms={}",
            char_id,
            from_loc,
            to_loc,
            _elapsed_ms(started_at),
        )
        return True

    async def get_cached_encounter_monsters(self, cache_key: str) -> dict[str, Any] | None:
        if self.redis is None:
            return None
        result = await self.redis.json_module.get(cache_key, "$")
        payload = _first(result)
        return copy.deepcopy(payload) if isinstance(payload, dict) else None

    async def set_cached_encounter_monsters(
        self,
        cache_key: str,
        payload: dict[str, Any],
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        if self.redis is None:
            raise RuntimeError("EncounterIntegration requires redis for encounter monster cache writes")
        await self.redis.json_module.set(cache_key, "$", dict(payload))
        if ttl_seconds is not None:
            await self.redis.string.expire(cache_key, int(ttl_seconds))

    async def prepare_monster_group(
        self,
        loc_id: str,
        budget: float,
        preferred_family_id: str | None = None,
        force_single_family: bool = True,
        *,
        scope_id: str | None = None,
        ttl: int = 300,
        correlation_id: str | None = None,
        timeout: float = 10.0,
    ) -> MonsterGroupResult:
        if self.events is None:
            raise RuntimeError("EncounterIntegration requires events for monster requests")
        payload: dict[str, str] = {
            "loc_id": str(loc_id),
            "budget": _number_payload_value(budget),
            "force_single_family": "true" if force_single_family else "false",
            "ttl": str(int(ttl)),
        }
        if preferred_family_id:
            payload["preferred_family_id"] = str(preferred_family_id)
        if scope_id:
            payload["scope_id"] = str(scope_id)

        response = await self.events.request(
            MONSTER_GROUP_PREPARE_REQUESTED,
            payload,
            timeout=timeout,
            correlation_id=correlation_id,
        )
        if not isinstance(response, dict) or response.get("status") != "ok":
            raise RuntimeError(f"Monster group prepare failed: {response!r}")
        group_payload = response.get("payload")
        if not isinstance(group_payload, dict):
            raise RuntimeError(f"Monster group prepare returned invalid payload: {response!r}")
        return MonsterGroupResult.model_validate(group_payload)

    async def request_combat_session(
        self,
        payload: dict[str, Any],
        *,
        correlation_id: str | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        if self.events is None:
            raise RuntimeError("EncounterIntegration requires events for combat requests")
        response = await self.events.request(
            COMBAT_SESSION_REQUESTED,
            dict(payload),
            timeout=timeout,
            correlation_id=correlation_id,
        )
        return dict(response) if isinstance(response, dict) else {}

    async def attach_combat_session(self, char_id: int, combat_id: str) -> None:
        await self.character_sessions.set_combat_session(char_id, combat_id)

    def _redis_client(self) -> Any:
        if self.redis is None:
            raise RuntimeError("EncounterIntegration requires redis")
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client


def _skill_value(raw: Any) -> float:
    if isinstance(raw, dict):
        if raw.get("unlocked") is False:
            return 0.0
        raw = raw.get("xp", raw.get("total_xp", 0.0))
    try:
        return max(0.0, float(raw or 0.0))
    except (TypeError, ValueError):
        return 0.0


def _positive_number(value: Any) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def _number_payload_value(value: float) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number)


def _first(result: Any) -> Any:
    if isinstance(result, list):
        return result[0] if result else None
    return result


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 2)

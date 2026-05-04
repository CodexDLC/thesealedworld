from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

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


ATTRIBUTE_KEY_MIGRATIONS = {
    "intelligence": "intellect",
    "wisdom": "memory",
    "men": "mental",
    "charisma": "projection",
    "luck": "prediction",
}


class CharacterSessionManager:
    """RedisJSON access layer for long-lived online character state."""

    def __init__(self, redis: RedisService) -> None:
        self.redis = redis
        self.key = PlayerCoreKey()

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

    async def update_session(self, char_id: int, data: dict[str, Any]) -> None:
        """Overwrite entire session document."""
        await self.redis.json_module.set(self.build_key(char_id), "$", data)

    async def get_session(self, char_id: int) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(self.build_key(char_id), "$")
        doc = self._first(result)
        if not isinstance(doc, dict):
            return None
        normalized = self._normalize_session_contract(doc)
        if normalized:
            await self.update_session(char_id, doc)
        return doc

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
            await pipe.execute()

    async def set_state(self, char_id: int, state: CoreDomain | str) -> None:
        """Set state and best-effort prev_state.

        This intentionally reads the current state before a non-atomic pipeline,
        so concurrent updates may race. Call sites in v1 are controlled; a guarded
        transition API can replace this later.
        """
        current_state = await self.get_section(char_id, "state")
        if current_state is None:
            raise SessionNotFoundError(f"Character session not found: char_id={char_id}")

        next_state = state.value if isinstance(state, CoreDomain) else state
        await self.patch_fields(
            char_id,
            {
                "$.prev_state": current_state,
                "$.state": next_state,
            },
        )

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
    ) -> None:
        current_state = await self.get_section(char_id, "state")
        if current_state is None:
            raise SessionNotFoundError(f"Character session not found: char_id={char_id}")

        expected = expected_state.value if isinstance(expected_state, CoreDomain) else expected_state
        if expected is not None and current_state != expected:
            raise StateTransitionError(
                f"Invalid state transition for char_id={char_id}: expected={expected} actual={current_state}"
            )

        next_state = state.value if isinstance(state, CoreDomain) else state
        await self.patch_fields(
            char_id,
            {
                "$.prev_state": current_state,
                "$.state": next_state,
            },
        )

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

    async def clear_scenario_session(self, char_id: int) -> None:
        await self.patch_fields(
            char_id,
            {
                "$.sessions.scenario_id": None,
                "$.active_quest": None,
            },
        )

    async def set_combat_session(self, char_id: int, combat_id: str) -> None:
        await self.patch_fields(char_id, {"$.sessions.combat_id": str(combat_id)})

    async def clear_combat_session(self, char_id: int) -> None:
        await self.patch_fields(char_id, {"$.sessions.combat_id": None})

    async def set_inventory_session(self, char_id: int, inventory_id: str) -> None:
        raise NotImplementedError("Inventory session attachment is planned for iteration 2.")

    async def clear_inventory_session(self, char_id: int) -> None:
        raise NotImplementedError("Inventory session clearing is planned for iteration 2.")

    async def update_vital(
        self,
        char_id: int,
        vital: Literal["hp", "energy", "stamina"],
        *,
        cur: int | None = None,
        max: int | None = None,  # noqa: A002
    ) -> None:
        raise NotImplementedError("Vital point-updates are planned for iteration 2.")

    async def apply_attribute_bonus(self, char_id: int, bonuses: dict[str, int]) -> None:
        if not bonuses:
            return
        key = self.build_key(char_id)
        async with self._redis_client().pipeline(transaction=False) as pipe:
            for attr, delta in bonuses.items():
                pipe.json().numincrby(key, f"$.attributes.{attr}", int(delta))
            await pipe.execute()

    async def unlock_skills(self, char_id: int, skills: list[str]) -> None:
        unique_skills = list(dict.fromkeys(skill for skill in skills if skill))
        if not unique_skills:
            return

        key = self.build_key(char_id)
        async with self._redis_client().pipeline(transaction=False) as pipe:
            for skill_key in unique_skills:
                pipe.json().set(
                    key,
                    f"$.skills.{skill_key}",
                    {
                        "xp": 0.0,
                        "unlocked": True,
                        "state": SkillProgressState.PLUS.value,
                    },
                )
            await pipe.execute()

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
            updates["$.location.previous"] = prev

        await self.patch_fields(char_id, updates)

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
        raise NotImplementedError("Activity markers are planned for iteration 2.")

    @staticmethod
    def _first(result: Any) -> Any:
        if isinstance(result, list):
            return result[0] if result else None
        return result

    @staticmethod
    def _normalize_session_contract(document: dict[str, Any]) -> bool:
        attributes = document.get("attributes")
        if not isinstance(attributes, dict):
            return False

        changed = False
        for old_key, new_key in ATTRIBUTE_KEY_MIGRATIONS.items():
            if old_key not in attributes:
                continue
            attributes.setdefault(new_key, attributes[old_key])
            del attributes[old_key]
            changed = True
        return changed

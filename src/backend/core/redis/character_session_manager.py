from __future__ import annotations

from typing import Any, Literal

from codex_platform.redis_service import RedisService

from src.backend.core.redis.keys import PlayerCoreKey
from src.shared.enums import CoreDomain


class CharacterSessionError(RuntimeError):
    """Base error for player core session Redis operations."""


class SessionAlreadyExistsError(CharacterSessionError):
    """Raised when a player core session key already exists."""


class SessionNotFoundError(CharacterSessionError):
    """Raised when a player core session is required but absent."""


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

    async def get_session(self, char_id: int) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(self.build_key(char_id), "$")
        doc = self._first(result)
        return doc if isinstance(doc, dict) else None

    async def get_section(self, char_id: int, section: str) -> Any:
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
        raise NotImplementedError("Character session guarded transitions are planned for iteration 2.")

    async def set_scenario_session(
        self,
        char_id: int,
        scenario_id: str,
        *,
        active_quest: str | None = None,
    ) -> None:
        raise NotImplementedError("Scenario session attachment is planned for iteration 2.")

    async def clear_scenario_session(self, char_id: int) -> None:
        raise NotImplementedError("Scenario session clearing is planned for iteration 2.")

    async def set_combat_session(self, char_id: int, combat_id: str) -> None:
        raise NotImplementedError("Combat session attachment is planned for iteration 2.")

    async def clear_combat_session(self, char_id: int) -> None:
        raise NotImplementedError("Combat session clearing is planned for iteration 2.")

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
        max: int | None = None,
    ) -> None:
        raise NotImplementedError("Vital point-updates are planned for iteration 2.")

    async def update_bio(
        self,
        char_id: int,
        *,
        name: str | None = None,
        gender: str | None = None,
        avatar: str | None = None,
    ) -> None:
        raise NotImplementedError("Bio point-updates are planned for iteration 2.")

    async def set_location(
        self,
        char_id: int,
        current: str,
        *,
        prev: str | None = None,
    ) -> None:
        raise NotImplementedError("Location updates are planned for iteration 2.")

    async def touch(self, char_id: int) -> None:
        raise NotImplementedError("Activity markers are planned for iteration 2.")

    @staticmethod
    def _first(result: Any) -> Any:
        if isinstance(result, list):
            return result[0] if result else None
        return result

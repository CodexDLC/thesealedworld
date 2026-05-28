from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.scenario.dto.context import ScenarioContextDTO
from src.backend.infrastructure.scenario.managers.keys import ScenarioSessionKey

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class ScenarioSessionError(RuntimeError):
    pass


class ScenarioSessionAlreadyExistsError(ScenarioSessionError):
    pass


SCENARIO_SESSION_TTL_SECONDS = 24 * 60 * 60


class ScenarioSessionManager:
    def __init__(self, redis: RedisService) -> None:
        self.redis = redis
        self.key = ScenarioSessionKey()

    def build_key(self, char_id: int) -> str:
        return self.key.build(char_id=char_id)

    def _redis_client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    async def create(self, char_id: int, context: ScenarioContextDTO) -> None:
        result = await self.redis.json_module.set(
            self.build_key(char_id),
            "$",
            context.model_dump(mode="json"),
            nx=True,
        )
        if not result:
            raise ScenarioSessionAlreadyExistsError(f"Scenario session already exists: char_id={char_id}")
        await self.redis.string.expire(self.build_key(char_id), SCENARIO_SESSION_TTL_SECONDS)

    async def get(self, char_id: int) -> ScenarioContextDTO | None:
        result = await self.redis.json_module.get(self.build_key(char_id), "$")
        doc = self._first(result)
        return ScenarioContextDTO.model_validate(doc) if isinstance(doc, dict) else None

    async def patch(self, char_id: int, updates: dict[str, Any]) -> None:
        if not updates:
            return
        key = self.build_key(char_id)
        async with self._redis_client().pipeline(transaction=False) as pipe:
            for path, value in updates.items():
                pipe.json().set(key, path, value)
            pipe.expire(key, SCENARIO_SESSION_TTL_SECONDS)
            await pipe.execute()

    async def delete(self, char_id: int) -> None:
        await self.redis.string.delete(self.build_key(char_id))

    async def exists(self, char_id: int) -> bool:
        return await self.redis.string.exists(self.build_key(char_id))

    async def list_session_summaries(self, *, limit: int = 100) -> list[dict[str, Any]]:
        client = self._redis_client()
        keys: list[Any] = []
        cursor = 0
        while True:
            cursor, batch = await client.scan(cursor, match="game:ac:*:scenario", count=limit)
            keys.extend(batch)
            if cursor == 0:
                break

        results: list[dict[str, Any]] = []
        for key in keys:
            try:
                raw = await self.redis.json_module.get(key, "$")
                doc = self._first(raw)
                if not isinstance(doc, dict):
                    continue
                key_str = key.decode() if isinstance(key, bytes) else str(key)
                parts = key_str.split(":")
                char_id = parts[2] if len(parts) >= 4 else "?"
                results.append(
                    {
                        "char_id": char_id,
                        "session_id": doc.get("scenario_session_id", "-"),
                        "quest_key": doc.get("quest_key", "-"),
                        "current_node": doc.get("current_node_key", "-"),
                        "step": f"{doc.get('step_counter', 0)}/{doc.get('total_steps', '?')}",
                        "updated_at": doc.get("updated_at", "-"),
                    }
                )
            except Exception:  # nosec B112
                continue
        return results

    @staticmethod
    def _first(result: Any) -> Any:
        if isinstance(result, list):
            return result[0] if result else None
        return result

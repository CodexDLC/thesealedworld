from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from src.backend.features.actor_state.services.actor_state_service import ActorStateService
from src.backend.features.combat.services.lifecycle_service import CombatLifecycleError
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService

    from src.backend.core.bus import GameEventProducer
    from src.backend.infrastructure.actor_state import ActorSnapshotManager, CharacterSessionManager


class CombatSystemIntegrator:
    """Feature facade over actor snapshot, character session, and event boundaries."""

    SNAPSHOT_TIMEOUT_SECONDS = 10.0

    def __init__(
        self,
        *,
        actor_snapshots: ActorSnapshotManager,
        character_sessions: CharacterSessionManager,
        events: GameEventProducer,
        redis: RedisService | None = None,
    ) -> None:
        self.actor_snapshots = actor_snapshots
        self.character_sessions = character_sessions
        self.events = events
        self.redis = redis

    async def prepare_actor_snapshots(
        self,
        combat_id: str,
        *,
        player_ids: list[int],
        monster_ids: list[str],
    ) -> dict[str, str]:
        if self.redis is None:
            return await self._request_actor_snapshots(
                combat_id,
                player_ids=player_ids,
                monster_ids=monster_ids,
            )

        service = ActorStateService(self.actor_snapshots, self.redis)
        result = await service.prepare_snapshots(
            session_id=combat_id,
            player_ids=player_ids,
            monster_ids=monster_ids,
            include={"combat", "status", "runtime", "source"},
        )
        if result.failed_players or result.failed_monsters:
            raise CombatLifecycleError(
                "actor_state snapshot preparation failed: "
                f"failed_players={result.failed_players} failed_monsters={result.failed_monsters}"
            )
        snapshot_keys = result.snapshot_keys
        if not snapshot_keys:
            snapshot_keys = self._fallback_snapshot_keys(combat_id, player_ids=player_ids, monster_ids=monster_ids)
        if not isinstance(snapshot_keys, dict) or not snapshot_keys:
            raise CombatLifecycleError("actor_state snapshot response did not include snapshot_keys")
        return {str(snapshot_id): str(snapshot_key) for snapshot_id, snapshot_key in snapshot_keys.items()}

    async def _request_actor_snapshots(
        self,
        combat_id: str,
        *,
        player_ids: list[int],
        monster_ids: list[str],
    ) -> dict[str, str]:
        response = await self.events.request(
            "actor_state.snapshots_requested",
            {
                "session_id": combat_id,
                "player_ids": json.dumps(player_ids),
                "monster_ids": json.dumps(monster_ids),
                "include": json.dumps(["combat", "status", "runtime", "source"]),
            },
            timeout=self.SNAPSHOT_TIMEOUT_SECONDS,
        )
        if not isinstance(response, dict):
            raise CombatLifecycleError("actor_state snapshot response is invalid")
        if response.get("status") not in ("ok", "partial"):
            raise CombatLifecycleError(str(response.get("error") or "actor_state snapshot preparation failed"))

        snapshot_keys = response.get("snapshot_keys") or {}
        if isinstance(snapshot_keys, str):
            snapshot_keys = json.loads(snapshot_keys)
        if not snapshot_keys:
            snapshot_keys = self._fallback_snapshot_keys(combat_id, player_ids=player_ids, monster_ids=monster_ids)
        if not isinstance(snapshot_keys, dict) or not snapshot_keys:
            raise CombatLifecycleError("actor_state snapshot response did not include snapshot_keys")
        return {str(snapshot_id): str(snapshot_key) for snapshot_id, snapshot_key in snapshot_keys.items()}

    async def load_actor_snapshots(self, snapshot_keys: dict[str, str]) -> dict[str, dict[str, Any]]:
        docs = await self.actor_snapshots.get_snapshots_batch(list(snapshot_keys.values()))
        snapshots: dict[str, dict[str, Any]] = {}
        for snapshot_id, snapshot_key in snapshot_keys.items():
            doc = docs.get(snapshot_key)
            if isinstance(doc, dict):
                snapshots[snapshot_id] = doc
        if len(snapshots) != len(snapshot_keys):
            missing = sorted(set(snapshot_keys) - set(snapshots))
            raise CombatLifecycleError(f"prepared actor snapshots are missing: {missing}")
        return snapshots

    async def link_players_to_combat(self, player_ids: list[int], combat_id: str) -> None:
        for char_id in player_ids:
            await self.character_sessions.set_combat_session(char_id, combat_id)
            if hasattr(self.character_sessions, "set_state"):
                await self.character_sessions.set_state(char_id, CoreDomain.COMBAT)

    async def unlink_players_from_combat(self, player_ids: list[int]) -> None:
        for char_id in player_ids:
            await self.character_sessions.clear_combat_session(char_id)

    async def publish_session_ready(self, payload: dict[str, Any]) -> None:
        await self.events.publish(
            "combat.session_ready",
            self._flat_payload(payload),
            correlation_id=payload.get("correlation_id"),
        )

    async def publish_session_failed(self, payload: dict[str, Any]) -> None:
        await self.events.publish(
            "combat.session_failed",
            self._flat_payload(payload),
            correlation_id=payload.get("correlation_id"),
        )

    def _fallback_snapshot_keys(
        self,
        combat_id: str,
        *,
        player_ids: list[int],
        monster_ids: list[str],
    ) -> dict[str, str]:
        return {
            **{
                f"{combat_id}:player:{player_id}": self.actor_snapshots.build_key(f"{combat_id}:player:{player_id}")
                for player_id in player_ids
            },
            **{
                f"{combat_id}:monster:{monster_id}": self.actor_snapshots.build_key(f"{combat_id}:monster:{monster_id}")
                for monster_id in monster_ids
            },
        }

    @staticmethod
    def _flat_payload(payload: dict[str, Any]) -> dict[str, Any]:
        flat: dict[str, Any] = {}
        for key, value in payload.items():
            if value is None:
                continue
            flat[key] = json.dumps(value) if isinstance(value, (dict, list)) else value
        return flat

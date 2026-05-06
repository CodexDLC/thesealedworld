from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from src.backend.features.character.events import CharacterEvents
from src.backend.features.character.integrations import CharacterCombatCommitmentIntegration
from src.backend.features.combat.services.lifecycle_service import CombatLifecycleError
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService

    from src.backend.core.bus import GameEventProducer
    from src.backend.features.character.managers import CharacterSessionManager
    from src.backend.infrastructure.actor_commitments import ActorCommitmentManager


class CombatSystemIntegrator:
    """Feature facade over actor commitments, character session, and event boundaries."""

    COMMITMENT_TIMEOUT_SECONDS = 10.0

    def __init__(
        self,
        *,
        actor_commitments: ActorCommitmentManager,
        character_sessions: CharacterSessionManager,
        events: GameEventProducer,
        redis: RedisService | None = None,
    ) -> None:
        self.actor_commitments = actor_commitments
        self.character_sessions = character_sessions
        self.events = events
        self.redis = redis

    async def prepare_actor_commitments(
        self,
        combat_id: str,
        *,
        player_ids: list[int],
        monster_ids: list[str],
    ) -> dict[str, str]:
        if self.redis is None:
            return await self._request_actor_commitments(
                combat_id,
                player_ids=player_ids,
                monster_ids=monster_ids,
            )

        result = await CharacterCombatCommitmentIntegration(
            character_sessions=self.character_sessions,
            commitment_manager=self.actor_commitments,
        ).prepare_commitments(
            scope_id=combat_id,
            player_ids=player_ids,
            monster_ids=monster_ids,
            ttl=300,
        )
        if result.failed_players or result.failed_monsters:
            raise CombatLifecycleError(
                "character combat commitment preparation failed: "
                f"failed_players={result.failed_players} failed_monsters={result.failed_monsters}"
            )
        commitments = result.commitments
        if not commitments:
            commitments = self._fallback_commitments(combat_id, player_ids=player_ids, monster_ids=monster_ids)
        if not isinstance(commitments, dict) or not commitments:
            raise CombatLifecycleError("character combat commitment response did not include commitments")
        return {str(snapshot_id): str(commitment_id) for snapshot_id, commitment_id in commitments.items()}

    async def _request_actor_commitments(
        self,
        combat_id: str,
        *,
        player_ids: list[int],
        monster_ids: list[str],
    ) -> dict[str, str]:
        response = await self.events.request(
            CharacterEvents.COMBAT_COMMITMENTS_REQUESTED,
            {
                "scope_id": combat_id,
                "player_ids": json.dumps(player_ids),
                "monster_ids": json.dumps(monster_ids),
                "include": json.dumps(["combat", "status", "runtime", "source"]),
            },
            timeout=self.COMMITMENT_TIMEOUT_SECONDS,
        )
        if not isinstance(response, dict):
            raise CombatLifecycleError("character combat commitment response is invalid")
        if response.get("status") not in ("ok", "partial"):
            raise CombatLifecycleError(str(response.get("error") or "character combat commitment preparation failed"))

        commitments = response.get("commitments") or {}
        if isinstance(commitments, str):
            commitments = json.loads(commitments)
        if not commitments:
            commitments = self._fallback_commitments(combat_id, player_ids=player_ids, monster_ids=monster_ids)
        if not isinstance(commitments, dict) or not commitments:
            raise CombatLifecycleError("character combat commitment response did not include commitments")
        return {str(snapshot_id): str(commitment_id) for snapshot_id, commitment_id in commitments.items()}

    async def load_actor_commitments(self, commitments: dict[str, str]) -> dict[str, dict[str, Any]]:
        docs = await self.actor_commitments.get_commitments_batch(list(commitments.values()))
        snapshots: dict[str, dict[str, Any]] = {}
        for snapshot_id, commitment_id in commitments.items():
            doc = docs.get(commitment_id)
            if isinstance(doc, dict):
                snapshots[snapshot_id] = doc
        if len(snapshots) != len(commitments):
            missing = sorted(set(commitments) - set(snapshots))
            raise CombatLifecycleError(f"prepared actor commitments are missing: {missing}")
        return snapshots

    async def link_players_to_combat(self, player_ids: list[int], combat_id: str) -> None:
        for char_id in player_ids:
            await self.character_sessions.set_combat_session(char_id, combat_id)
            if hasattr(self.character_sessions, "set_state"):
                await self.character_sessions.set_state(char_id, CoreDomain.COMBAT)

    async def unlink_players_from_combat(self, player_ids: list[int]) -> None:
        for char_id in player_ids:
            await self.character_sessions.clear_combat_session(char_id)

    async def resolve_combat_session_for_character(self, char_id: int) -> str | None:
        session = await self.character_sessions.get_session(char_id)
        combat_id = ((session or {}).get("sessions") or {}).get("combat_id") if isinstance(session, dict) else None
        return str(combat_id) if combat_id else None

    async def recover_missing_combat_session(self, char_id: int, *, combat_id: str | None = None) -> str | None:
        session = await self.character_sessions.get_session(char_id)
        if not isinstance(session, dict):
            return None

        raw_sessions = session.get("sessions")
        sessions = raw_sessions if isinstance(raw_sessions, dict) else {}
        current_combat_id = sessions.get("combat_id")
        current_state = self._state_text(session.get("state"))
        if current_state != CoreDomain.COMBAT.value and not current_combat_id:
            return None

        if combat_id is not None and current_combat_id and str(current_combat_id) != str(combat_id):
            return None

        return_state = self._recover_return_state(session.get("prev_state"))
        await self.character_sessions.patch_fields(
            char_id,
            {
                "$.sessions.combat_id": None,
                "$.prev_state": current_state or CoreDomain.COMBAT.value,
                "$.state": return_state,
            },
        )
        await self.character_sessions.mark_dirty(
            char_id,
            reason="combat_session_missing_recovered",
            paths=["$.prev_state", "$.sessions.combat_id", "$.state"],
        )
        return return_state

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

    def _fallback_commitments(
        self,
        combat_id: str,
        *,
        player_ids: list[int],
        monster_ids: list[str],
    ) -> dict[str, str]:
        return {
            **{f"{combat_id}:player:{player_id}": f"{combat_id}:player:{player_id}" for player_id in player_ids},
            **{f"{combat_id}:monster:{monster_id}": f"{combat_id}:monster:{monster_id}" for monster_id in monster_ids},
        }

    @staticmethod
    def _flat_payload(payload: dict[str, Any]) -> dict[str, Any]:
        flat: dict[str, Any] = {}
        for key, value in payload.items():
            if value is None:
                continue
            flat[key] = json.dumps(value) if isinstance(value, (dict, list)) else value
        return flat

    @staticmethod
    def _recover_return_state(value: Any) -> str:
        state = CombatSystemIntegrator._state_text(value)
        if state and state != CoreDomain.COMBAT.value:
            try:
                return CoreDomain(state).value
            except ValueError:
                pass
        return CoreDomain.EXPLORATION.value

    @staticmethod
    def _state_text(value: Any) -> str | None:
        if value is None:
            return None
        return value.value if isinstance(value, CoreDomain) else str(value)

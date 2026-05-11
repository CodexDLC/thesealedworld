from __future__ import annotations

import json
from dataclasses import dataclass
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
        if not isinstance(commitments, dict) or not commitments:
            raise CombatLifecycleError("character combat commitment response did not include commitments")
        return {str(source_ref): str(actor_id) for source_ref, actor_id in commitments.items()}

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
        if not isinstance(commitments, dict) or not commitments:
            raise CombatLifecycleError("character combat commitment response did not include commitments")
        return {str(source_ref): str(actor_id) for source_ref, actor_id in commitments.items()}

    async def load_actor_commitments(self, combat_id: str, commitments: dict[str, str]) -> dict[str, dict[str, Any]]:
        docs = await self.actor_commitments.get_snapshots_batch(combat_id, list(commitments.values()))
        snapshots: dict[str, dict[str, Any]] = {}
        for source_ref, actor_id in commitments.items():
            doc = docs.get(actor_id)
            if isinstance(doc, dict):
                snapshots[source_ref] = doc
        if len(snapshots) != len(commitments):
            missing = sorted(set(commitments) - set(snapshots))
            raise CombatLifecycleError(f"prepared actor snapshots are missing: {missing}")
        return snapshots

    def source_ref(self, actor_type: str, source_id: int | str) -> str:
        if actor_type not in {"player", "monster"}:
            raise ValueError(f"Unsupported combat actor type: {actor_type}")
        return self.actor_commitments.source_ref(actor_type, source_id)  # type: ignore[arg-type]

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

    async def resolve_combat_finalization_for_character(self, char_id: int) -> str | None:
        session = await self.character_sessions.get_session(char_id)
        finalization_id = (
            ((session or {}).get("sessions") or {}).get("combat_finalization_id") if isinstance(session, dict) else None
        )
        return str(finalization_id) if finalization_id else None

    async def mark_combat_finalized(self, char_id: int, combat_id: str) -> None:
        session = await self.character_sessions.get_session(char_id)
        if not isinstance(session, dict):
            return

        updates = {
            "$.sessions.combat_id": None,
            "$.sessions.combat_finalization_id": str(combat_id),
            "$.state": CoreDomain.COMBAT_RESULT.value,
        }
        await self.character_sessions.patch_fields(char_id, updates)
        await self.character_sessions.mark_dirty(
            char_id,
            reason="combat_session_finalized",
            paths=sorted(updates),
        )

    async def recover_missing_combat_session(self, char_id: int, *, combat_id: str | None = None) -> str | None:
        return await self._return_from_combat(
            char_id,
            combat_id=combat_id,
            dirty_reason="combat_session_missing_recovered",
        )

    async def complete_combat_session_return(self, char_id: int, *, combat_id: str | None = None) -> str | None:
        return await self._return_from_combat(
            char_id,
            combat_id=combat_id,
            dirty_reason="combat_session_finalized_returned",
            sync_to_db=True,
        )

    async def _return_from_combat(
        self,
        char_id: int,
        *,
        combat_id: str | None = None,
        dirty_reason: str,
        sync_to_db: bool = False,
    ) -> str | None:
        session = await self.character_sessions.get_session(char_id)
        if not isinstance(session, dict):
            return None

        raw_sessions = session.get("sessions")
        sessions = raw_sessions if isinstance(raw_sessions, dict) else {}
        current_combat_id = sessions.get("combat_id")
        current_finalization_id = sessions.get("combat_finalization_id")
        current_state = self._state_text(session.get("state"))
        if current_state not in {CoreDomain.COMBAT.value, CoreDomain.COMBAT_RESULT.value} and not (
            current_combat_id or current_finalization_id
        ):
            return None

        if (
            combat_id is not None
            and (current_combat_id or current_finalization_id)
            and str(current_combat_id or current_finalization_id) != str(combat_id)
        ):
            return None

        return_path = CombatReturnStateMapper.from_combat_previous(session.get("prev_state"))
        await self.character_sessions.patch_fields(
            char_id,
            {
                "$.sessions.combat_id": None,
                "$.sessions.combat_finalization_id": None,
                "$.prev_state": return_path.previous_state,
                "$.state": return_path.current_state,
            },
        )
        await self.character_sessions.mark_dirty(
            char_id,
            reason=dirty_reason,
            paths=["$.prev_state", "$.sessions.combat_finalization_id", "$.sessions.combat_id", "$.state"],
        )
        if sync_to_db:
            await self._sync_active_character_to_db(char_id)
        return return_path.current_state

    async def resolve_return_state_for_character(self, char_id: int) -> str:
        session = await self.character_sessions.get_session(char_id)
        if not isinstance(session, dict):
            return CoreDomain.EXPLORATION.value

        current_state = self._state_text(session.get("state"))
        if current_state in {CoreDomain.COMBAT.value, CoreDomain.COMBAT_RESULT.value}:
            return CombatReturnStateMapper.from_combat_previous(session.get("prev_state")).current_state
        return CombatReturnStateMapper.normalize_current(current_state)

    async def _sync_active_character_to_db(self, char_id: int) -> None:
        request = getattr(self.events, "request", None)
        if request is None:
            return
        response = await request(
            CharacterEvents.ACTIVE_SESSION_SYNC_REQUESTED,
            {"char_id": char_id},
            timeout=30.0,
        )
        if isinstance(response, dict) and response.get("status") == "error":
            raise RuntimeError(str(response.get("error") or "character active session sync failed"))

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
        return CombatReturnStateMapper.from_combat_previous(value).current_state

    @staticmethod
    def _state_text(value: Any) -> str | None:
        if value is None:
            return None
        return value.value if isinstance(value, CoreDomain) else str(value)


@dataclass(frozen=True)
class CombatReturnPath:
    current_state: str
    previous_state: str | None


class CombatReturnStateMapper:
    """Maps stale combat sessions back into the surrounding gameplay state."""

    PARENT_BY_STATE = {
        CoreDomain.ARENA.value: CoreDomain.EXPLORATION.value,
        CoreDomain.SCENARIO.value: CoreDomain.EXPLORATION.value,
        CoreDomain.INVENTORY.value: CoreDomain.EXPLORATION.value,
        CoreDomain.STATUS.value: CoreDomain.EXPLORATION.value,
        CoreDomain.WORLD.value: CoreDomain.EXPLORATION.value,
    }

    @classmethod
    def from_combat_previous(cls, value: Any) -> CombatReturnPath:
        current_state = cls.normalize_current(value)
        return CombatReturnPath(
            current_state=current_state,
            previous_state=cls.PARENT_BY_STATE.get(current_state),
        )

    @classmethod
    def normalize_current(cls, value: Any) -> str:
        state = cls._state_text(value)
        if state and state not in {CoreDomain.COMBAT.value, CoreDomain.COMBAT_RESULT.value}:
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

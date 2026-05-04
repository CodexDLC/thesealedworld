from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.features.combat.services.lifecycle_service import CombatLifecycleError

if TYPE_CHECKING:
    from src.backend.features.combat.integrations import CombatSystemIntegrator
    from src.backend.features.combat.services.lifecycle_service import CombatLifecycleService


class CombatCreationOrchestrator:
    """Coordinates stream-facing combat session creation."""

    def __init__(self, *, lifecycle: CombatLifecycleService, integrator: CombatSystemIntegrator) -> None:
        self.lifecycle = lifecycle
        self.integrator = integrator

    async def create_from_request(self, request: dict[str, Any]) -> dict[str, Any]:
        source = str(request.get("source") or "unknown")
        battle_type = str(request.get("battle_type") or request.get("mode") or "arena")
        combat_id = str(request.get("combat_id") or uuid.uuid4())
        participants = self.lifecycle.prepare_participants(request, battle_type=battle_type)

        if battle_type == "shadow" or self.lifecycle.is_shadow_participants(request, participants):
            participants = self.lifecycle.shadow_participants(request, participants)
            battle_type = "shadow"

        player_ids = self.lifecycle.player_snapshot_ids(participants)
        monster_ids = self.lifecycle.monster_snapshot_ids(participants)
        if not player_ids:
            raise CombatLifecycleError("combat session requires at least one player snapshot")

        snapshot_keys = await self.integrator.prepare_actor_snapshots(
            combat_id,
            player_ids=player_ids,
            monster_ids=monster_ids,
        )
        snapshots = await self.integrator.load_actor_snapshots(snapshot_keys)
        await self.lifecycle.create_session_from_snapshots(
            combat_id,
            battle_type=battle_type,
            participants=participants,
            snapshots=snapshots,
            request=request,
        )
        if not self._should_defer_player_link(request):
            await self.integrator.link_players_to_combat(player_ids, combat_id)

        ready = {
            "status": "ready",
            "source": source,
            "combat_id": combat_id,
            "battle_type": battle_type,
            "participants": participants,
            "requested_by": request.get("requested_by"),
            "arena_session_id": request.get("arena_session_id"),
            "correlation_id": request.get("correlation_id"),
        }
        await self.integrator.publish_session_ready(ready)
        logger.info("Combat lifecycle ready: combat_id={} source={}", combat_id, source)
        return ready

    async def fail_request(self, request: dict[str, Any], error: str) -> dict[str, Any]:
        failed = {
            "status": "failed",
            "source": request.get("source") or "unknown",
            "combat_id": request.get("combat_id"),
            "arena_session_id": request.get("arena_session_id"),
            "requested_by": request.get("requested_by"),
            "error": error,
            "correlation_id": request.get("correlation_id"),
        }
        await self.integrator.publish_session_failed(failed)
        return failed

    @staticmethod
    def _should_defer_player_link(request: dict[str, Any]) -> bool:
        metadata = request.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        return request.get("battle_type") == "shadow" and bool(metadata.get("awaiting_player_choice"))

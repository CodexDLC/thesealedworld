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
            raise CombatLifecycleError("combat session requires at least one player commitment")

        commitments = self._provided_commitments(combat_id, participants, request)
        missing_player_ids = [
            player_id for player_id in player_ids if f"{combat_id}:player:{player_id}" not in commitments
        ]
        missing_monster_ids = [
            monster_id for monster_id in monster_ids if f"{combat_id}:monster:{monster_id}" not in commitments
        ]
        if missing_player_ids or missing_monster_ids:
            commitments.update(
                await self.integrator.prepare_actor_commitments(
                    combat_id,
                    player_ids=missing_player_ids,
                    monster_ids=missing_monster_ids,
                )
            )
        snapshots = await self.integrator.load_actor_commitments(commitments)
        await self.lifecycle.create_session_from_snapshots(
            combat_id,
            battle_type=battle_type,
            participants=participants,
            snapshots=snapshots,
            request=request,
        )
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

    def _provided_commitments(
        self,
        combat_id: str,
        participants: dict[str, list[int | str]],
        request: dict[str, Any],
    ) -> dict[str, str]:
        raw = request.get("commitments") or {}
        if isinstance(raw, str):
            raw = json.loads(raw)
        if not isinstance(raw, dict) or not raw:
            return {}

        mapped: dict[str, str] = {}
        for team_members in participants.values():
            for raw_member in team_members:
                value = str(raw_member)
                actor_id = value[1:] if value.startswith("-") and value[1:].isdigit() else value
                if actor_id.isdigit():
                    commitment_id = raw.get(actor_id) or raw.get(f"player:{actor_id}")
                    if commitment_id:
                        mapped[f"{combat_id}:player:{actor_id}"] = str(commitment_id)
                    continue

                commitment_id = raw.get(actor_id) or raw.get(f"monster:{actor_id}")
                if commitment_id:
                    mapped[f"{combat_id}:monster:{actor_id}"] = str(commitment_id)

        if mapped:
            return mapped

        return {str(snapshot_id): str(commitment_id) for snapshot_id, commitment_id in raw.items() if commitment_id}

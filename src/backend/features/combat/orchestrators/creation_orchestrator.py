from __future__ import annotations

import json
import uuid
from time import perf_counter
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.features.combat.services.lifecycle_service import CombatLifecycleError

if TYPE_CHECKING:
    from src.backend.features.combat.integrations import CombatSystemIntegrator
    from src.backend.features.combat.services.lifecycle_service import CombatLifecycleService


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 2)


class CombatCreationOrchestrator:
    """Coordinates stream-facing combat session creation."""

    def __init__(self, *, lifecycle: CombatLifecycleService, integrator: CombatSystemIntegrator) -> None:
        self.lifecycle = lifecycle
        self.integrator = integrator

    async def create_from_request(self, request: dict[str, Any]) -> dict[str, Any]:
        total_started_at = perf_counter()
        source = str(request.get("source") or "unknown")
        battle_type = str(request.get("battle_type") or request.get("mode") or "arena")
        combat_id = str(request.get("combat_id") or uuid.uuid4())
        step_started_at = perf_counter()
        participants = self.lifecycle.prepare_participants(request, battle_type=battle_type)

        if battle_type == "shadow" or self.lifecycle.is_shadow_participants(request, participants):
            participants = self.lifecycle.shadow_participants(request, participants)
            battle_type = "shadow"
        logger.info(
            "CombatCreationTiming | step=prepare_participants combat_id={} source={} battle_type={} ms={}",
            combat_id,
            source,
            battle_type,
            _elapsed_ms(step_started_at),
        )

        player_ids = self.lifecycle.player_snapshot_ids(participants)
        monster_ids = self.lifecycle.monster_snapshot_ids(participants)
        if not player_ids:
            raise CombatLifecycleError("combat session requires at least one player commitment")

        step_started_at = perf_counter()
        commitments = self._provided_commitments(participants, request)
        logger.info(
            "CombatCreationTiming | step=provided_commitments combat_id={} commitment_count={} ms={}",
            combat_id,
            len(commitments),
            _elapsed_ms(step_started_at),
        )
        missing_player_ids = [
            player_id for player_id in player_ids if self.integrator.source_ref("player", player_id) not in commitments
        ]
        missing_monster_ids = [
            monster_id
            for monster_id in monster_ids
            if self.integrator.source_ref("monster", monster_id) not in commitments
        ]
        if missing_player_ids or missing_monster_ids:
            step_started_at = perf_counter()
            commitments.update(
                await self.integrator.prepare_actor_commitments(
                    combat_id,
                    player_ids=missing_player_ids,
                    monster_ids=missing_monster_ids,
                )
            )
            logger.info(
                "CombatCreationTiming | step=prepare_missing_commitments combat_id={} missing_players={} "
                "missing_monsters={} ms={}",
                combat_id,
                len(missing_player_ids),
                len(missing_monster_ids),
                _elapsed_ms(step_started_at),
            )
        step_started_at = perf_counter()
        snapshots = await self.integrator.load_actor_commitments(commitments)
        logger.info(
            "CombatCreationTiming | step=load_actor_commitments combat_id={} commitment_count={} snapshot_count={} "
            "ms={}",
            combat_id,
            len(commitments),
            len(snapshots),
            _elapsed_ms(step_started_at),
        )
        step_started_at = perf_counter()
        await self.lifecycle.create_session_from_snapshots(
            combat_id,
            battle_type=battle_type,
            participants=participants,
            snapshots=snapshots,
            request=request,
        )
        logger.info(
            "CombatCreationTiming | step=create_session_from_snapshots combat_id={} actor_count={} ms={}",
            combat_id,
            sum(len(members) for members in participants.values()),
            _elapsed_ms(step_started_at),
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
        step_started_at = perf_counter()
        await self.integrator.publish_session_ready(ready)
        logger.info(
            "CombatCreationTiming | step=publish_session_ready combat_id={} ms={}",
            combat_id,
            _elapsed_ms(step_started_at),
        )
        logger.info(
            "CombatCreationTiming | step=total combat_id={} source={} battle_type={} ms={}",
            combat_id,
            source,
            battle_type,
            _elapsed_ms(total_started_at),
        )
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
                    source_ref = self.integrator.source_ref("player", actor_id)
                    commitment_id = raw.get(source_ref)
                    if commitment_id:
                        mapped[source_ref] = str(commitment_id)
                    continue

                source_ref = self.integrator.source_ref("monster", actor_id)
                commitment_id = raw.get(source_ref)
                if commitment_id:
                    mapped[source_ref] = str(commitment_id)

        return mapped

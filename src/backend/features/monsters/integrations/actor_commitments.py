from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.infrastructure.actor_commitments import ActorCommitmentManager


class MonsterActorCommitmentIntegration:
    """Writes monster-owned actor source documents into temporary actor commitments."""

    def __init__(self, commitment_manager: ActorCommitmentManager) -> None:
        self.commitment_manager = commitment_manager

    async def save_monster_sources(
        self,
        *,
        scope_id: str,
        sources: list[dict[str, Any]],
        ttl: int,
    ) -> dict[str, str]:
        refs_by_actor_id: dict[str, str] = {}
        snapshots: dict[str, dict[str, Any]] = {}
        for source in sources:
            source_data = source.get("source")
            if not isinstance(source_data, dict) or not source_data.get("monster_id"):
                continue
            monster_id = str(source_data["monster_id"])
            actor_id = self.commitment_manager.actor_uuid(scope_id, "monster", monster_id)
            refs_by_actor_id[actor_id] = self.commitment_manager.source_ref("monster", monster_id)
            snapshots[actor_id] = source

        saved = await self.commitment_manager.save_snapshots(scope_id, snapshots, ttl=ttl)
        return {source_ref: actor_id for actor_id, source_ref in refs_by_actor_id.items() if actor_id in saved}

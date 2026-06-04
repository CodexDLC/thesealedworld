from __future__ import annotations

from typing import Any

from src.backend.features.monsters.dto.generated_view import (
    MonsterDataRebuildItemDTO,
    MonsterDataRebuildRequestDTO,
    MonsterDataRebuildResponseDTO,
)


class MonsterGeneratedRebuildService:
    """Legacy generated monster rebuilds are disabled for replacement-only storage."""

    def __init__(self, *, session: Any, item_generation: Any | None = None) -> None:
        del session, item_generation

    async def plan(self, request: MonsterDataRebuildRequestDTO) -> MonsterDataRebuildResponseDTO:
        return _disabled_response(request, dry_run=True)

    async def apply(self, request: MonsterDataRebuildRequestDTO) -> MonsterDataRebuildResponseDTO:
        return _disabled_response(request, dry_run=False)


def _disabled_response(request: MonsterDataRebuildRequestDTO, *, dry_run: bool) -> MonsterDataRebuildResponseDTO:
    scope = request.clan_id or request.family_id or "all"
    return MonsterDataRebuildResponseDTO(
        dry_run=dry_run,
        status="disabled",
        scanned=0,
        stale=0,
        rebuilt=0,
        skipped=0,
        errors=["Generated monster rebuild/backfill is disabled by the replacement-only storage contract."],
        items=[
            MonsterDataRebuildItemDTO(
                clan_id=str(scope),
                family_id=str(request.family_id or ""),
                status="disabled",
                reason="replacement-only contract forbids rebuild/backfill",
            )
        ],
    )


__all__ = ["MonsterGeneratedRebuildService"]

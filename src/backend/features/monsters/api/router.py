from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.backend.core.database import get_db
from src.backend.features.monsters.dto.generated_view import (
    GeneratedMonstersResponseDTO,
    GeneratedMonstersSummaryDTO,
    MonsterAIRegenerationResponseDTO,
    MonsterDataRebuildRequestDTO,
    MonsterDataRebuildResponseDTO,
    MonsterImageRegenerationBatchRequestDTO,
    MonsterImageRegenerationBatchResponseDTO,
    MonsterImageRegenerationResponseDTO,
)
from src.backend.features.monsters.repositories import MonsterGenerationRepository
from src.backend.features.monsters.services.content_regeneration_service import MonsterContentRegenerationService
from src.backend.features.monsters.services.generated_rebuild_service import MonsterGeneratedRebuildService
from src.backend.features.monsters.services.generated_view_service import GeneratedMonsterViewService
from src.backend.features.monsters.services.visual_regeneration_service import MonsterVisualRegenerationService

router = APIRouter(prefix="/api/admin/monsters", tags=["monsters-admin"])


def get_generated_monster_view_service(db_session=Depends(get_db)) -> GeneratedMonsterViewService:
    return GeneratedMonsterViewService(MonsterGenerationRepository(db_session))


def get_monster_visual_regeneration_service(
    request: Request,
    db_session=Depends(get_db),
) -> MonsterVisualRegenerationService:
    return MonsterVisualRegenerationService(
        session=db_session,
        arq=getattr(request.app.state, "generation_ai_arq", None),
    )


def get_monster_content_regeneration_service(
    request: Request,
    db_session=Depends(get_db),
) -> MonsterContentRegenerationService:
    return MonsterContentRegenerationService(
        session=db_session,
        arq=getattr(request.app.state, "generation_ai_arq", None),
    )


def get_monster_generated_rebuild_service(db_session=Depends(get_db)) -> MonsterGeneratedRebuildService:
    return MonsterGeneratedRebuildService(session=db_session)


@router.get("/generated", response_model=GeneratedMonstersResponseDTO)
async def get_generated_monsters(
    service: Annotated[GeneratedMonsterViewService, Depends(get_generated_monster_view_service)],
    family_id: str | None = None,
    clan_id: str | None = None,
    role: str | None = None,
    include_members: bool = True,
    light: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GeneratedMonstersResponseDTO:
    return await service.list_generated(
        family_id=family_id,
        clan_id=clan_id,
        role=role,
        include_members=include_members,
        light=light,
        limit=limit,
        offset=offset,
    )


@router.get("/generated/summary", response_model=GeneratedMonstersSummaryDTO)
async def get_generated_monsters_summary(
    service: Annotated[GeneratedMonsterViewService, Depends(get_generated_monster_view_service)],
    family_id: str | None = None,
) -> GeneratedMonstersSummaryDTO:
    return await service.summary(family_id=family_id)


@router.post("/generated/rebuild/plan", response_model=MonsterDataRebuildResponseDTO)
async def plan_generated_monster_rebuild(
    payload: MonsterDataRebuildRequestDTO,
    service: Annotated[MonsterGeneratedRebuildService, Depends(get_monster_generated_rebuild_service)],
) -> MonsterDataRebuildResponseDTO:
    try:
        return await service.plan(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/generated/rebuild/apply", response_model=MonsterDataRebuildResponseDTO)
async def apply_generated_monster_rebuild(
    payload: MonsterDataRebuildRequestDTO,
    service: Annotated[MonsterGeneratedRebuildService, Depends(get_monster_generated_rebuild_service)],
) -> MonsterDataRebuildResponseDTO:
    try:
        return await service.apply(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/generated/clans/{clan_id}/regenerate-flavor", response_model=MonsterAIRegenerationResponseDTO)
async def regenerate_generated_clan_flavor(
    clan_id: str,
    service: Annotated[MonsterContentRegenerationService, Depends(get_monster_content_regeneration_service)],
) -> MonsterAIRegenerationResponseDTO:
    try:
        return await service.request_clan_flavor(clan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/generated/clans/{clan_id}/regenerate-member-images",
    response_model=MonsterImageRegenerationBatchResponseDTO,
)
async def regenerate_generated_clan_member_images(
    clan_id: str,
    service: Annotated[MonsterVisualRegenerationService, Depends(get_monster_visual_regeneration_service)],
) -> MonsterImageRegenerationBatchResponseDTO:
    try:
        return await service.request_clan_member_images(clan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/generated/clans/regenerate-member-images", response_model=MonsterImageRegenerationBatchResponseDTO)
async def regenerate_generated_clan_member_images_batch(
    payload: MonsterImageRegenerationBatchRequestDTO,
    service: Annotated[MonsterVisualRegenerationService, Depends(get_monster_visual_regeneration_service)],
) -> MonsterImageRegenerationBatchResponseDTO:
    try:
        return await service.request_clan_member_images_for_clans(payload.clan_ids)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/generated/members/{member_id}/regenerate-image", response_model=MonsterImageRegenerationResponseDTO)
async def regenerate_generated_member_image(
    member_id: str,
    service: Annotated[MonsterVisualRegenerationService, Depends(get_monster_visual_regeneration_service)],
) -> MonsterImageRegenerationResponseDTO:
    try:
        return await service.request_member_image(member_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


__all__ = [
    "get_generated_monster_view_service",
    "get_monster_content_regeneration_service",
    "get_monster_generated_rebuild_service",
    "get_monster_visual_regeneration_service",
    "router",
]

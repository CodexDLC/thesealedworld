from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from codex_core.common.log_context import clear_log_context, set_log_context
from codex_platform.streams import StreamRouter
from loguru import logger

from src.backend.core.database.session import get_manual_session_context
from src.backend.features.generation_ai.bootstrap import build_generation_ai_registry
from src.backend.features.generation_ai.repositories import AIGenerationTaskRepository
from src.backend.features.generation_ai.services import GenerationAIService
from src.backend.features.items.integrations import ItemPersistenceIntegration
from src.backend.features.items.repositories import ItemInstanceRepository
from src.backend.features.items.services import ItemGenerationService
from src.backend.features.monsters.integrations import (
    MonsterActorCommitmentIntegration,
    MonsterLocationContextIntegration,
)
from src.backend.features.monsters.repositories import MonsterGenerationRepository
from src.backend.features.monsters.runtime import ClanFactory, MonsterClanGenerationBuilder
from src.backend.features.monsters.services import MonsterGroupService
from src.backend.infrastructure.monsters.managers import MonsterGroupCacheManager

if TYPE_CHECKING:
    from fastapi import FastAPI

router = StreamRouter()
_app: FastAPI | None = None


def with_log_context(
    handler: Callable[[dict[str, Any]], Awaitable[None]],
) -> Callable[[dict[str, Any]], Awaitable[None]]:
    async def wrapped(payload: dict[str, Any]) -> None:
        set_log_context(correlation_id=payload.get("correlation_id"))
        try:
            await handler(payload)
        finally:
            clear_log_context()

    return wrapped


class MonsterEvents:
    GROUP_PREPARE_REQUESTED = "monsters.group_prepare_requested"
    GROUP_PREPARED = "monsters.group_prepared"
    GROUP_PREPARE_FAILED = "monsters.group_prepare_failed"


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on(MonsterEvents.GROUP_PREPARE_REQUESTED, group="monsters", reply=True)
@with_log_context
async def on_group_prepare_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        logger.warning("MonsterGroupPrepareIgnored")
        return

    try:
        loc_id = str(payload["loc_id"])
        budget = float(payload["budget"])
        preferred_family_id = _optional_str(payload.get("preferred_family_id"))
        force_single_family = _bool(payload.get("force_single_family"), default=True)
        threat_mitigation_skill = _float(payload.get("threat_mitigation_skill"), default=0.0)
        scope_id = _optional_str(payload.get("scope_id"))
        ttl = int(payload.get("ttl") or 300)

        async with get_manual_session_context() as session:
            monster_repository = MonsterGenerationRepository(session)
            item_generation = ItemGenerationService(
                ItemPersistenceIntegration(ItemInstanceRepository(session)),
            )
            generation_ai = GenerationAIService(
                repository=AIGenerationTaskRepository(session),
                registry=build_generation_ai_registry(session=session),
                arq=getattr(_app.state, "generation_ai_arq", None),
                auto_schedule=False,
            )
            service = MonsterGroupService(  # type: ignore
                repository=monster_repository,
                location_context=MonsterLocationContextIntegration(_app.state.world_locations),
                actor_commitments=MonsterActorCommitmentIntegration(_app.state.actor_commitments),
                group_cache=MonsterGroupCacheManager(_app.state.redis),
                factory=ClanFactory(  # type: ignore
                    MonsterClanGenerationBuilder(  # type: ignore
                        repository=monster_repository,
                        item_generation=item_generation,
                        generation_ai=generation_ai,
                    ),
                ),
            )
            result = await service.prepare_monster_group(
                loc_id=loc_id,
                budget=budget,
                preferred_family_id=preferred_family_id,
                force_single_family=force_single_family,
                threat_mitigation_skill=threat_mitigation_skill,
                scope_id=scope_id,
                ttl=ttl,
            )
            await session.commit()
            await generation_ai.schedule_pending_task_ids()

        ack: dict[str, Any] = {"status": "ok", "payload": result.model_dump(mode="json")}
        await _app.state.events.publish(MonsterEvents.GROUP_PREPARED, ack, correlation_id=cid)
    except Exception as exc:  # noqa: BLE001
        logger.exception("MonsterGroupPrepareFailed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(MonsterEvents.GROUP_PREPARE_FAILED, {"request": payload, **ack})
        except Exception:
            logger.exception("MonsterGroupPrepareFailureEventDeliveryFailed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            logger.exception("MonsterGroupPrepareAckDeliveryFailed")


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


__all__ = ["MonsterEvents", "bind", "router"]

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from codex_platform.streams import StreamRouter

from src.backend.core.database.session import get_session_context
from src.backend.features.generation_ai.bootstrap import build_generation_ai_registry
from src.backend.features.generation_ai.repositories import AIGenerationTaskRepository
from src.backend.features.generation_ai.services import GenerationAIService
from src.backend.features.items.integrations import ItemPersistenceIntegration, ItemTextAIClient
from src.backend.features.items.repositories import ItemInstanceRepository
from src.backend.features.items.services import ItemGenerationService
from src.backend.features.monsters.integrations import (
    MonsterActorCommitmentIntegration,
    MonsterGroupCacheIntegration,
    MonsterLocationContextIntegration,
)
from src.backend.features.monsters.repositories import MonsterGenerationRepository
from src.backend.features.monsters.runtime import MonsterClanGenerationBuilder
from src.backend.features.monsters.services import MonsterGroupService

if TYPE_CHECKING:
    from fastapi import FastAPI

router = StreamRouter()
_app: FastAPI | None = None
log = logging.getLogger(__name__)


class MonsterEvents:
    GROUP_PREPARE_REQUESTED = "monsters.group_prepare_requested"
    GROUP_PREPARED = "monsters.group_prepared"
    GROUP_PREPARE_FAILED = "monsters.group_prepare_failed"


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on(MonsterEvents.GROUP_PREPARE_REQUESTED, group="monsters", reply=True)
async def on_group_prepare_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        log.warning("Monster group prepare ignored: app_not_bound cid=%s", cid)
        return

    try:
        loc_id = str(payload["loc_id"])
        budget = float(payload["budget"])
        preferred_family_id = _optional_str(payload.get("preferred_family_id"))
        force_single_family = _bool(payload.get("force_single_family"), default=True)
        scope_id = _optional_str(payload.get("scope_id"))
        ttl = int(payload.get("ttl") or 300)

        async with get_session_context() as session:
            monster_repository = MonsterGenerationRepository(session)
            item_generation = ItemGenerationService(
                ItemPersistenceIntegration(ItemInstanceRepository(session)),
                ItemTextAIClient(getattr(_app.state, "ai", None)),
            )
            service = MonsterGroupService(
                repository=monster_repository,
                location_context=MonsterLocationContextIntegration(_app.state.world_locations),
                actor_commitments=MonsterActorCommitmentIntegration(_app.state.actor_commitments),
                group_cache=MonsterGroupCacheIntegration(_app.state.redis),
                generator=MonsterClanGenerationBuilder(
                    repository=monster_repository,
                    item_generation=item_generation,
                    generation_ai=GenerationAIService(
                        repository=AIGenerationTaskRepository(session),
                        registry=build_generation_ai_registry(session=session),
                        arq=getattr(_app.state, "generation_ai_arq", None),
                    ),
                ),
            )
            result = await service.prepare_monster_group(
                loc_id=loc_id,
                budget=budget,
                preferred_family_id=preferred_family_id,
                force_single_family=force_single_family,
                scope_id=scope_id,
                ttl=ttl,
            )

        ack: dict[str, Any] = {"status": "ok", "payload": result.model_dump(mode="json")}
        await _app.state.events.publish(MonsterEvents.GROUP_PREPARED, ack, correlation_id=cid)
    except Exception as exc:  # noqa: BLE001
        log.exception("Monster group prepare failed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(MonsterEvents.GROUP_PREPARE_FAILED, {"request": payload, **ack})
        except Exception:
            log.exception("Monster group prepare failure event delivery failed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            log.exception("Monster group prepare ack delivery failed: cid=%s", cid)


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


__all__ = ["MonsterEvents", "bind", "router"]

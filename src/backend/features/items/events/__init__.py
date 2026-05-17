from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from codex_platform.streams import StreamRouter

from src.backend.core.database.session import get_manual_session_context, get_session_context
from src.backend.features.generation_ai.bootstrap import build_generation_ai_registry
from src.backend.features.generation_ai.repositories import AIGenerationTaskRepository
from src.backend.features.generation_ai.services import GenerationAIService
from src.backend.features.items.dto.instance import ItemGenerationBatchRequestDTO, ItemGenerationRequestDTO
from src.backend.features.items.events.publisher import ItemEvents
from src.backend.features.items.integrations import ItemPersistenceIntegration
from src.backend.features.items.repositories import ItemInstanceRepository
from src.backend.features.items.resources.item_grade import GRADE_BY_RARITY_TIER
from src.backend.features.items.services import ItemGenerationService
from src.backend.features.items.tasks_ai import build_item_text_task_spec

if TYPE_CHECKING:
    from fastapi import FastAPI

router = StreamRouter()
_app: FastAPI | None = None
log = logging.getLogger(__name__)


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on(ItemEvents.GENERATE_REQUESTED, group="items", reply=True)
async def on_generate_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        log.warning("Item generation request ignored: app_not_bound cid=%s", cid)
        return

    try:
        requests = _parse_generation_requests(payload)
        async with get_session_context() as session:
            service = _build_generation_service(session)
            result = await service.generate_many(requests)

        ack: dict[str, Any] = {"status": "ok", **result.model_dump(mode="json")}
        await _app.state.events.publish(
            ItemEvents.GENERATED,
            {
                "item_ids": result.item_ids,
                "item": result.items[0].model_dump(mode="json") if result.items and len(result.items) == 1 else None,
                "items": [item.model_dump(mode="json") for item in result.items] if result.items is not None else None,
                "sources": [request.source for request in requests],
                "placement_refs": [
                    request.placement_ref.model_dump(mode="json") if request.placement_ref is not None else None
                    for request in requests
                ],
                "generation_modes": [request.generation_mode for request in requests],
            },
            correlation_id=cid,
        )
        persisted_requests = [request for request in requests if request.generation_mode == "player"]
        for item_id, request in zip(result.item_ids, persisted_requests, strict=True):
            if not _should_request_ai_text(request):
                continue
            await _app.state.events.publish(
                "items.text_requested",
                {"item_id": item_id, "request": request.model_dump(mode="json")},
                correlation_id=cid,
            )
    except Exception as exc:  # noqa: BLE001
        log.exception("Item generation request failed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(
                ItemEvents.GENERATION_FAILED,
                {"request": payload, "error": ack["error"]},
                correlation_id=cid,
            )
        except Exception:
            log.exception("Item generation failure event delivery failed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            log.exception("Item generation ack delivery failed: cid=%s", cid)


def _parse_generation_requests(payload: dict[str, Any]) -> list[ItemGenerationRequestDTO]:
    if "items" in payload:
        batch = ItemGenerationBatchRequestDTO.model_validate(payload)
        return [
            item.model_copy(
                update={
                    "delivery_mode": item.delivery_mode or batch.delivery_mode,
                    "return_item": item.return_item and batch.return_items,
                }
            )
            for item in batch.items
        ]
    return [ItemGenerationRequestDTO.model_validate(payload)]


@router.on("items.text_requested", group="items")
async def on_text_requested(payload: dict[str, Any]) -> None:
    if _app is None:
        log.warning("Item text request ignored: app_not_bound")
        return
    item_id = payload.get("item_id")
    request_payload = payload.get("request")
    if not item_id or not isinstance(request_payload, dict):
        log.warning("Item text request ignored: invalid_payload item_id=%s", item_id)
        return

    request = ItemGenerationRequestDTO.model_validate(request_payload)
    if not _should_request_ai_text(request):
        log.info(
            "Item text request skipped: ai_text_not_allowed item_id=%s rarity_tier=%s",
            item_id,
            request.rarity_tier,
        )
        return
    async with get_manual_session_context() as session:
        generation_ai = GenerationAIService(
            repository=AIGenerationTaskRepository(session),
            registry=build_generation_ai_registry(session=session),
            arq=getattr(_app.state, "generation_ai_arq", None),
            auto_schedule=False,
        )
        await generation_ai.enqueue_many([build_item_text_task_spec(item_id=str(item_id), request=request)])
        await session.commit()
        await generation_ai.schedule_pending_task_ids()


def _build_generation_service(session: Any) -> ItemGenerationService:
    return ItemGenerationService(
        ItemPersistenceIntegration(ItemInstanceRepository(session)),
    )


def _should_request_ai_text(request: ItemGenerationRequestDTO) -> bool:
    if request.generation_mode != "player" or not request.request_ai_text:
        return False
    item_grade = request.item_grade or GRADE_BY_RARITY_TIER.get(request.rarity_tier, "common")
    return item_grade != "common"


__all__ = ["ItemEvents", "bind", "router"]

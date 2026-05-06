from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from codex_platform.streams import StreamRouter

from src.backend.core.database.session import get_session_context
from src.backend.features.items.dto.instance import ItemGenerationBatchRequestDTO, ItemGenerationRequestDTO
from src.backend.features.items.events.publisher import ItemEvents
from src.backend.features.items.integrations import ItemPersistenceIntegration, ItemTextAIClient
from src.backend.features.items.repositories import ItemInstanceRepository
from src.backend.features.items.services import ItemGenerationService

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
            result = await service.generate_many_mechanical(requests)

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
            },
            correlation_id=cid,
        )
        for item_id, request in zip(result.item_ids, requests, strict=True):
            if not request.request_ai_text:
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
    async with get_session_context() as session:
        service = _build_generation_service(session)
        item = await service.enrich_text(str(item_id), request)
    if item is None:
        log.warning("Item text request skipped: item_not_found item_id=%s", item_id)
        return

    await _app.state.events.publish(
        "items.text_generated" if item.metadata.get("ai_text_status") == "generated" else "items.text_failed",
        {"item_id": item_id, "item": item.model_dump(mode="json")},
        correlation_id=payload.get("correlation_id"),
    )


def _build_generation_service(session: Any) -> ItemGenerationService:
    ai = getattr(_app.state, "ai", None) if _app is not None else None
    return ItemGenerationService(
        ItemPersistenceIntegration(ItemInstanceRepository(session)),
        ItemTextAIClient(ai) if ai is not None else None,
    )


__all__ = ["ItemEvents", "bind", "router"]

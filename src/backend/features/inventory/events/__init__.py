from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from codex_core.common.log_context import clear_log_context, set_log_context
from codex_platform.streams import StreamRouter
from loguru import logger

from src.backend.core.database.session import get_session_context
from src.backend.features.inventory.events.publisher import InventoryEvents
from src.backend.features.inventory.integrations import InventoryStreamClient
from src.backend.features.inventory.repositories.items import InventoryItemRepository
from src.backend.features.inventory.services.inventory_service import InventoryService
from src.backend.features.inventory.services.reward_service import InventoryRewardService
from src.backend.infrastructure.inventory.managers import InventorySessionManager

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


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on(InventoryEvents.REWARDS_GRANT_REQUESTED, group="inventory", reply=True)
@with_log_context
async def on_rewards_grant_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        logger.warning("InventoryRewardGrantIgnored")
        return

    try:
        char_id = int(payload["char_id"])
        quest_key = str(payload.get("quest_key") or payload.get("source") or "unknown")
        item_ids = _parse_item_ids(payload) if "item_ids" in payload else None
        base_item_ids = _parse_base_item_ids(payload) if item_ids is None else None
        equip_if_possible = bool(payload.get("equip_if_possible", True))

        async with get_session_context() as session:
            service = _build_reward_service(session)
            result = await service.grant_scenario_rewards(
                char_id=char_id,
                item_ids=item_ids,
                base_item_ids=base_item_ids,
                quest_key=quest_key,
                equip_if_possible=equip_if_possible,
            )

        ack: dict[str, Any] = {"status": "ok", **result.model_dump()}
        await _app.state.events.publish(
            InventoryEvents.REWARDS_GRANTED,
            {
                "char_id": char_id,
                "quest_key": quest_key,
                **result.model_dump(),
            },
            correlation_id=cid,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("InventoryRewardGrantFailed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(
                InventoryEvents.REWARDS_GRANT_FAILED,
                {"request": payload, **ack},
                correlation_id=cid,
            )
        except Exception:
            logger.exception("InventoryRewardGrantFailureEventDeliveryFailed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            logger.exception("InventoryRewardGrantAckDeliveryFailed")


@router.on(InventoryEvents.DURABILITY_DAMAGE_REQUESTED, group="inventory", reply=True)
@with_log_context
async def on_durability_damage_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        logger.warning("InventoryDurabilityDamageIgnored")
        return

    try:
        char_id = int(payload["char_id"])
        async with get_session_context() as session:
            service = _build_inventory_service(session)
            result = await service.apply_durability_damage(
                char_id=char_id,
                amount=float(payload.get("amount") or 0),
                scope=str(payload.get("scope") or "equipped"),
                reason=str(payload.get("reason") or "combat_completed"),
                source=str(payload.get("source") or "combat_finalization"),
                combat_id=str(payload.get("combat_id")) if payload.get("combat_id") else None,
                idempotency_key=str(payload.get("idempotency_key")) if payload.get("idempotency_key") else None,
                metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
            )

        ack: dict[str, Any] = {"status": "ok", **result}
        await _app.state.events.publish(
            InventoryEvents.DURABILITY_DAMAGE_APPLIED,
            {"char_id": char_id, **result},
            correlation_id=cid,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("InventoryDurabilityDamageFailed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(
                InventoryEvents.DURABILITY_DAMAGE_FAILED,
                {"request": payload, **ack},
                correlation_id=cid,
            )
        except Exception:
            logger.exception("InventoryDurabilityDamageFailureEventDeliveryFailed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            logger.exception("InventoryDurabilityDamageAckDeliveryFailed")


def _parse_item_ids(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("item_ids") or []
    if not isinstance(raw, list):
        raise ValueError("Inventory reward grant requires a list of item_ids")
    return [str(item_id) for item_id in raw if item_id]


def _parse_base_item_ids(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("items") or payload.get("base_item_ids") or []
    if not isinstance(raw, list):
        raise ValueError("Inventory reward grant requires a list of items")
    return [str(item_id) for item_id in raw if item_id]


def _build_reward_service(session: Any) -> InventoryRewardService:
    if _app is None:
        raise RuntimeError("Inventory events are not bound to app")

    repository = InventoryItemRepository(session)
    inventory_sessions = InventorySessionManager(_app.state.redis)
    character_sessions = _app.state.character_sessions
    inventory_service = InventoryService(
        repository=repository,
        inventory_sessions=inventory_sessions,
        character_sessions=character_sessions,
        stream_client=InventoryStreamClient(_app.state.events),
    )
    return InventoryRewardService(
        repository=repository,
        inventory_sessions=inventory_sessions,
        inventory_service=inventory_service,
        events=_app.state.events,
    )


def _build_inventory_service(session: Any) -> InventoryService:
    if _app is None:
        raise RuntimeError("Inventory events are not bound to app")
    return InventoryService(
        repository=InventoryItemRepository(session),
        inventory_sessions=InventorySessionManager(_app.state.redis),
        character_sessions=_app.state.character_sessions,
        stream_client=InventoryStreamClient(_app.state.events),
    )


__all__ = ["InventoryEvents", "bind", "router"]

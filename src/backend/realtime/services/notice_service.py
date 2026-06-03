"""Fan-out of ``player.notice`` events to connected realtime sockets.

Runs in the chat container (where the realtime gateway lives). Decodes the
flat, string-safe stream payload, builds the typed browser envelope, and
delivers it to each recipient's live socket. Offline recipients are skipped —
critical state stays fetchable over HTTP, so a missed transient notice is not
an error (gateway non-goals).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from src.backend.realtime.services.connection_manager import RealtimeConnectionManager


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return []
        return decoded if isinstance(decoded, list) else []
    return []


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return {}


class RealtimeNoticeService:
    def __init__(self, manager: RealtimeConnectionManager) -> None:
        self._manager = manager

    async def deliver(self, payload: dict[str, Any]) -> None:
        character_ids = _as_list(payload.get("character_ids"))
        if not character_ids:
            return

        inner: dict[str, Any] = {
            "domain": payload.get("domain", "system"),
            "severity": payload.get("severity") or "info",
        }
        template_key = payload.get("template_key")
        if template_key:
            inner["template_key"] = template_key
            inner["variables"] = _as_dict(payload.get("variables"))
        target = payload.get("target")
        if target:
            inner["target"] = target
        reason = payload.get("reason")
        if reason:
            inner["reason"] = reason

        envelope = {
            "type": "player.notice",
            "presentation": payload.get("presentation") or "system_chat",
            "payload": inner,
        }

        for raw_cid in character_ids:
            try:
                character_id = int(raw_cid)
            except (TypeError, ValueError):
                continue
            await self._manager.send_to_character(character_id, envelope)
        logger.bind(
            presentation=envelope["presentation"],
            template_key=inner.get("template_key"),
            target=inner.get("target"),
            recipients=len(character_ids),
        ).debug("RealtimeNoticeDelivered")

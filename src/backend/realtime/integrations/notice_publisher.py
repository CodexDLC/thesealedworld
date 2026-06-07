"""Outbound contract for the ``player.notice`` realtime event.

Features publish short, player-facing notices ("you died", "searched the
corpse", "entered the safe zone") that render in the classic-MMO system chat.
The backend sends only a ``template_key`` + ``variables`` (data); the frontend
owns the wording and fills the placeholders.

This module is shared because ``player.notice`` is a single cross-feature event
type with one consumer (the realtime gateway in the chat container). Each
feature's service calls a semantic :class:`PlayerNoticePublisher` method through
its own integration/dependency wiring — no feature builds the payload or the
event name by hand, and no feature imports a socket manager.

Two producer backends are supported so the same publisher works in both
execution contexts:

* HTTP/service context — wrap ``app.state.events`` (``GameEventProducer``).
* ARQ-worker context — wrap a raw redis client with
  :class:`RawStreamNoticeProducer` (mirrors ``combat/workers/tasks/chat_announcements.py``).
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from codex_platform.streams.codec import encode_stream_payload

from src.backend.config.settings import settings

PLAYER_NOTICE_EVENT = "player.notice"


class NoticeTemplates:
    """Template keys understood by the frontend notice renderer."""

    COMBAT_STARTED = "combat.started"
    COMBAT_FINISHED = "combat.finished"
    PLAYER_DEATH = "player.death"
    PLAYER_RESPAWN = "player.respawn"
    CORPSE_ITEMS_LOST = "player.corpse_items_lost"
    CORPSE_SEARCHED = "loot.corpse_searched"
    LOOT_CLAIMED = "loot.items_claimed"
    SAFE_ZONE_ENTERED = "exploration.safe_zone_entered"
    ITEMS_SECURED = "expedition.items_secured"


class RefreshTargets:
    """Refresh targets the frontend knows how to re-fetch.

    A ``presentation="refresh"`` notice does not render text; it wakes the UI
    to re-fetch an existing HTMX fragment. The frontend maps each target to the
    DOM event the fragment already listens for (e.g. ``status`` ->
    ``character-status-refresh``). WebSocket delivery stays a wake-up signal —
    the authoritative state is still fetched over HTTP.
    """

    STATUS = "status"


def build_player_notice_payload(
    *,
    character_ids: list[int],
    template_key: str = "",
    variables: dict[str, Any] | None = None,
    presentation: str = "system_chat",
    severity: str = "info",
    domain: str,
    target: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Build the flat, string-safe ``player.notice`` stream payload.

    Complex values (``character_ids``, ``variables``) are JSON-encoded as
    strings so the payload survives the Redis Streams flat-dict contract.
    ``template_key``/``variables`` drive ``system_chat`` rendering;
    ``target``/``reason`` drive ``refresh`` delivery. Unused fields stay empty
    and the realtime service drops them from the browser envelope.
    """
    return {
        "character_ids": json.dumps([int(cid) for cid in character_ids]),
        "template_key": template_key,
        "variables": json.dumps(variables or {}, default=str),
        "presentation": presentation,
        "severity": severity,
        "domain": domain,
        "target": target or "",
        "reason": reason or "",
    }


class _Producer(Protocol):
    async def publish(self, event_type: str, data: dict[str, Any]) -> Any: ...


class RawStreamNoticeProducer:
    """``publish``-compatible adapter over a raw redis client for ARQ workers.

    Workers do not have a :class:`GameEventProducer` on ``app.state``; they hold
    an internal redis client (``ctx["redis_client_internal"]``). This adapter
    writes the same ``player.notice`` event to the game stream the way
    ``combat/workers/tasks/chat_announcements.py`` already does.
    """

    def __init__(self, redis: Any) -> None:
        self._redis = redis

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        await self._redis.xadd(
            settings.game_stream_name,
            encode_stream_payload({"type": event_type, **data}),
            maxlen=settings.game_stream_maxlen,
            approximate=True,
        )


class PlayerNoticePublisher:
    """Semantic publisher for player-facing system-chat notices.

    Feature services call the method matching the event that just happened.
    The publisher owns the ``template_key`` + minimal ``variables`` mapping and
    the event name, keeping transport detail out of feature code.
    """

    def __init__(self, producer: _Producer) -> None:
        self._producer = producer

    async def _emit(
        self,
        *,
        char_id: int,
        template_key: str = "",
        domain: str,
        variables: dict[str, Any] | None = None,
        severity: str = "info",
        presentation: str = "system_chat",
        target: str | None = None,
        reason: str | None = None,
    ) -> None:
        payload = build_player_notice_payload(
            character_ids=[char_id],
            template_key=template_key,
            variables=variables,
            severity=severity,
            domain=domain,
            presentation=presentation,
            target=target,
            reason=reason,
        )
        await self._producer.publish(PLAYER_NOTICE_EVENT, payload)

    async def _emit_many(
        self,
        *,
        char_ids: list[int],
        template_key: str = "",
        domain: str,
        variables: dict[str, Any] | None = None,
        severity: str = "info",
        presentation: str = "system_chat",
        target: str | None = None,
        reason: str | None = None,
    ) -> None:
        if not char_ids:
            return
        payload = build_player_notice_payload(
            character_ids=char_ids,
            template_key=template_key,
            variables=variables,
            severity=severity,
            domain=domain,
            presentation=presentation,
            target=target,
            reason=reason,
        )
        await self._producer.publish(PLAYER_NOTICE_EVENT, payload)

    async def player_died(self, char_id: int) -> None:
        await self._emit(
            char_id=char_id,
            template_key=NoticeTemplates.PLAYER_DEATH,
            domain="expedition",
            severity="danger",
        )

    async def corpse_items_lost(self, char_id: int, count: int | None = None) -> None:
        variables = {"count": int(count)} if count is not None else None
        await self._emit(
            char_id=char_id,
            template_key=NoticeTemplates.CORPSE_ITEMS_LOST,
            domain="expedition",
            variables=variables,
            severity="warning",
        )

    async def player_respawned(self, char_id: int) -> None:
        await self._emit(
            char_id=char_id,
            template_key=NoticeTemplates.PLAYER_RESPAWN,
            domain="expedition",
        )

    async def corpse_searched(self, char_id: int) -> None:
        await self._emit(
            char_id=char_id,
            template_key=NoticeTemplates.CORPSE_SEARCHED,
            domain="loot",
        )

    async def loot_claimed(self, char_id: int, *, summary: str) -> None:
        await self._emit(
            char_id=char_id,
            template_key=NoticeTemplates.LOOT_CLAIMED,
            domain="loot",
            variables={"summary": summary or "добычу"},
        )

    async def safe_zone_entered(self, char_id: int, location_name: str | None = None) -> None:
        variables = {"location": location_name} if location_name else None
        await self._emit(
            char_id=char_id,
            template_key=NoticeTemplates.SAFE_ZONE_ENTERED,
            domain="exploration",
            variables=variables,
        )

    async def items_secured(self, char_id: int, count: int | None = None) -> None:
        variables = {"count": int(count)} if count is not None else None
        await self._emit(
            char_id=char_id,
            template_key=NoticeTemplates.ITEMS_SECURED,
            domain="expedition",
            variables=variables,
        )

    async def combat_started(
        self,
        char_ids: list[int],
        *,
        time_text: str,
        participants: str,
    ) -> None:
        await self._emit_many(
            char_ids=char_ids,
            template_key=NoticeTemplates.COMBAT_STARTED,
            domain="combat",
            variables={"time": time_text, "participants": participants},
            severity="warning",
        )

    async def combat_finished(
        self,
        char_ids: list[int],
        *,
        time_text: str,
        outcome: str,
        participants: str,
    ) -> None:
        await self._emit_many(
            char_ids=char_ids,
            template_key=NoticeTemplates.COMBAT_FINISHED,
            domain="combat",
            variables={"time": time_text, "outcome": outcome, "participants": participants},
            severity="info",
        )

    async def request_refresh(
        self,
        char_id: int,
        *,
        target: str,
        reason: str | None = None,
        domain: str = "system",
    ) -> None:
        """Wake the player's UI to re-fetch an existing HTMX fragment.

        Carries no text — ``presentation="refresh"`` tells the frontend to
        re-fetch ``target`` (e.g. ``status``). Use this for state that changes
        without a direct player request (combat resolved in the background,
        opponent acted, etc.). The fragment stays the source of truth.
        """
        await self._emit(
            char_id=char_id,
            domain=domain,
            presentation="refresh",
            target=target,
            reason=reason,
        )

    async def request_refresh_many(
        self,
        char_ids: list[int],
        *,
        target: str,
        reason: str | None = None,
        domain: str = "system",
    ) -> None:
        """Wake several players' UIs to re-fetch the same existing fragment."""
        await self._emit_many(
            char_ids=char_ids,
            domain=domain,
            presentation="refresh",
            target=target,
            reason=reason,
        )

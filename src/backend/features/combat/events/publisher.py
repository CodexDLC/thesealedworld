from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.core.bus import GameEventProducer


class CombatEventPublisher:
    SESSION_READY = "combat.session_ready"
    SESSION_FAILED = "combat.session_failed"

    def __init__(self, events: GameEventProducer) -> None:
        self.events = events

    async def session_ready(
        self,
        *,
        arena_session_id: str,
        combat_id: str,
        source: str = "arena",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self.events.publish(
            self.SESSION_READY,
            {
                "source": source,
                "arena_session_id": arena_session_id,
                "combat_id": combat_id,
                "metadata": metadata or {},
            },
            correlation_id=arena_session_id,
        )

    async def session_failed(self, *, arena_session_id: str, error: str, source: str = "arena") -> None:
        await self.events.publish(
            self.SESSION_FAILED,
            {"source": source, "arena_session_id": arena_session_id, "error": error},
            correlation_id=arena_session_id,
        )

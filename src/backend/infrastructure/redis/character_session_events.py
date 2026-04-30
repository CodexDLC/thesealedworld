from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.core.bus import GameEventProducer


class CharacterSessionEvents:
    """Typed stream publisher for future character_session.* events."""

    CREATED = "character_session.created"
    SCENARIO_ATTACHED = "character_session.scenario_attached"
    SCENARIO_CLEARED = "character_session.scenario_cleared"
    COMBAT_ATTACHED = "character_session.combat_attached"
    COMBAT_CLEARED = "character_session.combat_cleared"
    INVENTORY_ATTACHED = "character_session.inventory_attached"
    INVENTORY_CLEARED = "character_session.inventory_cleared"
    VITALS_CHANGED = "character_session.vitals_changed"
    LOCATION_CHANGED = "character_session.location_changed"
    STATE_TRANSITIONED = "character_session.state_transitioned"

    def __init__(self, events: GameEventProducer) -> None:
        self.events = events

    async def created(self, char_id: int, user_id: str, *, correlation_id: str | None = None) -> str:
        return await self.events.publish(
            self.CREATED,
            {"char_id": char_id, "user_id": user_id},
            correlation_id=correlation_id,
        )

    async def scenario_attached(
        self,
        char_id: int,
        scenario_id: str,
        *,
        active_quest: str | None = None,
        correlation_id: str | None = None,
    ) -> str:
        return await self.events.publish(
            self.SCENARIO_ATTACHED,
            {"char_id": char_id, "scenario_id": scenario_id, "active_quest": active_quest},
            correlation_id=correlation_id,
        )

    async def scenario_cleared(self, char_id: int, *, correlation_id: str | None = None) -> str:
        return await self.events.publish(
            self.SCENARIO_CLEARED,
            {"char_id": char_id},
            correlation_id=correlation_id,
        )

    async def combat_attached(self, char_id: int, combat_id: str, *, correlation_id: str | None = None) -> str:
        return await self.events.publish(
            self.COMBAT_ATTACHED,
            {"char_id": char_id, "combat_id": combat_id},
            correlation_id=correlation_id,
        )

    async def combat_cleared(self, char_id: int, *, correlation_id: str | None = None) -> str:
        return await self.events.publish(
            self.COMBAT_CLEARED,
            {"char_id": char_id},
            correlation_id=correlation_id,
        )

    async def inventory_attached(self, char_id: int, inventory_id: str, *, correlation_id: str | None = None) -> str:
        return await self.events.publish(
            self.INVENTORY_ATTACHED,
            {"char_id": char_id, "inventory_id": inventory_id},
            correlation_id=correlation_id,
        )

    async def inventory_cleared(self, char_id: int, *, correlation_id: str | None = None) -> str:
        return await self.events.publish(
            self.INVENTORY_CLEARED,
            {"char_id": char_id},
            correlation_id=correlation_id,
        )

    async def vitals_changed(
        self,
        char_id: int,
        changes: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> str:
        return await self.events.publish(
            self.VITALS_CHANGED,
            {"char_id": char_id, "changes": changes},
            correlation_id=correlation_id,
        )

    async def location_changed(
        self,
        char_id: int,
        current: str,
        *,
        prev: str | None = None,
        correlation_id: str | None = None,
    ) -> str:
        return await self.events.publish(
            self.LOCATION_CHANGED,
            {"char_id": char_id, "current": current, "prev": prev},
            correlation_id=correlation_id,
        )

    async def state_transitioned(
        self,
        char_id: int,
        state: str,
        *,
        prev_state: str | None = None,
        correlation_id: str | None = None,
    ) -> str:
        return await self.events.publish(
            self.STATE_TRANSITIONED,
            {"char_id": char_id, "state": state, "prev_state": prev_state},
            correlation_id=correlation_id,
        )

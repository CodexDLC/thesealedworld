from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.features.combat.services.session_service import CombatSessionService
    from src.shared.schemas.combat import (
        CombatDashboardDTO,
        CombatLogDTO,
        CombatRegisterMoveRequestDTO,
        CombatResultDTO,
    )


class CombatRuntimeOrchestrator:
    """Runtime boundary for browser/API combat views and player intents."""

    def __init__(self, session_service: CombatSessionService) -> None:
        self.session_service = session_service

    async def get_initial_view(self, char_id: int) -> CombatDashboardDTO:
        return await self.session_service.get_dashboard(char_id)

    async def get_dashboard(self, char_id: int) -> CombatDashboardDTO:
        return await self.session_service.get_dashboard(char_id)

    async def get_logs(self, char_id: int, *, page: int = 1, page_size: int = 20) -> CombatLogDTO:
        return await self.session_service.get_logs(char_id, page=page, page_size=page_size)

    async def get_archived_result(self, char_id: int, *, reason: str = "combat_session_not_found") -> CombatResultDTO:
        return await self.session_service.get_archived_result(char_id, reason=reason)

    async def register_move(self, char_id: int, body: CombatRegisterMoveRequestDTO) -> CombatDashboardDTO:
        return await self.session_service.register_move(char_id, body)

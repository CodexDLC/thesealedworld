from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.features.combat.services.session_service import CombatSessionService
    from src.shared.schemas.combat import (
        CombatDashboardDTO,
        CombatLogDTO,
        CombatPinFeintRequestDTO,
        CombatRegisterMoveRequestDTO,
        CombatResultDTO,
    )


class CombatRuntimeOrchestrator:
    """Runtime boundary for API-facing combat reads and player intents.

    The orchestrator stays intentionally thin. It does not own combat logic,
    queue orchestration, or persistence details. Its job is to route browser/API
    requests into the session service and normalize the returned view/result
    shape for the public contract.
    """

    def __init__(self, session_service: CombatSessionService) -> None:
        self.session_service = session_service

    async def get_initial_view(self, char_id: int) -> CombatDashboardDTO | CombatResultDTO:
        """Return the current combat view or the archived result if combat ended.

        Args:
            char_id: Player character requesting the combat surface.

        Returns:
            The live combat dashboard while the runtime session is active, or the
            archived combat result once the combat is finished.
        """
        dashboard = await self.session_service.get_dashboard(char_id)
        if dashboard.status == "finished" or dashboard.winner_team:
            return await self.session_service.get_archived_result(char_id, reason="combat_session_finished")
        return dashboard

    async def get_dashboard(self, char_id: int) -> CombatDashboardDTO:
        """Load the current live combat dashboard for a character."""
        return await self.session_service.get_dashboard(char_id)

    async def get_logs(self, char_id: int, *, page: int = 1, page_size: int = 20) -> CombatLogDTO:
        """Load paginated combat logs for the current or archived combat."""
        return await self.session_service.get_logs(char_id, page=page, page_size=page_size)

    async def get_archived_result(self, char_id: int, *, reason: str = "combat_session_not_found") -> CombatResultDTO:
        return await self.session_service.get_archived_result(char_id, reason=reason)

    async def find_archived_result(
        self, char_id: int, *, reason: str = "combat_session_not_found"
    ) -> CombatResultDTO | None:
        return await self.session_service.find_archived_result(char_id, reason=reason)

    async def recover_missing_combat_transition(self, char_id: int, *, reason: str, combat_id: str | None = None):
        return await self.session_service.recover_missing_combat_transition(
            char_id,
            reason=reason,
            combat_id=combat_id,
        )

    async def continue_result(self, char_id: int):
        return await self.session_service.continue_result(char_id)

    async def register_move(
        self, char_id: int, body: CombatRegisterMoveRequestDTO
    ) -> CombatDashboardDTO | CombatResultDTO:
        """Register one player intent and return the resulting combat surface.

        Args:
            char_id: Acting player character.
            body: Public move request contract from the API layer.

        Returns:
            The live dashboard after the intent is accepted, or the archived
            combat result when the move settles the combat.
        """
        dashboard = await self.session_service.register_move(char_id, body)
        if dashboard.status == "finished" or dashboard.winner_team:
            return await self.session_service.get_archived_result(char_id, reason="combat_session_finished")
        return dashboard

    async def pin_feint(self, char_id: int, body: CombatPinFeintRequestDTO) -> CombatDashboardDTO:
        """Pin or unpin a combat feint for the current player hand."""
        return await self.session_service.pin_feint(char_id, body)

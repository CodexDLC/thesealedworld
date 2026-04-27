# apps/game_core/modules/combats/combat_gateway.py
from typing import Any

from loguru import logger as log

# DTOs
# Services
from src.backend.domains.user_features.combat.orchestrators.handler.combat_session_service import CombatSessionService
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.combat import CombatDashboardDTO, CombatLogDTO
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader


class CombatGateway:
    """
    CombatGateway (Layer 2: Runtime).
    Обеспечивает стыковку системы (SystemDispatcher) и бизнес-логики боя (v3.0).
    """

    def __init__(self, session_service: CombatSessionService):
        self.session_service = session_service

    # ==========================================================================
    # 1. SYSTEM CONTRACT (SystemDispatcher Integration)
    # ==========================================================================

    async def get_entry_point(self, action: str, context: dict[str, Any]) -> Any:
        """Вход для SystemDispatcher. Возвращает чистые DTO."""
        char_id = context.get("char_id") or context.get("actor_id")
        if not char_id:
            return {"success": False, "error": "Missing char_id"}

        char_id = int(char_id)

        try:
            if action in ("snapshot", "logs", "get_initial_state"):
                return await self._router_get_view(char_id, action, context)

            # Любое другое действие (атака, скилл, предмет)
            return await self._router_handle_action(char_id, action, context)

        except Exception as e:  # noqa: BLE001
            log.error(f"Gateway | System Error | {char_id=} | {e}")
            return {"success": False, "error": str(e)}

    # ==========================================================================
    # 2. CLIENT CONTRACT (FastAPI Response Wrapper)
    # ==========================================================================

    async def handle_action(self, char_id: int, action_type: str, payload: dict[str, Any]) -> CoreResponseDTO:
        """Метод для внешних API (возвращает обертку CoreResponseDTO)."""
        try:
            result = await self._router_handle_action(char_id, action_type, payload)
            return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.COMBAT), payload=result)
        except Exception as e:  # noqa: BLE001
            return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.COMBAT, error=str(e)), payload=None)

    async def get_view(self, char_id: int, view_type: str, params: dict[str, Any]) -> CoreResponseDTO:
        """Метод для внешних GET-запросов."""
        try:
            result = await self._router_get_view(char_id, view_type, params)
            return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.COMBAT), payload=result)
        except Exception as e:  # noqa: BLE001
            return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.COMBAT, error=str(e)), payload=None)

    # ==========================================================================
    # 3. INTERNAL LOGIC (The "Clean" Implementation)
    # ==========================================================================

    async def _router_get_view(
        self, char_id: int, view_type: str, params: dict[str, Any]
    ) -> CombatDashboardDTO | CombatLogDTO | None:
        """Логика чтения: скрываем session_id через SessionService."""
        if view_type in ("snapshot", "get_initial_state"):
            return await self.session_service.get_snapshot(char_id)

        elif view_type in ("logs", "history"):
            page = int(params.get("page", 1))
            return await self.session_service.get_logs(char_id, page)
        return None

    async def _router_handle_action(
        self, char_id: int, action_type: str, payload: dict[str, Any]
    ) -> CombatDashboardDTO:
        """
        Логика записи: делегируем всё в SessionService.
        В v3.0 Гейтвей больше НЕ создает CombatMoveDTO сам!
        Возвращает актуальный снапшот (Dashboard).
        """
        # ВАЖНО: Мы передаем action_type и payload отдельно,
        # чтобы TurnManager мог правильно выбрать DTO (Exchange/Item/Instant)

        # Создаем копию, чтобы не мутировать входной payload
        enriched_payload = payload.copy()
        if "action" not in enriched_payload:
            enriched_payload["action"] = action_type

        # Теперь это возвращает DTO (CombatDashboardDTO)
        return await self.session_service.register_move(char_id, enriched_payload)

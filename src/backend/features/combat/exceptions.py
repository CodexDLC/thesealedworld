from __future__ import annotations

from typing import Any

from src.backend.core.exceptions import BaseAPIException
from src.shared.schemas.combat import CombatErrorDTO


class CombatError(ValueError):
    """Typed combat-layer error safe to expose through the browser API."""

    code = "combat_error"
    status_code = 400
    frontend_action = "show_message"
    retriable = False

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        frontend_action: str | None = None,
        retriable: bool | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.code
        self.status_code = status_code if status_code is not None else self.status_code
        self.frontend_action = frontend_action or self.frontend_action
        self.retriable = retriable if retriable is not None else self.retriable
        self.context = context or {}


class CombatSessionNotFoundError(CombatError):
    """Raised when an actor is not attached to a combat session."""

    code = "combat_session_not_found"
    status_code = 404
    frontend_action = "recover_or_redirect"


class CombatActionRejectedError(CombatError):
    """Raised when a player's combat action is valid JSON but cannot be accepted."""

    code = "combat_action_rejected"
    status_code = 400


class CombatInvalidMovePayloadError(CombatActionRejectedError):
    code = "combat_invalid_move_payload"


class CombatFeintUnavailableError(CombatActionRejectedError):
    code = "combat_feint_unavailable"


class CombatTargetRequiredError(CombatActionRejectedError):
    code = "combat_target_required"


class CombatTargetUnavailableError(CombatActionRejectedError):
    code = "combat_target_unavailable"


class CombatAPIError(BaseAPIException):
    """HTTP exception that serializes to the shared CombatErrorDTO contract."""

    def __init__(self, error: CombatError, *, context: dict[str, Any] | None = None) -> None:
        merged_context = {**error.context, **(context or {})}
        payload = CombatErrorDTO(
            code=error.code,
            message=error.message,
            frontend_action=error.frontend_action,
            retriable=error.retriable,
            context=merged_context,
        )
        super().__init__(
            status_code=error.status_code,
            detail=payload.message,
            error_code=payload.code,
            extra=payload.model_dump(mode="json", exclude={"code", "message"}),
        )
        self.payload = payload

# backend/core/exceptions.py
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class BaseAPIException(HTTPException):
    """
    Base class for all API exceptions.
    """

    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        error_code: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.extra = extra or {}


class NotFoundException(BaseAPIException):
    """Resource not found (404)."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="not_found",
        )


class ValidationException(BaseAPIException):
    """Validation error (422)."""

    def __init__(self, detail: str, errors: list[Any] | None = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="validation_error",
            extra={"fields": errors or []},
        )


class BusinessLogicException(BaseAPIException):
    """Business logic conflict (409)."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="business_conflict",
        )


class PermissionDeniedException(BaseAPIException):
    """Permission denied (403)."""

    def __init__(self, detail: str = "Permission denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="permission_denied",
        )


class AuthException(BaseAPIException):
    """Authentication failed (401)."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="auth_error",
            extra={"headers": {"WWW-Authenticate": "Bearer"}},
        )


class SessionExpiredException(BaseAPIException):
    """
    Исключение для истекшей сессии (Redis).
    Клиент должен обработать это как сигнал к перезагрузке или выходу.
    """

    def __init__(self, detail: str = "SESSION_EXPIRED"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="session_expired",
        )


async def api_exception_handler(_: Request, exc: BaseAPIException) -> JSONResponse:
    """
    Handler for custom BaseAPIException.
    Returns structured JSON error response.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.detail,
                **exc.extra,
            }
        },
    )

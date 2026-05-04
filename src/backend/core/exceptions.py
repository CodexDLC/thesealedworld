from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from loguru import logger


class BaseAPIException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        error_code: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code or "api_error"
        self.extra = extra or {}


class AuthException(BaseAPIException):
    def __init__(self, detail: str = "Authentication failed") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="auth_error",
            extra={"headers": {"WWW-Authenticate": "Bearer"}},
        )


class BusinessLogicException(BaseAPIException):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="business_conflict",
        )


async def api_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    logger.warning(
        "API exception handled: method={} path={} status={} code={}",
        request.method,
        request.url.path,
        exc.status_code,
        exc.error_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.detail,
                **exc.extra,
            }
        },
        headers=exc.extra.get("headers"),
    )
